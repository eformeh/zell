# CAC Report Generator

This project converts structured registration text into validated JSON, previews issues in the terminal, and generates organized HTML and PDF search reports.

## Recommended command

```powershell
.\venv\Scripts\python.exe run.py "C:\path\to\structured data.txt"
```

The command performs rule-based conversion, validation, terminal approval, HTML generation, and PDF generation. Each run is saved under `reports/runs/<timestamp>/` with its source input, normalized JSON, effective report settings, HTML, PDFs, failure log, and summary.

The original entry point also uses the new workflow:

```powershell
.\venv\Scripts\python.exe main.py
```

With no arguments, `main.py` reads `data/raw_data.json`.

## Date and recipient overrides

```powershell
.\venv\Scripts\python.exe run.py "C:\path\to\data.txt" `
  --date 2026-10-03 `
  --recipient "Zenith Bank Plc" `
  --recipient-title "The Branch Manager" `
  --recipient-address "Plot 1, Test Avenue" `
  --recipient-address "Lagos State"
```

Dates such as `today`, `2026-10-03`, and `03/10/2026` are automatically displayed as `3rd October 2026`. Edit `config/report_settings.json` to change persistent recipient, firm, asset, worker, or retry defaults.

## Approval and validation

The default workflow shows all errors and warnings before asking for approval. Blocking records are skipped; warnings remain visible but can be approved.

Useful options:

```text
--validate-only   Preview validation without creating output
--yes             Approve valid records without prompting
--no-pdf          Generate data and HTML only
--ids 1,29,71     Process selected record IDs
--run-name NAME   Add a readable suffix to the run folder
```

## Optional AI fallback

The AI fallback is opt-in and only reviews structurally invalid records. Valid records stay in the rule-based offline path.

```powershell
$env:OPENAI_API_KEY="your-api-key"
$env:OPENAI_MODEL="your-structured-output-model"
.\venv\Scripts\python.exe run.py "C:\path\to\data.txt" --ai
```

Without `--ai`, no registration data is sent to an external service. The fallback uses the OpenAI Responses API with a strict JSON schema.
