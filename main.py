import os
from scripts.data_loader import load_data
from scripts.report_generator import render_template, save_html_report
from scripts.pdf_generator import html_to_pdf
import logging

logging.basicConfig(filename='process.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_entry(entry):
    try:
        # Determine the category
        category = entry.get('category', 'company')
        
        # Generate HTML report
        html_report = render_template(entry, category)
        report_name = entry.get('company_name', 'report').replace(" ", "_")
        save_html_report(html_report, report_name)
        
        # Optionally generate PDF
        generate_pdf = True
        if generate_pdf:
            html_to_pdf(f"{report_name}.html", report_name)
    
    except Exception as e:
        print(f"Error processing entry with ID {entry.get('id', 'unknown')}: {e}")


def main():
    # Load all data from JSON file
    raw_data_path = 'data/raw_data.json'
    data = load_data(raw_data_path)
    
    # Ensure data is a list of entries
    if not isinstance(data, list):
        raise ValueError("Expected a list of entries in the JSON file.")
    
    # Process each entry
    for entry in data:
        process_entry(entry)

if __name__ == "__main__":
    main()
