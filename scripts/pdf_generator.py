import pdfkit
import os
import time
from pathlib import Path
from config.settings import OUTPUT_HTML_DIR, OUTPUT_PDF_DIR, PDFKIT_OPTIONS
from config.settings import load_report_settings


def convert_html_to_pdf(html_path, output_pdf, retries=None, wkhtmltopdf_path=None):
    html_path = Path(html_path)
    output_pdf = Path(output_pdf)
    generation = load_report_settings()["generation"]
    retries = generation["pdf_retries"] if retries is None else retries
    wkhtmltopdf_path = wkhtmltopdf_path or generation["wkhtmltopdf_path"]
    if not Path(wkhtmltopdf_path).is_file():
        raise FileNotFoundError(f"wkhtmltopdf was not found at {wkhtmltopdf_path}")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    temporary_pdf = output_pdf.with_suffix(".partial.pdf")
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    options = PDFKIT_OPTIONS.copy()
    options.update({'enable-local-file-access': None, 'no-stop-slow-scripts': None, 'quiet': ''})
    last_error = None
    for attempt in range(retries + 1):
        try:
            temporary_pdf.unlink(missing_ok=True)
            pdfkit.from_file(str(html_path), str(temporary_pdf), options=options, configuration=config)
            content = temporary_pdf.read_bytes()
            if len(content) < 1000 or not content.startswith(b"%PDF"):
                raise RuntimeError("Generated PDF is empty or invalid.")
            temporary_pdf.replace(output_pdf)
            return output_pdf
        except Exception as exc:
            last_error = exc
            temporary_pdf.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"PDF generation failed after {retries + 1} attempts: {last_error}")

def html_to_pdf(html_file, output_pdf_name):
    """
    Converts an HTML file to a PDF.
    :param html_file: Path to the HTML file to be converted
    :param output_pdf_name: Name for the output PDF
    """
    html_path = Path(OUTPUT_HTML_DIR) / html_file
    output_pdf = Path(OUTPUT_PDF_DIR) / f"{output_pdf_name}.pdf"
    return convert_html_to_pdf(html_path, output_pdf)
