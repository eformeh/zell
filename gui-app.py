import tkinter as tk
from tkinter import messagebox
import json
import os
from main import main  # Ensure this connects to your existing pipeline
from scripts.data_loader import load_data
import logging

# Configure logging
logging.basicConfig(filename='gui_process.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_json_data():
    try:
        # Get JSON data from text area
        json_data = json_text.get("1.0", tk.END).strip()
        if not json_data:
            raise ValueError("No JSON data entered.")
        
        # Validate JSON format
        data = json.loads(json_data)
        
        if not isinstance(data, list):
            raise ValueError("Expected a list of dictionaries for bulk JSON data.")

        # Save the JSON data to a temporary file
        temp_json_path = 'temp_data.json'
        with open(temp_json_path, 'w', encoding='utf-8') as temp_file:
            json.dump(data, temp_file, indent=4)
        
        # Run the main processing pipeline
        load_data(temp_json_path)  # Ensure this works for your bulk input
        main()  # Call your existing main function to process the data

        messagebox.showinfo("Success", "Processing complete! Reports generated.")
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON input: {e}")
        messagebox.showerror("Error", f"Invalid JSON format: {e}")
    except Exception as e:
        logging.error(f"Error during processing: {e}")
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

# GUI Setup
root = tk.Tk()
root.title("JSON to PDF Bulk Report Generator")

# JSON Input Section
tk.Label(root, text="Enter or Paste JSON Data Below:").pack(pady=5)
json_text = tk.Text(root, height=20, width=80)
json_text.pack(padx=10, pady=5)

# Process Button
tk.Button(root, text="Generate Reports", command=process_json_data, bg="green", fg="white").pack(pady=10)

root.mainloop()
