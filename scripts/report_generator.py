from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import os
from pathlib import Path

from config.settings import TEMPLATES_DIR, STATIC_DIR, OUTPUT_HTML_DIR
from scripts.report_config import build_report_settings


ENV = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

def render_template(data, category, report_settings=None):
    """
    Renders an HTML report using Jinja2 based on the data and category.
    :param data: Dictionary containing data to populate the template
    :param category: The type of entity (e.g., 'company', 'business')
    :return: Rendered HTML as a string
    """
    template_file = f"{category}.html"  # Choose the correct template based on category
    
    try:
        template = ENV.get_template(template_file)
    except TemplateNotFound:
        raise FileNotFoundError(f"Template file {template_file} not found in {TEMPLATES_DIR}.")
    except Exception as e:
        raise RuntimeError(f"An error occurred while loading the template: {e}")
    
    try:
        context = dict(data)
        report = report_settings or build_report_settings()
        assets = report["assets"]
        context.update({
            'report': report,
            'stylesheet_uri': (STATIC_DIR / 'css' / 'styles.css').as_uri(),
            'logo_uri': (STATIC_DIR / assets['logo']).resolve().as_uri(),
            'signature_uri': (STATIC_DIR / assets['signature']).resolve().as_uri(),
            'stamp_beside_uri': (STATIC_DIR / assets['stamp_beside']).resolve().as_uri(),
            'stamp_below_uri': (STATIC_DIR / assets['stamp_below']).resolve().as_uri(),
        })
        html_output = template.render(context)
    except Exception as e:
        raise RuntimeError(f"An error occurred while rendering the template: {e}")
    
    return html_output

def save_html_report(html_content, report_name, output_dir=None):
    """
    Saves rendered HTML to the file system.
    :param html_content: The HTML content to save
    :param report_name: The name for the output HTML file
    """
    output_path = Path(output_dir or OUTPUT_HTML_DIR) / f"{report_name}.html"
    
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8', newline='\n') as file:
            file.write(html_content)
    except OSError as e:
        raise RuntimeError(f"An error occurred while saving the HTML report to {output_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred while saving the HTML report: {e}")
