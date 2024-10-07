import openai
import os
import json

# Load API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_formatted_json(data):
    """
    Sends a prompt to OpenAI API with the data and receives a formatted JSON response.
    """
    prompt = f"""
    Please format the following data as JSON:
    Category: Specify whether the entity is a business, company, partnership, guarantee, or trustee.
    
    Fields:
    - id
    - company_name
    - registration_number
    - category ("business", "company", "partnership", "guarantee", "trustee")
    - registered_address
    - incorporation_date
    - main_object
    - share capital (for company)
    - proprietors (for business) or directors (for company and guarantee) or partners (for partnership) or trustees (for trustee)
    - company_sec (for company and guarantee)
    - trustee_sec (for trustee)
    - shareholders (for company)
    - trustees (for trustee)
    - guarantors (for guarantee)
    
    Detailed constraints:
    - For business, include proprietors as an array of objects with name and address.
    - For company, include directors as an array of objects with name and address as well as shareholders as an array of objects with name and shares (convert share numbers into numeric form, e.g. 1m becomes 1,000,000).
    - For guarantee, include directors as an array of objects with name and address.
    - For partnership, include partners as an array of objects with name and address.
    - For trustee, include trustees as an array of objects with name and address.
    - If the address for any entity is not provided, use the company registered address as their address.
    
    Data to be formatted: {data}
    """

    # Make the request to the OpenAI API
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0
    )

    return response.choices[0].text.strip()

def read_data_from_file(file_path):
    """
    Reads the input data from a text file and returns it.
    """
    try:
        with open(file_path, 'r') as file:
            data = file.read()
        return data
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def save_json_to_file(data, output_file):
    """
    Saves formatted JSON data to a file.
    """
    try:
        with open(output_file, 'w') as file:
            json.dump(data, file, indent=4)
        print(f"Formatted JSON saved to {output_file}.")
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    # File path to the input data text file (assuming it contains JSON-like data)
    input_file_path = 'data/input_data.txt'
    output_file_path = 'data/raw_data.json'

    # Read the data from the file
    data_from_file = read_data_from_file(input_file_path)

    if data_from_file:
        # Send data to the OpenAI API for formatting
        formatted_json = get_formatted_json(data_from_file)
        print("Formatted JSON received.")

        # Save formatted JSON to the raw_data.json file
        save_json_to_file(formatted_json, output_file_path)
    else:
        print("Failed to retrieve data from the input file.")
