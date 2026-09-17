import re
from collections import Counter
from dataclasses import asdict, dataclass


CATEGORIES = {"business", "company", "partnership", "guarantee", "trustee"}
NUMBER_RE = re.compile(r"^\d{1,3}(?:,\d{3})*$|^\d+$")
ROLE_FIELDS = {
    "business": "proprietors",
    "company": "directors",
    "partnership": "partners",
    "guarantee": "directors",
    "trustee": "trustees",
}


@dataclass
class ValidationIssue:
    record_id: object
    company_name: str
    severity: str
    code: str
    message: str

    def to_dict(self):
        return asdict(self)


def issue(record, severity, code, message):
    return ValidationIssue(
        record.get("id", "?"), record.get("company_name", "<unnamed>"), severity, code, message
    )


def validate_person_list(record, field, issues):
    people = record.get(field)
    if not isinstance(people, list) or not people:
        issues.append(issue(record, "error", f"missing_{field}", f"At least one {field} entry is required."))
        return
    for index, person in enumerate(people, 1):
        if not isinstance(person, dict) or not str(person.get("name", "")).strip():
            issues.append(issue(record, "error", f"invalid_{field}_name", f"{field} entry {index} has no name."))
        if not isinstance(person, dict) or not str(person.get("address", "")).strip():
            issues.append(issue(record, "error", f"invalid_{field}_address", f"{field} entry {index} has no address."))


def parse_number(value):
    text = str(value or "").replace(",", "")
    return int(text) if text.isdigit() else None


def validate_record(record):
    issues = []
    for field in ("id", "company_name", "registration_number", "category", "registered_address", "incorporation_date"):
        if record.get(field) in (None, ""):
            issues.append(issue(record, "error", f"missing_{field}", f"Required field '{field}' is missing."))

    category = record.get("category")
    if category not in CATEGORIES:
        issues.append(issue(record, "error", "invalid_category", f"Unsupported category: {category!r}."))
        return issues

    if not str(record.get("main_object", "")).strip():
        issues.append(issue(record, "warning", "missing_main_object", "Main object is empty."))

    validate_person_list(record, ROLE_FIELDS[category], issues)

    if category == "company":
        capital = str(record.get("share_capital", ""))
        if not capital or not NUMBER_RE.match(capital):
            issues.append(issue(record, "error", "invalid_share_capital", "Share capital must be a numeric amount."))
        shareholders = record.get("shareholders")
        if not isinstance(shareholders, list) or not shareholders:
            issues.append(issue(record, "error", "missing_shareholders", "At least one shareholder is required."))
        else:
            amounts = []
            for index, shareholder in enumerate(shareholders, 1):
                if not str(shareholder.get("name", "")).strip():
                    issues.append(issue(record, "error", "invalid_shareholder_name", f"Shareholder {index} has no name."))
                shares = parse_number(shareholder.get("shares"))
                if shares is None:
                    issues.append(issue(record, "warning", "unknown_shareholding", f"Shareholder {index} has no numeric shareholding."))
                else:
                    amounts.append(shares)
            capital_value = parse_number(capital)
            if capital_value is not None and len(amounts) == len(shareholders) and sum(amounts) != capital_value:
                issues.append(issue(
                    record,
                    "warning",
                    "share_total_mismatch",
                    f"Shareholders total {sum(amounts):,}, but share capital is {capital_value:,}.",
                ))

    if category == "guarantee" and not record.get("guarantors"):
        issues.append(issue(record, "error", "missing_guarantors", "At least one guarantor is required."))

    return issues


def validate_records(records):
    issues = []
    ids = Counter(record.get("id") for record in records)
    registrations = Counter(str(record.get("registration_number", "")).strip() for record in records)
    for record in records:
        issues.extend(validate_record(record))
        if ids[record.get("id")] > 1:
            issues.append(issue(record, "error", "duplicate_id", f"ID {record.get('id')} appears more than once."))
        registration = str(record.get("registration_number", "")).strip()
        if registration and registrations[registration] > 1:
            issues.append(issue(record, "warning", "duplicate_registration", f"Registration number {registration} appears more than once."))
    return issues


def records_with_errors(issues):
    return {item.record_id for item in issues if item.severity == "error"}


def needs_ai_review(issues):
    review_codes = {
        "invalid_category", "missing_registered_address", "missing_incorporation_date",
        "missing_directors", "missing_proprietors", "missing_partners", "missing_trustees",
        "missing_guarantors", "missing_shareholders", "invalid_share_capital",
    }
    return {item.record_id for item in issues if item.code in review_codes}
