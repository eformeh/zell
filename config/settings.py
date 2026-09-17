from pathlib import Path
import json


# Resolve paths from the project itself so generation works from any directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / 'templates'
STATIC_DIR = PROJECT_ROOT / 'static'
OUTPUT_HTML_DIR = PROJECT_ROOT / 'reports' / 'html'
OUTPUT_PDF_DIR = PROJECT_ROOT / 'reports' / 'pdf'
REPORT_SETTINGS_FILE = PROJECT_ROOT / 'config' / 'report_settings.json'
RUNS_DIR = PROJECT_ROOT / 'reports' / 'runs'


def load_report_settings():
    with REPORT_SETTINGS_FILE.open('r', encoding='utf-8') as stream:
        return json.load(stream)

# PDFKit options
PDFKIT_OPTIONS = {
    'page-size': 'A4',
    'enable-local-file-access': '',  # Allows local file access (CSS, images)
    'encoding': 'UTF-8',
    'no-outline': None,
    'disable-javascript': '',  # You can disable this if you're not using JavaScript in HTML
    'custom-header': [
        ('Accept-Encoding', 'gzip')
    ],
    'debug-javascript': ''  # Optional, helps debug JavaScript issues
}
