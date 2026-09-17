import argparse
import sys
from pathlib import Path

from config.settings import RUNS_DIR
from scripts.ai_extractor import available as ai_available
from scripts.ai_extractor import extract_record
from scripts.pipeline_service import execute_run, load_input
from scripts.report_config import build_report_settings
from scripts.terminal_editor import review_flagged_records
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
        return valid, []
    if issues:
        print("\nFlagged records can now be reviewed and corrected before generation.")
        answer = input("[R]eview/edit, [G]enerate valid records as shown, or [Q]uit: ").strip().lower()
        if answer in {"r", "review"}:
            reviewed, changes, cancelled = review_flagged_records(records, issues)
            if cancelled:
                return [], changes
            final_issues = validate_records(reviewed)
            remaining_errors = records_with_errors(final_issues)
            reviewed = [record for record in reviewed if record.get("id") not in remaining_errors]
            if remaining_errors:
                print(f"Skipping {len(remaining_errors)} record(s) that still contain errors.")
            confirm = input(f"Generate {len(reviewed)} reviewed record(s)? [y/N]: ").strip().lower()
            return (reviewed, changes) if confirm in {"y", "yes"} else ([], changes)
        if answer in {"g", "generate"}:
            confirm = input(f"Generate {len(valid)} valid record(s)? [y/N]: ").strip().lower()
            return (valid, []) if confirm in {"y", "yes"} else ([], [])
        return [], []
    answer = input(f"\nGenerate all {len(records)} record(s)? [y/N]: ").strip().lower()
    return (records, []) if answer in {"y", "yes"} else ([], [])


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

    initial_issues = issues
    approved, edits = approve(records, issues, args.yes)
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
    run_dir, summary = execute_run(
        approved,
        args.input,
        report_settings,
        edits,
        initial_issues,
        args.output_root,
        args.run_name,
        args.no_pdf,
    )

    print("\nCOMPLETE")
    print(f"  Run folder: {run_dir}")
    print(f"  HTML: {summary['html_generated']}/{len(approved)}")
    if not args.no_pdf:
        print(f"  PDF:  {summary['pdf_generated']}/{len(approved)}")
    print(f"  Failures: {len(summary['failures'])}")
    return 1 if summary['failures'] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
