import requests
import json



def main(messages, tools = None):
    url = "http://localhost:11434/api/chat"

    payload = {
        "model": "llama3.1:latest",
        "messages":messages,
        "stream": False,
        "tools": tools
    }

    try:
        # Send a POST request with the JSON data
        response = requests.post(url, json=payload)
        return response

    except requests.exceptions.ConnectionError as e:
        print(f"Failed to connect to the Ollama server.")
        print(f"Please ensure the Ollama server is running. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main(query="hi")



