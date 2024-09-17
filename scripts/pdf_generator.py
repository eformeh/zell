import pdfkit
import os
from config.settings import OUTPUT_HTML_DIR, OUTPUT_PDF_DIR, PDFKIT_OPTIONS
import subprocess

def html_to_pdf(html_file, output_pdf_name):
    html_path = os.path.join(OUTPUT_HTML_DIR, html_file)
    output_pdf = os.path.join(OUTPUT_PDF_DIR, f"{output_pdf_name}.pdf")
    
    try:
        # Configure pdfkit with options from settings.py
        config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')  # Update this if necessary
        
        # Log output from wkhtmltopdf
        command = [
            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
            html_path,
            output_pdf
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr)
        
        # Generate PDF
        pdfkit.from_file(html_path, output_pdf, options=PDFKIT_OPTIONS, configuration=config)
        print(f"PDF report generated: {output_pdf}")
    except OSError as e:
        raise RuntimeError(f"An error occurred while accessing files for PDF conversion: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred while converting HTML to PDF: {e}")
