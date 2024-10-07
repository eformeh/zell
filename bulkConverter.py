import os
import pdfkit
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(filename='bulk_conversion.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_html_files(folder_path):
    """
    Retrieves all HTML files from the specified folder.
    """
    try:
        return [f for f in os.listdir(folder_path) if f.endswith('.html')]
    except OSError as e:
        logging.error(f"Error accessing folder: {folder_path} - {e}")
        raise RuntimeError(f"Error accessing folder: {folder_path} - {e}")

def html_to_pdf(html_file_path, output_pdf_path):
    """
    Converts an HTML file to PDF.
    """
    try:
        config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
        options = {
            'enable-local-file-access': None,
            'no-stop-slow-scripts': None
        }
        pdfkit.from_file(html_file_path, output_pdf_path, options=options, configuration=config)
        logging.info(f"Successfully generated PDF: {output_pdf_path}")
    except Exception as e:
        logging.error(f"Error converting {html_file_path} to PDF: {e}")
        raise RuntimeError(f"Error converting {html_file_path} to PDF: {e}")

def convert_html_files_to_pdf_concurrently(html_folder, output_folder, max_workers=6):
    """
    Converts HTML files to PDF concurrently.
    """
    try:
        os.makedirs(output_folder, exist_ok=True)
        html_files = get_html_files(html_folder)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {}
            for html_file in html_files:
                html_file_path = os.path.join(html_folder, html_file)
                output_pdf_name = os.path.splitext(html_file)[0] + ".pdf"
                output_pdf_path = os.path.join(output_folder, output_pdf_name)
                future = executor.submit(html_to_pdf, html_file_path, output_pdf_path)
                future_to_file[future] = html_file

            for future in as_completed(future_to_file):
                html_file = future_to_file[future]
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error during conversion of {html_file}: {e}")

        logging.info("Bulk conversion completed successfully.")
        print("Bulk conversion completed successfully.")

    except Exception as e:
        logging.error(f"An error occurred during bulk conversion: {e}")
        print(f"An error occurred during bulk conversion: {e}")

if __name__ == "__main__":
    html_folder = 'reports/html'
    output_folder = 'reports/pdfBulk'
    max_workers = 8
    convert_html_files_to_pdf_concurrently(html_folder, output_folder, max_workers)
