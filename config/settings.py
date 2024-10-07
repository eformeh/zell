# Path settings for templates, input, and output
TEMPLATES_DIR = 'templates/'
OUTPUT_HTML_DIR = 'reports/html/'
OUTPUT_PDF_DIR = 'reports/pdf/'
OPENAI_API_KEY= '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'
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
