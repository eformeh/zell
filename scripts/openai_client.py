import openai

def convert_to_json(prompt, api_key):
    """
    Sends a prompt to OpenAI's API to convert data to JSON format.
    :param prompt: The prompt to send to OpenAI
    :param api_key: OpenAI API key
    :return: JSON formatted string
    """
    openai.api_key = api_key

    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=1500,
            n=1,
            stop=None,
            temperature=0.5,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        raise RuntimeError(f"An error occurred while communicating with OpenAI: {e}")
