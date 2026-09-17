# Agent Instructions for This Project

This project generates CAC-style search reports from structured JSON data and HTML templates. When the user provides a `.txt` file or pasted structured registration data, convert it into valid JSON that matches the schema below. When the user asks to change report/template dates, update the relevant HTML templates to the exact date specified.

## Main Jobs

1. Convert supplied registration data into JSON.
2. Normalize categories to one of:
   - `business`
   - `company`
   - `partnership`
   - `guarantee`
   - `trustee`
3. Update template dates when requested.
4. Keep output compatible with `data/raw_data.json` and the templates in `templates/`.

Do not run report generation unless the user asks. Usually the user wants the JSON prepared so they can run the system themselves.

## JSON Output

Return a JSON array when there is more than one entity. Return one JSON object only if the user explicitly asks for a single object.

Use these common fields for every entity:

```json
{
  "id": 1,
  "company_name": "",
  "registration_number": "",
  "category": "",
  "registered_address": "",
  "incorporation_date": "",
  "main_object": ""
}
```

Keep `registration_number` as a string. Keep `share_capital` and `shares` as strings containing only the numeric amount with comma separators, for example `"1,000,000"`.

## Category-Specific Fields

### Business

Use category `business`.

```json
{
  "proprietors": [
    {
      "name": "",
      "address": ""
    }
  ]
}
```

If the source says `business name`, normalize it to `business`.

### Company

Use category `company`.

```json
{
  "share_capital": "1,000,000",
  "directors": [
    {
      "name": "",
      "address": ""
    }
  ],
  "shareholders": [
    {
      "name": "",
      "shares": "1,000,000"
    }
  ],
  "company_sec": null
}
```

`company_sec` should be either `null` or an object:

```json
{
  "name": "",
  "address": ""
}
```

### Partnership

Use category `partnership`.

```json
{
  "partners": [
    {
      "name": "",
      "address": ""
    }
  ]
}
```

### Guarantee

Use category `guarantee`.

```json
{
  "directors": [
    {
      "name": "",
      "address": ""
    }
  ],
  "guarantors": [
    {
      "name": "",
      "address": ""
    }
  ],
  "company_sec": null
}
```

If guarantor addresses are not supplied, use the registered address.

### Trustee

Use category `trustee`.

```json
{
  "trustees": [
    {
      "name": "",
      "address": ""
    }
  ],
  "trustee_sec": null
}
```

`trustee_sec` should be either `null` or an object:

```json
{
  "name": "",
  "address": ""
}
```

## Missing Addresses

If an address is missing for any person or role, use the entity's `registered_address`.

This applies to:

- proprietors
- directors
- partners
- trustees
- guarantors
- company secretaries
- trustee secretaries

## Share and Capital Conversion

For `share_capital` and shareholder `shares`, extract only the numeric amount and format it with commas.

Examples:

- `1m` -> `"1,000,000"`
- `1 million` -> `"1,000,000"`
- `500000` -> `"500,000"`
- `10,000,000` -> `"10,000,000"`
- `N1,000,000` -> `"1,000,000"`

Do not include words like `shares`, `ordinary shares`, `NGN`, `Naira`, or currency symbols in the JSON value.

## Dates

For `incorporation_date`, preserve the source date style unless the user requests a specific format. Existing data commonly uses formats like:

- `MAR 25, 2024`
- `JUL 3, 2024`
- `24th December 2025`

When the user asks to update template dates, update every visible report/search date in the relevant templates. If no template category is specified, update all category templates:

- `templates/business.html`
- `templates/company.html`
- `templates/partnership.html`
- `templates/guarantee.html`
- `templates/trustee.html`

The report date usually appears in two places:

- the letter address block near the top
- the `Date of Search:` table row

Use the exact date text provided by the user, for example `24th December 2025`.

## Output Quality Rules

- Output valid JSON only when the user asks for JSON.
- Do not wrap JSON in prose or Markdown fences unless the user asks.
- Use arrays for people lists even when there is only one person.
- Use `null` for missing `company_sec` or `trustee_sec`, not `"Nil"`.
- Preserve names, addresses, and main objects as given, but trim obvious extra spaces.
- Keep field names in snake_case exactly as used above.
- Avoid inventing data. If a required field is truly absent, use an empty string, except person addresses where the registered address should be used.

## File Placement

When asked to save converted data for the app, place it in:

```text
data/raw_data.json
```

The file must contain a JSON array because `scripts/data_loader.py` expects a list.

