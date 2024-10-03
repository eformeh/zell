import os
import pdfkit
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logging to track conversion status
logging.basicConfig(filename='bulk_conversion.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_html_files(folder_path):
    """
    Retrieves all HTML files from the specified folder.
    :param folder_path: The folder where HTML files are stored.
    :return: List of HTML filenames in the folder.
    """
    try:
        return [f for f in os.listdir(folder_path) if f.endswith('.html')]
    except OSError as e:
        logging.error(f"Error accessing folder: {folder_path} - {e}")
        raise RuntimeError(f"Error accessing folder: {folder_path} - {e}")

def html_to_pdf(html_file_path, output_pdf_path):
    """
    Converts an HTML file to PDF.
    :param html_file_path: Full path to the HTML file to be converted.
    :param output_pdf_path: Full path where the output PDF will be saved.
    """
    try:
        # Configure pdfkit with wkhtmltopdf binary path (adjust this path to match your installation)
        config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

        # Set options for PDF generation (e.g., allow local file access)
        options = {
            'enable-local-file-access': None,  # Allow access to local files for resources like images
            'no-stop-slow-scripts': None  # Continue rendering even with slow scripts
        }

        # Generate PDF from HTML file
        pdfkit.from_file(html_file_path, output_pdf_path, options=options, configuration=config)
        logging.info(f"Successfully generated PDF: {output_pdf_path}")
    except Exception as e:
        logging.error(f"Error converting {html_file_path} to PDF: {e}")
        raise RuntimeError(f"Error converting {html_file_path} to PDF: {e}")

def convert_html_files_to_pdf_concurrently(html_folder, output_folder, max_workers=6):
    """
    Converts HTML files to PDF concurrently.
    :param html_folder: Path to the folder containing HTML files.
    :param output_folder: Path to the folder where PDFs will be saved.
    :param max_workers: Maximum number of threads for concurrent execution.
    """
    try:
        # Ensure the output folder exists
        os.makedirs(output_folder, exist_ok=True)

        # Retrieve all HTML files in the folder
        html_files = get_html_files(html_folder)

        # Use ThreadPoolExecutor for concurrent conversion
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {}
            
            for html_file in html_files:
                html_file_path = os.path.join(html_folder, html_file)
                output_pdf_name = os.path.splitext(html_file)[0] + ".pdf"
                output_pdf_path = os.path.join(output_folder, output_pdf_name)

                # Submit the conversion task to the pool
                future = executor.submit(html_to_pdf, html_file_path, output_pdf_path)
                future_to_file[future] = html_file

            # Process the completed tasks
            for future in as_completed(future_to_file):
                html_file = future_to_file[future]
                try:
                    future.result()  # This will raise any exception caught during the task execution
                except Exception as e:
                    logging.error(f"Error occurred during conversion of {html_file}: {e}")

        logging.info("Bulk conversion completed successfully.")
        print("Bulk conversion completed successfully.")

    except Exception as e:
        logging.error(f"An error occurred during bulk conversion: {e}")
        print(f"An error occurred during bulk conversion: {e}")

if __name__ == "__main__":
    # Specify the folder containing the HTML files to convert
    html_folder = 'reports/html'

    # Specify the folder to save the generated PDFs
    output_folder = 'reports/pdfBulk'

    # Max out the threads for fast performance (6-8 for maximum speed)
    max_workers = 8  # Start with 6, increase to 8 if system handles it well

    # Perform the bulk HTML to PDF conversion concurrently
    convert_html_files_to_pdf_concurrently(html_folder, output_folder, max_workers)

