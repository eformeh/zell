import json
import os
import urllib.error
import urllib.request


PERSON = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"name": {"type": "string"}, "address": {"type": "string"}},
    "required": ["name", "address"],
}
SHAREHOLDER = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"name": {"type": "string"}, "shares": {"type": "string"}},
    "required": ["name", "shares"],
}
RECORD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer"},
        "company_name": {"type": "string"},
        "registration_number": {"type": "string"},
        "category": {"type": "string", "enum": ["business", "company", "partnership", "guarantee", "trustee"]},
        "registered_address": {"type": "string"},
        "incorporation_date": {"type": "string"},
        "main_object": {"type": "string"},
        "share_capital": {"type": ["string", "null"]},
        "proprietors": {"type": "array", "items": PERSON},
        "directors": {"type": "array", "items": PERSON},
        "partners": {"type": "array", "items": PERSON},
        "trustees": {"type": "array", "items": PERSON},
        "guarantors": {"type": "array", "items": PERSON},
        "shareholders": {"type": "array", "items": SHAREHOLDER},
        "company_sec": {"anyOf": [PERSON, {"type": "null"}]},
        "trustee_sec": {"anyOf": [PERSON, {"type": "null"}]},
    },
    "required": [
        "id", "company_name", "registration_number", "category", "registered_address",
        "incorporation_date", "main_object", "share_capital", "proprietors", "directors",
        "partners", "trustees", "guarantors", "shareholders", "company_sec", "trustee_sec",
    ],
}


def available():
    return bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL"))


def extract_record(source_text, timeout=90):
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")
    if not api_key or not model:
        raise RuntimeError("AI fallback requires both OPENAI_API_KEY and OPENAI_MODEL.")

    instructions = (
        "Extract one Nigerian registration record. Preserve source wording. Normalize the category. "
        "Use the registered address when a person's address is missing. Format capital and shares "
        "as digit strings with comma separators. Use empty arrays or null for inapplicable fields."
    )
    payload = {
        "model": model,
        "store": False,
        "instructions": instructions,
        "input": source_text,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "registration_record",
                "strict": True,
                "schema": RECORD_SCHEMA,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc

    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return json.loads(content["text"])
    raise RuntimeError("OpenAI API response did not contain structured output.")
