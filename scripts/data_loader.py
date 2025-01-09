import json
import os
from .openai_client import convert_to_json

def load_data(file_path, prompt_file_path, api_key):
    """
    Loads data from a JSON file and converts it using OpenAI if necessary.
    :param file_path: Path to the data file (JSON format)
    :param prompt_file_path: Path to the prompt file
    :param api_key: OpenAI API key
    :return: Parsed JSON data as a list of dictionaries
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found.")
    
    if not os.path.exists(prompt_file_path):
        raise FileNotFoundError(f"{prompt_file_path} not found.")
    
    try:
        with open(file_path, 'r', encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from {file_path}: {e}")
    except UnicodeDecodeError as e:
        raise RuntimeError(f"Encoding error while loading data from {file_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred while loading data from {file_path}: {e}")
    
    if not isinstance(data, list):
        raise ValueError("Expected a list of entries in the JSON file.")
    
    try:
        with open(prompt_file_path, 'r', encoding="utf-8") as prompt_file:
            prompt = prompt_file.read()
    except Exception as e:
        raise RuntimeError(f"An error occurred while reading the prompt file: {e}")
    
    # Append the data to the prompt
    prompt += "\n\n" + json.dumps(data, indent=2)
    converted_data = convert_to_json(prompt, api_key)
    
    try:
        return json.loads(converted_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from OpenAI response: {e}")
