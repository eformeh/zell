# Path settings for templates, input, and output
TEMPLATES_DIR = 'templates/'
OUTPUT_HTML_DIR = 'reports/html/'
OUTPUT_PDF_DIR = 'reports/pdf/'

# PDFKit options
PDFKIT_OPTIONS = {
    'page-size': 'A4',
    'enable-local-file-access': '',
    'encoding': 'UTF-8',
     'no-outline': None,
    'no-images': '',
    'disable-javascript': '',
    'no-stop-slow-scripts': '',
    'no-background': '',
    'custom-header': [
        ('Accept-Encoding', 'gzip')
    ],
    'debug-javascript': ''
}
