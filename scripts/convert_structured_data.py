import json
import re
import sys
from pathlib import Path


DATE_RE = re.compile(r"^(?:Date of Registration\s*-\s*)?([A-Za-z]{3}\s+\d{1,2},\s+\d{4})$", re.I)
CAPITAL_RE = re.compile(r"^(\d[\d,]*(?:\.\d+)?)(m)?$", re.I)


def clean(value):
    return re.sub(r"\s+", " ", value.strip())


def amount(value):
    match = CAPITAL_RE.match(clean(value))
    if not match:
        digits = re.sub(r"\D", "", value)
        return f"{int(digits):,}" if digits else ""
    number = float(match.group(1).replace(",", ""))
    if match.group(2):
        number *= 1_000_000
    return f"{int(number):,}"


def split_records(text):
    matches = list(re.finditer(r"(?m)^\s*(\d+)\.\s+(.+?)\s*$", text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end]
        lines = [clean(line) for line in body.splitlines() if clean(line)]
        yield int(match.group(1)), clean(match.group(2)), lines


def find_date(lines):
    for index, line in enumerate(lines):
        match = DATE_RE.match(line)
        if match:
            return index, match.group(1)
    return -1, ""


def parse_business(record_id, name, lines):
    registration = re.sub(r"^RC\s*-\s*", "", lines[0], flags=re.I)
    date_index, date = find_date(lines)
    before = lines[1:date_index]
    after = lines[date_index + 1:]

    if record_id == 2:
        address = after[1] if len(after) > 1 else ""
        main_object = after[0] if after else ""
        people = after[2:]
    elif record_id == 15:
        main_object = before[0]
        address = clean(" ".join(before[1:])).lstrip(",")
        people = after
    else:
        address = clean(" ".join(before))
        main_object = after[0] if after else ""
        people = after[1:]

    main_object = re.sub(r"^Nature of Business\s*-\s*", "", main_object, flags=re.I)
    return {
        "id": record_id,
        "company_name": name,
        "registration_number": registration,
        "category": "business",
        "registered_address": address,
        "incorporation_date": date,
        "main_object": main_object,
        "proprietors": [{"name": person, "address": address} for person in people],
    }


def marker_index(lines, pattern, start=0):
    for index in range(start, len(lines)):
        if re.search(pattern, lines[index], re.I):
            return index
    return len(lines)


def parse_named_people(lines, default_address):
    people = []
    index = 0
    while index < len(lines):
        if lines[index].upper() != "NAME" or index + 1 >= len(lines):
            index += 1
            continue
        name = lines[index + 1]
        address = default_address
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].upper() != "NAME":
            if lines[cursor].upper() == "CONTACT ADDRESS" and cursor + 1 < len(lines):
                address = lines[cursor + 1]
                break
            cursor += 1
        if not any(person["name"] == name for person in people):
            people.append({"name": name, "address": address})
        index += 2
    return people


def parse_shareholders(lines):
    shareholders = []
    for line in lines:
        share_match = re.match(
            r"^(.*?)(?:\s+(?:ORDINARY|PREFERENCE)\s+(\d[\d,]*)|\s+(\d[\d,]*)\s+(?:ORDINARY|PREFERENCE)|\s+(\d[\d,]*))$",
            line,
            re.I,
        )
        if not share_match:
            continue
        raw_shares = next(value for value in share_match.groups()[1:] if value)
        shares = amount(raw_shares)
        prefix = share_match.group(1).strip()
        prefix = re.sub(r"^\d+\s+", "", prefix)
        prefix = re.sub(r"\s+(?:ORDINARY|PREFERENCE)\s*$", "", prefix, flags=re.I)
        prefix = re.sub(r"\s+\S+@\S+\s*$", "", prefix)
        if prefix:
            shareholders.append({"name": prefix, "shares": shares})
    return shareholders


def parse_secretary(lines, default_address):
    if not lines or any(re.match(r"No sec", line, re.I) for line in lines):
        return None
    named = parse_named_people(lines, default_address)
    if named:
        return named[0]
    values = [line for line in lines if not re.search(r"Secretary", line, re.I)]
    if not values:
        return None
    return {"name": values[0], "address": values[1] if len(values) > 1 else default_address}


def parse_company(record_id, name, lines):
    registration = lines[0]
    date_index, date = find_date(lines)
    address = clean(" ".join(lines[2:date_index]))
    director_index = marker_index(lines, r"Director(?:'s)? Details", date_index + 1)
    shareholder_index = marker_index(lines, r"Shareholders?", date_index + 1)
    secretary_index = marker_index(lines, r"Secretary", shareholder_index + 1)
    no_sec_index = marker_index(lines, r"^No sec", shareholder_index + 1)
    section_end = min(secretary_index, no_sec_index, len(lines))

    pre_directors = lines[date_index + 1:director_index]
    capital_candidates = [line for line in lines[date_index + 1:shareholder_index] if CAPITAL_RE.match(line)]
    capital_line = next((line for line in capital_candidates if line.lower().endswith("m")), "")
    if not capital_line:
        capital_line = next((line for line in pre_directors if CAPITAL_RE.match(line)), "")
    main_lines = [line for line in pre_directors if not CAPITAL_RE.match(line)]
    main_object = clean(" ".join(main_lines))

    directors = parse_named_people(lines[director_index + 1:shareholder_index], address)
    shareholders = parse_shareholders(lines[shareholder_index + 1:section_end])
    if not shareholders and shareholder_index < len(lines) and re.search(r"Directors as Shareholders", lines[shareholder_index], re.I):
        shareholders = [{"name": director["name"], "shares": ""} for director in directors]

    secretary_lines = lines[section_end:] if section_end < len(lines) else []
    return {
        "id": record_id,
        "company_name": name,
        "registration_number": registration,
        "category": "company",
        "registered_address": address,
        "incorporation_date": date,
        "main_object": main_object,
        "share_capital": amount(capital_line),
        "directors": directors,
        "company_sec": parse_secretary(secretary_lines, address),
        "shareholders": shareholders,
    }


def parse_trustee(record_id, name, lines):
    registration = lines[0]
    date_index, date = find_date(lines)
    address = clean(" ".join(lines[2:date_index]))
    trustee_index = marker_index(lines, r"^Trustees?$")
    names = [re.sub(r"^\d+\s+", "", line) for line in lines[trustee_index + 1:]]
    return {
        "id": record_id,
        "company_name": name,
        "registration_number": registration,
        "category": "trustee",
        "registered_address": address,
        "incorporation_date": date,
        "main_object": "",
        "trustees": [{"name": trustee, "address": address} for trustee in names],
        "trustee_sec": None,
    }


def convert(text):
    output = []
    for record_id, name, lines in split_records(text):
        category = lines[1].upper() if len(lines) > 1 else ""
        if "INCORPORATED TRUSTEE" in category:
            output.append(parse_trustee(record_id, name, lines))
        elif category == "COMPANY":
            output.append(parse_company(record_id, name, lines))
        else:
            output.append(parse_business(record_id, name, lines))
    return output


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: convert_structured_data.py INPUT OUTPUT")
    source = Path(sys.argv[1]).read_text(encoding="utf-8-sig")
    records = convert(source)
    Path(sys.argv[2]).write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Converted {len(records)} records to {sys.argv[2]}")


if __name__ == "__main__":
    main()
