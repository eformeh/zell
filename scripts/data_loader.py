import json
import os

def load_data(file_path):
    """
    Loads data from a JSON file.
    :param file_path: Path to the data file (JSON format)
    :return: Parsed JSON data as a list of dictionaries
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found.")
    
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from {file_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred while loading data from {file_path}: {e}")
    
    if not isinstance(data, list):
        raise ValueError("Expected a list of entries in the JSON file.")
    
    return data
