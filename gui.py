import tkinter as tk
from tkinter import filedialog, messagebox
from scripts.data_loader import load_data
from scripts.report_generator import render_template, save_html_report
from scripts.pdf_generator import html_to_pdf
from bulkConverter import convert_html_files_to_pdf_concurrently

class ReportGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Report Generator")

        # Load Data Button
        self.load_data_button = tk.Button(root, text="Load Data", command=self.load_data)
        self.load_data_button.pack(pady=10)

        # Generate Reports Button
        self.generate_reports_button = tk.Button(root, text="Generate Reports", command=self.generate_reports)
        self.generate_reports_button.pack(pady=10)

        # Convert HTML to PDF Button
        self.convert_button = tk.Button(root, text="Convert HTML to PDF", command=self.convert_html_to_pdf)
        self.convert_button.pack(pady=10)

        # Status Label
        self.status_label = tk.Label(root, text="")
        self.status_label.pack(pady=10)

        self.data = None

    def load_data(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                self.data = load_data(file_path)
                self.status_label.config(text="Data loaded successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load data: {e}")

    def generate_reports(self):
        if not self.data:
            messagebox.showwarning("Warning", "Please load data first.")
            return

        try:
            for entry in self.data:
                category = entry.get('category', 'company')
                html_report = render_template(entry, category)
                report_name = entry.get('company_name', 'report').replace(" ", "_").replace(':', '_').replace("'", '_').replace("-","_").replace("/","_")
                save_html_report(html_report, report_name)
            self.status_label.config(text="Reports generated successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate reports: {e}")

    def convert_html_to_pdf(self):
        html_folder = filedialog.askdirectory(title="Select HTML Folder")
        output_folder = filedialog.askdirectory(title="Select Output PDF Folder")
        if html_folder and output_folder:
            try:
                convert_html_files_to_pdf_concurrently(html_folder, output_folder)
                self.status_label.config(text="HTML to PDF conversion completed.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to convert HTML to PDF: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReportGeneratorApp(root)
    root.mainloop()
