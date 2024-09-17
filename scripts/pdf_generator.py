import pdfkit
import os
from config.settings import OUTPUT_HTML_DIR, OUTPUT_PDF_DIR, PDFKIT_OPTIONS
import subprocess

def html_to_pdf(html_file, output_pdf_name):
    """
    Converts an HTML file to a PDF.
    :param html_file: Path to the HTML file to be converted
    :param output_pdf_name: Name for the output PDF
    """
    html_path = os.path.join(OUTPUT_HTML_DIR, html_file)
    output_pdf = os.path.join(OUTPUT_PDF_DIR, f"{output_pdf_name}.pdf")
    
    try:
        # Configure pdfkit with wkhtmltopdf binary path
        config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

        # Add absolute paths to the options
        options = PDFKIT_OPTIONS.copy()
        options.update({
            'enable-local-file-access': None,  # Enable local file access
            'no-stop-slow-scripts': None
        })
        
        # Generate PDF using pdfkit
        pdfkit.from_file(html_path, output_pdf, options=options, configuration=config)
        print(f"PDF report generated: {output_pdf}")
    except OSError as e:
        raise RuntimeError(f"An error occurred while accessing files for PDF conversion: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred while converting HTML to PDF: {e}")
