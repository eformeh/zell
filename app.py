 # Flask Web Server (app.py)
from flask import Flask, request, jsonify, send_file, Response
import json
import os
import zipfile
import tempfile
from datetime import datetime
from main import main as generate_reports_main

app = Flask(__name__)

# Read the HTML file content
def get_html_content():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "HTML file not found. Please make sure index.html is in the same directory."

def format_date_for_zip(date_string):
    """
    Converts date from YYYY-MM-DD format to a readable format for zip filename
    """
    try:
        date_obj = datetime.strptime(date_string, '%Y-%m-%d')
        day = date_obj.day
        suffix = "th" if 4 <= day <= 20 or 24 <= day <= 30 else ["st", "nd", "rd"][day % 10 - 1]
        return date_obj.strftime(f"{day}{suffix} %B %Y")
    except ValueError:
        return date_string

@app.route('/', methods=['GET'])
def index():
    return get_html_content()

@app.route('/generate-reports', methods=['POST'])
def generate_reports():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Extract the JSON data and date
        json_data = data.get('jsonData')
        report_date = data.get('date')
        
        if not json_data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        # Parse the JSON data to validate it
        try:
            companies_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            return jsonify({'success': False, 'error': f'Invalid JSON: {str(e)}'}), 400
        
        # Ensure the reports directories exist
        os.makedirs('data', exist_ok=True)
        os.makedirs('reports/html', exist_ok=True)
        os.makedirs('reports/pdf', exist_ok=True)
        
        # Clear previous logs for this session
        if os.path.exists('process.log'):
            with open('process.log', 'w') as f:
                f.write('')  # Clear the log file
        
        # Save the JSON data to your expected file location
        with open('data/raw_data.json', 'w', encoding='utf-8') as f:
            json.dump(companies_data, f, indent=2, ensure_ascii=False)
        
        # Run your existing main function with the date
        generate_reports_main(report_date)
        
        return jsonify({
            'success': True, 
            'message': f'Successfully generated {len(companies_data)} reports',
            'count': len(companies_data),
            'date': report_date
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get-logs', methods=['GET'])
def get_logs():
    """
    Returns the content of process.log file
    """
    try:
        if os.path.exists('process.log'):
            with open('process.log', 'r', encoding='utf-8') as f:
                logs = f.read()
            return jsonify({'success': True, 'logs': logs})
        else:
            return jsonify({'success': True, 'logs': 'No logs found.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download-reports', methods=['POST'])
def download_reports():
    """
    Creates a zip file containing only the PDF reports and returns it for download
    """
    try:
        data = request.get_json()
        report_date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Format date for zip filename
        formatted_date = format_date_for_zip(report_date)
        zip_filename = f"SEARCH REPORT {formatted_date}.zip"
        
        # Create temporary zip file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add only PDF reports
            pdf_dir = 'reports/pdf'
            if os.path.exists(pdf_dir):
                pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
                
                if not pdf_files:
                    # If no PDF files found, raise an error
                    temp_zip.close()
                    os.unlink(temp_zip.name)
                    return jsonify({'success': False, 'error': 'No PDF reports found to download'}), 404
                
                # Add PDF files directly to the root of the zip (no subfolder)
                for filename in pdf_files:
                    file_path = os.path.join(pdf_dir, filename)
                    zipf.write(file_path, filename)  # filename only, no folder path
            else:
                temp_zip.close()
                os.unlink(temp_zip.name)
                return jsonify({'success': False, 'error': 'PDF reports directory not found'}), 404
        
        temp_zip.close()
        
        def remove_file(response):
            try:
                os.unlink(temp_zip.name)
            except Exception:
                pass
            return response
        
        return send_file(
            temp_zip.name,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8004)