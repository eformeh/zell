import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, flash, jsonify, redirect, render_template as render_page
from flask import request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from config.settings import PROJECT_ROOT, RUNS_DIR, load_report_settings
from scripts.ai_extractor import available as ai_available
from scripts.ai_extractor import extract_record
from scripts.gui_store import DraftStore, find_record
from scripts.pipeline_service import execute_run, list_runs, load_input
from scripts.report_config import build_report_settings
from scripts.report_generator import render_template as render_report
from scripts.validation import needs_ai_review, records_with_errors, validate_record, validate_records


load_dotenv(PROJECT_ROOT / ".env")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "local-cac-v3-session"),
    MAX_CONTENT_LENGTH=20 * 1024 * 1024,
)
store = DraftStore()
jobs = {}
jobs_lock = threading.Lock()


def issue_map(records):
    grouped = {str(record.get("id")): [] for record in records}
    for item in validate_records(records):
        grouped.setdefault(str(item.record_id), []).append(item.to_dict())
    return grouped


def counts_for(state):
    issues = validate_records(state["records"])
    skipped = {int(value) for value in state.get("skipped_ids", [])}
    active = [record for record in state["records"] if int(record["id"]) not in skipped]
    active_issues = validate_records(active)
    return {
        "records": len(state["records"]),
        "active": len(active),
        "skipped": len(skipped),
        "errors": sum(item.severity == "error" for item in active_issues),
        "warnings": sum(item.severity == "warning" for item in active_issues),
        "all_issues": issues,
    }


@app.get("/")
def home():
    defaults = build_report_settings()
    return render_page("gui_home.html", defaults=defaults, today=date.today().isoformat(), runs=list_runs()[:6], ai_ready=ai_available())


@app.post("/drafts")
def create_draft():
    upload = request.files.get("source_file")
    if not upload or not upload.filename:
        flash("Choose a TXT or JSON file.", "error")
        return redirect(url_for("home"))
    filename = secure_filename(upload.filename)
    if Path(filename).suffix.lower() not in {".txt", ".json"}:
        flash("Only TXT and JSON files are supported in this phase.", "error")
        return redirect(url_for("home"))
    content = upload.read()
    if not content:
        flash("The selected file is empty.", "error")
        return redirect(url_for("home"))

    temporary = store.root / f"upload-{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
    temporary.write_bytes(content)
    try:
        records, sources = load_input(temporary)
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        flash(str(exc), "error")
        return redirect(url_for("home"))
    temporary.unlink(missing_ok=True)

    address_lines = [line.strip() for line in request.form.get("recipient_address", "").splitlines() if line.strip()]
    overrides = {
        "title": request.form.get("recipient_title", "").strip() or None,
        "organization": request.form.get("recipient_organization", "").strip() or None,
        "address_lines": address_lines or None,
        "salutation": request.form.get("salutation", "").strip() or None,
    }
    settings = build_report_settings(request.form.get("report_date", "today"), overrides)
    state = store.create(filename, content, records, sources, settings)
    if request.form.get("use_ai") == "on":
        apply_ai_to_state(state)
        store.save(state)
    return redirect(url_for("review_draft", draft_id=state["id"]))


def apply_ai_to_state(state):
    if not ai_available():
        flash("AI fallback is not configured. Add OPENAI_API_KEY and OPENAI_MODEL to .env.", "error")
        return
    issues = validate_records(state["records"])
    targets = needs_ai_review(issues)
    if not targets:
        flash("No structurally invalid records needed AI review.", "info")
        return
    failures = []
    for index, record in enumerate(state["records"]):
        if record.get("id") not in targets:
            continue
        source = state.get("sources", {}).get(str(record.get("id")))
        if not source:
            failures.append(str(record.get("id")))
            continue
        try:
            replacement = extract_record(source)
            state["edits"].append({
                "record_id": record.get("id"),
                "field": "ai_fallback",
                "original": record,
                "corrected": replacement,
            })
            state["records"][index] = replacement
        except Exception:
            failures.append(str(record.get("id")))
    if failures:
        flash(f"AI review could not update record(s): {', '.join(failures)}.", "error")
    else:
        flash("AI review completed. Please verify every changed record.", "success")


@app.get("/drafts/<draft_id>")
def review_draft(draft_id):
    try:
        state = store.load(draft_id)
    except FileNotFoundError:
        abort(404)
    counts = counts_for(state)
    return render_page(
        "gui_review.html",
        state=state,
        counts=counts,
        issues=issue_map(state["records"]),
        skipped={int(value) for value in state.get("skipped_ids", [])},
        ai_ready=ai_available(),
    )


@app.post("/drafts/<draft_id>/ai")
def review_with_ai(draft_id):
    try:
        state = store.load(draft_id)
    except FileNotFoundError:
        abort(404)
    apply_ai_to_state(state)
    store.save(state)
    return redirect(url_for("review_draft", draft_id=draft_id))


@app.post("/drafts/<draft_id>/records/<int:record_id>/skip")
def toggle_skip(draft_id, record_id):
    try:
        state = store.load(draft_id)
    except FileNotFoundError:
        abort(404)
    skipped = {int(value) for value in state.get("skipped_ids", [])}
    if record_id in skipped:
        skipped.remove(record_id)
    else:
        skipped.add(record_id)
    state["skipped_ids"] = sorted(skipped)
    store.save(state)
    return redirect(url_for("review_draft", draft_id=draft_id))


def pairs(names, values, second_key):
    return [
        {"name": name.strip(), second_key: value.strip()}
        for name, value in zip(names, values)
        if name.strip() or value.strip()
    ]


@app.route("/drafts/<draft_id>/records/<int:record_id>", methods=["GET", "POST"])
def edit_record(draft_id, record_id):
    try:
        state = store.load(draft_id)
    except FileNotFoundError:
        abort(404)
    record = find_record(state, record_id)
    if record is None:
        abort(404)
    if request.method == "POST":
        before = deepcopy(record)
        for field in ("company_name", "registration_number", "registered_address", "incorporation_date", "main_object"):
            record[field] = request.form.get(field, "").strip()
        category = record.get("category")
        role_field = {
            "business": "proprietors", "company": "directors", "partnership": "partners",
            "guarantee": "directors", "trustee": "trustees",
        }.get(category)
        if role_field:
            record[role_field] = pairs(
                request.form.getlist(f"{role_field}_name"),
                request.form.getlist(f"{role_field}_address"),
                "address",
            )
        if category == "company":
            record["share_capital"] = request.form.get("share_capital", "").strip()
            record["shareholders"] = pairs(
                request.form.getlist("shareholders_name"),
                request.form.getlist("shareholders_shares"),
                "shares",
            )
        if category == "guarantee":
            record["guarantors"] = pairs(
                request.form.getlist("guarantors_name"),
                request.form.getlist("guarantors_address"),
                "address",
            )
        secretary_field = "trustee_sec" if category == "trustee" else "company_sec" if category in {"company", "guarantee"} else None
        if secretary_field:
            secretary_name = request.form.get("secretary_name", "").strip()
            secretary_address = request.form.get("secretary_address", "").strip()
            record[secretary_field] = {"name": secretary_name, "address": secretary_address} if secretary_name else None
        if before != record:
            state["edits"].append({
                "record_id": record_id,
                "company_name": record.get("company_name"),
                "field": "record",
                "original": before,
                "corrected": deepcopy(record),
            })
        store.save(state)
        flash("Record saved and revalidated.", "success")
        if request.form.get("save_action") == "preview":
            return redirect(url_for("preview_record", draft_id=draft_id, record_id=record_id))
        return redirect(url_for("review_draft", draft_id=draft_id))
    return render_page(
        "gui_edit.html",
        state=state,
        record=record,
        record_issues=validate_record(record),
    )


@app.get("/drafts/<draft_id>/preview/<int:record_id>")
def preview_record(draft_id, record_id):
    try:
        state = store.load(draft_id)
    except FileNotFoundError:
        abort(404)
    record = find_record(state, record_id)
    if record is None:
        abort(404)
    return render_report(record, record["category"], state["report_settings"], browser_asset_uris())


def browser_asset_uris():
    return {
        "stylesheet_uri": url_for("static", filename="css/styles.css"),
        "logo_uri": url_for("static", filename="images/logo.jpg"),
        "signature_uri": url_for("static", filename="images/signature.jpg"),
        "stamp_beside_uri": url_for("static", filename="images/stamp2.png"),
        "stamp_below_uri": url_for("static", filename="images/stamp1.png"),
    }


def update_job(job_id, **values):
    with jobs_lock:
        jobs.setdefault(job_id, {}).update(values)


def generation_worker(job_id, state, records, no_pdf):
    try:
        update_job(job_id, status="running", stage="html", completed=0, total=len(records))

        def progress(stage, completed, total):
            update_job(job_id, stage=stage, completed=completed, total=total)

        initial = validate_records(state["records"])
        run_dir, summary = execute_run(
            records,
            state["input_path"],
            state["report_settings"],
            state.get("edits", []),
            initial,
            RUNS_DIR,
            state["report_settings"]["recipient"]["organization"],
            no_pdf,
            progress,
        )
        update_job(
            job_id,
            status="completed",
            stage="done",
            run=run_dir.name,
            summary=summary,
            completed=len(records),
        )
    except Exception as exc:
        update_job(job_id, status="failed", error=str(exc))


@app.post("/drafts/<draft_id>/generate")
def generate_draft(draft_id):
    try:
        state = store.load(draft_id)
    except FileNotFoundError:
        abort(404)
    skipped = {int(value) for value in state.get("skipped_ids", [])}
    records = [record for record in state["records"] if int(record["id"]) not in skipped]
    errors = records_with_errors(validate_records(records))
    if errors:
        flash(f"Resolve or skip records with errors: {', '.join(map(str, sorted(errors)))}.", "error")
        return redirect(url_for("review_draft", draft_id=draft_id))
    if not records:
        flash("No active records are available to generate.", "error")
        return redirect(url_for("review_draft", draft_id=draft_id))
    job_id = uuid.uuid4().hex
    update_job(job_id, status="queued", stage="queued", completed=0, total=len(records), draft_id=draft_id)
    thread = threading.Thread(
        target=generation_worker,
        args=(job_id, state, deepcopy(records), request.form.get("no_pdf") == "on"),
        daemon=True,
    )
    thread.start()
    return redirect(url_for("job_page", job_id=job_id))


@app.get("/jobs/<job_id>")
def job_page(job_id):
    with jobs_lock:
        job = deepcopy(jobs.get(job_id))
    if not job:
        abort(404)
    return render_page("gui_job.html", job=job, job_id=job_id)


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    with jobs_lock:
        job = deepcopy(jobs.get(job_id))
    if not job:
        abort(404)
    return jsonify(job)


@app.get("/runs")
def run_history():
    return render_page("gui_runs.html", runs=list_runs())


@app.get("/runs/<run_name>")
def run_detail(run_name):
    run_dir = (RUNS_DIR / run_name).resolve()
    if run_dir.parent != RUNS_DIR.resolve() or not run_dir.is_dir():
        abort(404)
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        abort(404)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    html_files = sorted(path.name for path in (run_dir / "html").glob("*.html"))
    pdf_files = sorted(path.name for path in (run_dir / "pdf").glob("*.pdf"))
    return render_page("gui_run_detail.html", run_name=run_name, summary=summary, html_files=html_files, pdf_files=pdf_files)


@app.get("/runs/<run_name>/<kind>/<path:filename>")
def run_artifact(run_name, kind, filename):
    if kind not in {"html", "pdf", "data", "logs"}:
        abort(404)
    directory = (RUNS_DIR / run_name / kind).resolve()
    expected_parent = (RUNS_DIR / run_name).resolve()
    if directory.parent != expected_parent or not directory.is_dir():
        abort(404)
    if kind == "html":
        path = directory / filename
        if not path.is_file():
            abort(404)
        html = path.read_text(encoding="utf-8")
        settings = load_report_settings()
        replacements = {
            (PROJECT_ROOT / "static" / "css" / "styles.css").resolve().as_uri(): url_for("static", filename="css/styles.css"),
            (PROJECT_ROOT / "static" / settings["assets"]["logo"]).resolve().as_uri(): url_for("static", filename="images/logo.jpg"),
            (PROJECT_ROOT / "static" / settings["assets"]["signature"]).resolve().as_uri(): url_for("static", filename="images/signature.jpg"),
            (PROJECT_ROOT / "static" / settings["assets"]["stamp_beside"]).resolve().as_uri(): url_for("static", filename="images/stamp2.png"),
            (PROJECT_ROOT / "static" / settings["assets"]["stamp_below"]).resolve().as_uri(): url_for("static", filename="images/stamp1.png"),
        }
        for source, target in replacements.items():
            html = html.replace(source, target)
        return html
    return send_from_directory(directory, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
