from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import os
from config.settings import TEMPLATES_DIR, OUTPUT_HTML_DIR

def render_template(data, category):
    """
    Renders an HTML report using Jinja2 based on the data and category.
    :param data: Dictionary containing data to populate the template
    :param category: The type of entity (e.g., 'company', 'business')
    :return: Rendered HTML as a string
    """
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template_file = f"{category}.html"  # Choose the correct template based on category
    
    try:
        template = env.get_template(template_file)
    except TemplateNotFound:
        raise FileNotFoundError(f"Template file {template_file} not found in {TEMPLATES_DIR}.")
    except Exception as e:
        raise RuntimeError(f"An error occurred while loading the template: {e}")
    
    try:
        html_output = template.render(data)
    except Exception as e:
        raise RuntimeError(f"An error occurred while rendering the template: {e}")
    
    return html_output

def save_html_report(html_content, report_name):
    """
    Saves rendered HTML to the file system.
    :param html_content: The HTML content to save
    :param report_name: The name for the output HTML file
    """
    output_path = os.path.join(OUTPUT_HTML_DIR, f"{report_name}.html")
    
    try:
        with open(output_path, 'w') as file:
            file.write(html_content)
        print(f"HTML report generated: {output_path}")
    except OSError as e:
        raise RuntimeError(f"An error occurred while saving the HTML report to {output_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred while saving the HTML report: {e}")
