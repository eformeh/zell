import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool
from scripts.data_loader import load_data
from scripts.report_generator import render_template, save_html_report
from scripts.pdf_generator import html_to_pdf
from bulkConverter import convert_html_files_to_pdf_concurrently

logging.basicConfig(filename='process.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_html(entry):
    """
    Generates the HTML report for a given entry.
    """
    try:
        category = entry.get('category', 'company')
        html_report = render_template(entry, category)
        report_name = entry.get('company_name', 'report').replace(" ", "_")
        save_html_report(html_report, report_name)
        return report_name
    except Exception as e:
        logging.error(f"Error generating HTML for entry with ID {entry.get('id', 'unknown')}: {e}")
        return None

def main():
    # Step 1: Load data from raw_data.json
    raw_data_path = 'data/raw_data.json'
    data = load_data(raw_data_path)

    if not isinstance(data, list):
        raise ValueError("Expected a list of entries in the JSON file.")

    # Step 2: Generate HTML reports using multithreading
    report_names = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_html, entry) for entry in data]
        for future in as_completed(futures):
            result = future.result()
            if result:
                report_names.append(result)

    # Step 3: Convert HTML to PDF using bulk conversion
    html_folder = 'reports/html'
    output_folder = 'reports/pdfBulk'
    convert_html_files_to_pdf_concurrently(html_folder, output_folder)

if __name__ == "__main__":
    main()
