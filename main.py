import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool
from scripts.data_loader import load_data
from scripts.report_generator import render_template, save_html_report
from scripts.pdf_generator import html_to_pdf

logging.basicConfig(filename='process.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_html(entry):
    """
    Generates the HTML report for a given entry.
    """
    try:
        # Determine the category
        category = entry.get('category', 'company')

        # Generate HTML report
        html_report = render_template(entry, category)
        report_name = entry.get('company_name', 'report').replace(" ", "_")
        save_html_report(html_report, report_name)
        
        return report_name  # Return the report name for future PDF generation
    except Exception as e:
        logging.error(f"Error generating HTML for entry with ID {entry.get('id', 'unknown')}: {e}")
        print(f"Error generating HTML for entry with ID {entry.get('id', 'unknown')}: {e}")
        return None  # In case of error, return None


def generate_pdf(report_name):
    """
    Generates a PDF from the previously created HTML file.
    """
    try:
        if report_name:
            html_to_pdf(f"{report_name}.html", report_name)
    except Exception as e:
        logging.error(f"Error generating PDF for report {report_name}: {e}")
        print(f"Error generating PDF for report {report_name}: {e}")


def main():
    # Load all data from JSON file
    raw_data_path = 'data/raw_data.json'
    data = load_data(raw_data_path)

    # Ensure data is a list of entries
    if not isinstance(data, list):
        raise ValueError("Expected a list of entries in the JSON file.")
    
    # First phase: HTML generation (multithreading)
    report_names = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_html, entry) for entry in data]
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                report_names.append(result)

    # Second phase: PDF generation (multiprocessing)
    with Pool(processes=4) as pool:  # Adjust the number of processes based on available CPU cores
        pool.map(generate_pdf, report_names)


if __name__ == "__main__":
    main()
