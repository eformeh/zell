import json
import re
import shutil
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from config.settings import RUNS_DIR
from scripts.convert_structured_data import convert, split_records
from scripts.pdf_generator import convert_html_to_pdf
from scripts.report_generator import render_template, save_html_report


def load_input(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.suffix.lower() == ".json":
        records = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(records, list):
            raise ValueError("JSON input must contain an array of records.")
        return records, {}
    if path.suffix.lower() != ".txt":
        raise ValueError("This phase supports .txt and .json input files.")
    text = path.read_text(encoding="utf-8-sig")
    records = convert(text)
    sources = {
        record_id: f"{record_id}. {name}\n" + "\n".join(lines)
        for record_id, name, lines in split_records(text)
    }
    return records, sources


def safe_filename(record):
    name = unicodedata.normalize("NFKD", str(record.get("company_name", "report")))
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "report"
    return f"{int(record.get('id', 0)):03d}_{name[:100]}"


def prepare_run_folder(root=RUNS_DIR, run_name=None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = ""
    if run_name:
        suffix = "_" + re.sub(r"[^A-Za-z0-9_-]+", "_", run_name).strip("_")
    folder = Path(root).resolve() / f"{timestamp}{suffix}"
    counter = 2
    candidate = folder
    while candidate.exists():
        candidate = folder.with_name(f"{folder.name}_{counter}")
        counter += 1
    folder = candidate
    for child in ("input", "data", "html", "pdf", "logs"):
        (folder / child).mkdir(parents=True, exist_ok=False)
    return folder


def generate_html(record, html_dir, report_settings):
    name = safe_filename(record)
    html = render_template(record, record["category"], report_settings)
    save_html_report(html, name, html_dir)
    return record, name, Path(html_dir) / f"{name}.html"


def generate_reports(records, run_dir, report_settings, no_pdf=False, progress=None):
    generation = report_settings["generation"]
    html_results = []
    failures = []
    total = len(records)

    def update(stage, completed):
        if progress:
            progress(stage, completed, total)

    update("html", 0)
    with ThreadPoolExecutor(max_workers=max(1, int(generation["html_workers"]))) as pool:
        futures = {pool.submit(generate_html, record, run_dir / "html", report_settings): record for record in records}
        for completed, future in enumerate(as_completed(futures), 1):
            record = futures[future]
            try:
                html_results.append(future.result())
            except Exception as exc:
                failures.append({"id": record.get("id"), "stage": "html", "error": str(exc)})
            update("html", completed)

    generated_pdfs = []
    if not no_pdf:
        update("pdf", 0)
        with ThreadPoolExecutor(max_workers=max(1, int(generation["pdf_workers"]))) as pool:
            futures = {}
            for record, name, html_path in html_results:
                output_pdf = run_dir / "pdf" / f"{name}.pdf"
                future = pool.submit(
                    convert_html_to_pdf,
                    html_path,
                    output_pdf,
                    int(generation["pdf_retries"]),
                    generation["wkhtmltopdf_path"],
                )
                futures[future] = record
            for completed, future in enumerate(as_completed(futures), 1):
                record = futures[future]
                try:
                    generated_pdfs.append(str(future.result()))
                except Exception as exc:
                    failures.append({"id": record.get("id"), "stage": "pdf", "error": str(exc)})
                update("pdf", completed)
    return html_results, generated_pdfs, failures


def execute_run(
    records,
    input_path,
    report_settings,
    edits=None,
    initial_issues=None,
    output_root=RUNS_DIR,
    run_name=None,
    no_pdf=False,
    progress=None,
):
    from scripts.validation import validate_records

    edits = edits or []
    initial_issues = initial_issues or []
    run_dir = prepare_run_folder(output_root, run_name)
    input_path = Path(input_path).resolve()
    shutil.copy2(input_path, run_dir / "input" / input_path.name)
    (run_dir / "data" / "normalized.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (run_dir / "data" / "report_settings.json").write_text(
        json.dumps(report_settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (run_dir / "data" / "edits.json").write_text(
        json.dumps(edits, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    html_results, pdfs, failures = generate_reports(records, run_dir, report_settings, no_pdf, progress)
    final_issues = validate_records(records)
    summary = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input": str(input_path),
        "run_directory": str(run_dir),
        "approved_records": len(records),
        "html_generated": len(html_results),
        "pdf_generated": len(pdfs),
        "initial_validation_issues": [item.to_dict() if hasattr(item, "to_dict") else item for item in initial_issues],
        "validation_issues": [item.to_dict() for item in final_issues],
        "edits": edits,
        "failures": failures,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "logs" / "failures.json").write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")
    return run_dir, summary


def list_runs(root=RUNS_DIR):
    root = Path(root)
    if not root.exists():
        return []
    runs = []
    for folder in sorted((item for item in root.iterdir() if item.is_dir()), reverse=True):
        summary_path = folder / "summary.json"
        if not summary_path.is_file():
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        summary["folder_name"] = folder.name
        runs.append(summary)
    return runs
