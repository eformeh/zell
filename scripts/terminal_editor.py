import json

from scripts.validation import validate_record


COMMON_FIELDS = [
    ("company_name", "Company name"),
    ("registration_number", "Registration number"),
    ("registered_address", "Registered address"),
    ("incorporation_date", "Incorporation date"),
    ("main_object", "Main object"),
]
ROLE_FIELDS = {
    "business": ("proprietors", "Proprietors"),
    "company": ("directors", "Directors"),
    "partnership": ("partners", "Partners"),
    "guarantee": ("directors", "Directors"),
    "trustee": ("trustees", "Trustees"),
}


def record_change(changes, record, field, before, after):
    if before == after:
        return
    changes.append({
        "record_id": record.get("id"),
        "company_name": record.get("company_name", ""),
        "field": field,
        "original": before,
        "corrected": after,
    })


def prompt_value(label, current, input_fn=input, output_fn=print):
    output_fn(f"Current {label}: {current or '<empty>'}")
    value = input_fn(f"New {label} (blank keeps current): ").strip()
    return value if value else current


def edit_people(record, field, label, changes, input_fn=input, output_fn=print, shares=False):
    items = record.setdefault(field, [])
    while True:
        output_fn(f"\n{label.upper()}")
        if not items:
            output_fn("  No entries.")
        for index, item in enumerate(items, 1):
            detail = item.get("shares") if shares else item.get("address")
            output_fn(f"  {index}. {item.get('name', '<unnamed>')} - {detail or '<empty>'}")
        action = input_fn("Choose number to edit, [A]dd, [D]elete, or [B]ack: ").strip().lower()
        if action in {"b", "back", ""}:
            return
        if action in {"a", "add"}:
            name = input_fn("Name: ").strip()
            if not name:
                output_fn("Name is required.")
                continue
            detail_key = "shares" if shares else "address"
            default = "" if shares else record.get("registered_address", "")
            detail = input_fn(f"{detail_key.title()} [{default}]: ").strip() or default
            item = {"name": name, detail_key: detail}
            items.append(item)
            record_change(changes, record, f"{field}[{len(items) - 1}]", None, dict(item))
            continue
        if action in {"d", "delete"}:
            value = input_fn("Entry number to delete: ").strip()
            if not value.isdigit() or not 1 <= int(value) <= len(items):
                output_fn("Invalid entry number.")
                continue
            index = int(value) - 1
            removed = items.pop(index)
            record_change(changes, record, f"{field}[{index}]", dict(removed), None)
            continue
        if not action.isdigit() or not 1 <= int(action) <= len(items):
            output_fn("Invalid choice.")
            continue
        index = int(action) - 1
        item = items[index]
        before = dict(item)
        item["name"] = prompt_value("name", item.get("name", ""), input_fn, output_fn)
        detail_key = "shares" if shares else "address"
        item[detail_key] = prompt_value(detail_key, item.get(detail_key, ""), input_fn, output_fn)
        record_change(changes, record, f"{field}[{index}]", before, dict(item))


def edit_secretary(record, field, label, changes, input_fn=input, output_fn=print):
    current = record.get(field)
    output_fn(f"\n{label}: {json.dumps(current, ensure_ascii=False) if current else 'Nil'}")
    action = input_fn("[S]et/edit, [C]lear, or [B]ack: ").strip().lower()
    if action in {"c", "clear"}:
        record[field] = None
        record_change(changes, record, field, current, None)
    elif action in {"s", "set"}:
        before = dict(current) if isinstance(current, dict) else current
        person = dict(current) if isinstance(current, dict) else {"name": "", "address": record.get("registered_address", "")}
        person["name"] = prompt_value("name", person.get("name", ""), input_fn, output_fn)
        person["address"] = prompt_value("address", person.get("address", ""), input_fn, output_fn)
        record[field] = person
        record_change(changes, record, field, before, dict(person))


def editable_fields(record):
    fields = list(COMMON_FIELDS)
    category = record.get("category")
    if category == "company":
        fields.append(("share_capital", "Share capital"))
    role = ROLE_FIELDS.get(category)
    if role:
        fields.append(role)
    if category == "company":
        fields.extend([("shareholders", "Shareholders"), ("company_sec", "Company secretary")])
    elif category == "guarantee":
        fields.extend([("guarantors", "Guarantors"), ("company_sec", "Company secretary")])
    elif category == "trustee":
        fields.append(("trustee_sec", "Trustee secretary"))
    return fields


def edit_record(record, input_fn=input, output_fn=print):
    changes = []
    while True:
        fields = editable_fields(record)
        output_fn(f"\nEDIT ID {record.get('id')} - {record.get('company_name')}")
        for index, (_, label) in enumerate(fields, 1):
            output_fn(f"  {index}. {label}")
        output_fn("  V. View complete record")
        output_fn("  B. Back to validation")
        choice = input_fn("Select a field: ").strip().lower()
        if choice in {"b", "back", ""}:
            return changes
        if choice in {"v", "view"}:
            output_fn(json.dumps(record, indent=2, ensure_ascii=False))
            continue
        if not choice.isdigit() or not 1 <= int(choice) <= len(fields):
            output_fn("Invalid choice.")
            continue
        field, label = fields[int(choice) - 1]
        if field in {"proprietors", "directors", "partners", "trustees", "guarantors"}:
            edit_people(record, field, label, changes, input_fn, output_fn)
        elif field == "shareholders":
            edit_people(record, field, label, changes, input_fn, output_fn, shares=True)
        elif field in {"company_sec", "trustee_sec"}:
            edit_secretary(record, field, label, changes, input_fn, output_fn)
        else:
            before = record.get(field, "")
            after = prompt_value(label.lower(), before, input_fn, output_fn)
            record[field] = after
            record_change(changes, record, field, before, after)


def show_issues(record, issues, output_fn=print):
    current = [item for item in issues if item.record_id == record.get("id")]
    if not current:
        output_fn("  Validation passed.")
        return
    for item in current:
        output_fn(f"  [{item.severity.upper()}] {item.message}")


def review_flagged_records(records, initial_issues, input_fn=input, output_fn=print):
    flagged_ids = []
    for item in initial_issues:
        if item.record_id not in flagged_ids:
            flagged_ids.append(item.record_id)
    skipped = set()
    changes = []

    for record_id in flagged_ids:
        record = next((item for item in records if item.get("id") == record_id), None)
        if record is None:
            continue
        while True:
            current_issues = validate_record(record)
            output_fn(f"\nREVIEW ID {record.get('id')} - {record.get('company_name')}")
            show_issues(record, current_issues, output_fn)
            has_errors = any(item.severity == "error" for item in current_issues)
            keep_label = "[K]eep original" if not has_errors else "[K]eep unavailable while errors remain"
            output_fn(f"  [E]dit  [V]iew  {keep_label}  [S]kip  [Q]uit")
            action = input_fn("Action: ").strip().lower()
            if action in {"e", "edit"}:
                changes.extend(edit_record(record, input_fn, output_fn))
            elif action in {"v", "view"}:
                output_fn(json.dumps(record, indent=2, ensure_ascii=False))
            elif action in {"k", "keep"} and not has_errors:
                break
            elif action in {"s", "skip"}:
                skipped.add(record_id)
                break
            elif action in {"q", "quit"}:
                return [], changes, True
            else:
                output_fn("Choose a valid action.")

    approved = [record for record in records if record.get("id") not in skipped]
    return approved, changes, False
