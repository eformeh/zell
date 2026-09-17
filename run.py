import argparse
import json
import re
import shutil
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from config.settings import RUNS_DIR, load_report_settings
from scripts.ai_extractor import available as ai_available
from scripts.ai_extractor import extract_record
from scripts.convert_structured_data import convert, split_records
from scripts.pdf_generator import convert_html_to_pdf
from scripts.report_config import build_report_settings
from scripts.report_generator import render_template, save_html_report
from scripts.validation import needs_ai_review, records_with_errors, validate_records


def parse_args():
    parser = argparse.ArgumentParser(description="Convert, validate, approve, and generate CAC search reports.")
    parser.add_argument("input", type=Path, help="Structured .txt input or normalized .json input.")
    parser.add_argument("--date", help="Report date: today, YYYY-MM-DD, DD/MM/YYYY, or display text.")
    parser.add_argument("--recipient-title", help="Recipient role/title for this run.")
    parser.add_argument("--recipient", dest="recipient_organization", help="Recipient bank or organization.")
    parser.add_argument("--recipient-address", action="append", help="Recipient address line; repeat for each line.")
    parser.add_argument("--salutation", help="Letter salutation for this run.")
    parser.add_argument("--ai", action="store_true", help="Use optional AI fallback for structurally invalid records.")
    parser.add_argument("--yes", action="store_true", help="Approve all valid records without prompting.")
    parser.add_argument("--no-pdf", action="store_true", help="Create normalized data and HTML only.")
    parser.add_argument("--validate-only", action="store_true", help="Validate and preview without generating reports.")
    parser.add_argument("--ids", help="Comma-separated record IDs to process.")
    parser.add_argument("--output-root", type=Path, default=RUNS_DIR, help="Root folder for timestamped runs.")
    parser.add_argument("--run-name", help="Optional readable suffix for the run folder.")
    return parser.parse_args()


def load_input(path):
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


def preview(records, issues):
    errors = sum(item.severity == "error" for item in issues)
    warnings = sum(item.severity == "warning" for item in issues)
    categories = {}
    for record in records:
        categories[record.get("category", "unknown")] = categories.get(record.get("category", "unknown"), 0) + 1
    print("\nPREVIEW")
    print(f"  Records:  {len(records)}")
    print(f"  Categories: {', '.join(f'{key}={value}' for key, value in sorted(categories.items()))}")
    print(f"  Errors:   {errors}")
    print(f"  Warnings: {warnings}")
    if issues:
        print("\nVALIDATION ISSUES")
        for item in issues:
            marker = "ERROR" if item.severity == "error" else "WARN "
            print(f"  [{marker}] ID {item.record_id} - {item.company_name}: {item.message}")


def run_ai_fallback(records, sources, issues):
    targets = needs_ai_review(issues)
    if not targets:
        print("AI fallback: no structurally uncertain records found.")
        return records
    if not ai_available():
        raise RuntimeError("--ai requires OPENAI_API_KEY and OPENAI_MODEL environment variables.")
    updated = []
    for record in records:
        if record.get("id") not in targets:
            updated.append(record)
            continue
        source = sources.get(record.get("id"))
        if not source:
            print(f"AI fallback skipped ID {record.get('id')}: original TXT block unavailable.")
            updated.append(record)
            continue
        print(f"AI fallback: reviewing ID {record.get('id')} - {record.get('company_name')}")
        try:
            updated.append(extract_record(source))
        except Exception as exc:
            print(f"AI fallback failed for ID {record.get('id')}: {exc}")
            updated.append(record)
    return updated


def approve(records, issues, assume_yes):
    invalid_ids = records_with_errors(issues)
    valid = [record for record in records if record.get("id") not in invalid_ids]
    if assume_yes:
        if invalid_ids:
            print(f"Skipping {len(invalid_ids)} invalid record(s); approving {len(valid)} valid record(s).")
        return valid
    if invalid_ids:
        answer = input(f"\nGenerate {len(valid)} valid record(s) and skip {len(invalid_ids)} invalid record(s)? [y/N]: ").strip().lower()
    else:
        answer = input(f"\nGenerate all {len(records)} record(s)? [y/N]: ").strip().lower()
    return valid if answer in {"y", "yes"} else []


def prepare_run_folder(root, run_name=None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = ""
    if run_name:
        suffix = "_" + re.sub(r"[^A-Za-z0-9_-]+", "_", run_name).strip("_")
    folder = root.resolve() / f"{timestamp}{suffix}"
    for child in ("input", "data", "html", "pdf", "logs"):
        (folder / child).mkdir(parents=True, exist_ok=False)
    return folder


def generate_html(record, html_dir, report_settings):
    name = safe_filename(record)
    html = render_template(record, record["category"], report_settings)
    save_html_report(html, name, html_dir)
    return record, name, html_dir / f"{name}.html"


def generate_reports(records, run_dir, report_settings, no_pdf=False):
    generation = report_settings["generation"]
    html_results = []
    failures = []
    with ThreadPoolExecutor(max_workers=max(1, int(generation["html_workers"]))) as pool:
        futures = {pool.submit(generate_html, record, run_dir / "html", report_settings): record for record in records}
        for future in as_completed(futures):
            record = futures[future]
            try:
                html_results.append(future.result())
            except Exception as exc:
                failures.append({"id": record.get("id"), "stage": "html", "error": str(exc)})

    generated_pdfs = []
    if not no_pdf:
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
            for future in as_completed(futures):
                record = futures[future]
                try:
                    generated_pdfs.append(str(future.result()))
                except Exception as exc:
                    failures.append({"id": record.get("id"), "stage": "pdf", "error": str(exc)})
    return html_results, generated_pdfs, failures


def main():
    args = parse_args()
    records, sources = load_input(args.input.resolve())
    if args.ids:
        selected = {int(value.strip()) for value in args.ids.split(",") if value.strip()}
        records = [record for record in records if record.get("id") in selected]
        sources = {key: value for key, value in sources.items() if key in selected}
    if not records:
        raise RuntimeError("No records were selected.")

    issues = validate_records(records)
    if args.ai:
        records = run_ai_fallback(records, sources, issues)
        issues = validate_records(records)
    preview(records, issues)
    if args.validate_only:
        return 1 if records_with_errors(issues) else 0

    approved = approve(records, issues, args.yes)
    if not approved:
        print("Generation cancelled; no output was created.")
        return 1

    recipient_overrides = {
        "title": args.recipient_title,
        "organization": args.recipient_organization,
        "address_lines": args.recipient_address,
        "salutation": args.salutation,
    }
    report_settings = build_report_settings(args.date, recipient_overrides)
    run_dir = prepare_run_folder(args.output_root, args.run_name)
    shutil.copy2(args.input.resolve(), run_dir / "input" / args.input.name)
    (run_dir / "data" / "normalized.json").write_text(
        json.dumps(approved, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (run_dir / "data" / "report_settings.json").write_text(
        json.dumps(report_settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    html_results, pdfs, failures = generate_reports(approved, run_dir, report_settings, args.no_pdf)
    summary = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input": str(args.input.resolve()),
        "run_directory": str(run_dir),
        "approved_records": len(approved),
        "html_generated": len(html_results),
        "pdf_generated": len(pdfs),
        "validation_issues": [item.to_dict() for item in issues],
        "failures": failures,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "logs" / "failures.json").write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")

    print("\nCOMPLETE")
    print(f"  Run folder: {run_dir}")
    print(f"  HTML: {len(html_results)}/{len(approved)}")
    if not args.no_pdf:
        print(f"  PDF:  {len(pdfs)}/{len(approved)}")
    print(f"  Failures: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
