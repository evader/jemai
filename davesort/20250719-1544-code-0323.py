import sys
import json
import os
import requests # New import for making HTTP requests to Ollama

# --- Ollama Configuration (Local AI) ---
OLLAMA_API_URL = "http://localhost:11434/api/chat" # Ollama's API endpoint (inside Docker)
OLLAMA_MODEL_NAME = "llama3:8b" # The specific local model to use

# --- History File Management ---
CURRENT_CHAT_HISTORY_FILE = "current_synapz_og_chat.json" # Stores ongoing chat history for this local_og session
EXPORTED_LOG_FILE = "synapz_og_chat.json" # This is where you'll put SynapzOG's exported chat JSON

# --- Functions for History Management ---
def parse_external_log(file_path):
    """
    Parses a specific JSON export format (like the one from Google's chat exports, or our SynapzOG export)
    into the chat_history list format expected by the Ollama API.
    Excludes parts marked as "thought" (as in Google's chat exports).
    """
    parsed_history = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)

        messages = export_data.get('messages', [])

        for message in messages:
            content_obj = message.get('content', {})
            author = message.get('author') # Google export uses 'author' ("user", "bot")

            # Map 'author' from export to 'role' for Ollama API
            if author == 'bot':
                role = 'assistant' # Ollama expects 'assistant' for model responses
            elif author == 'user':
                role = 'user'
            else: # Skip unknown or non-standard roles/authors
                continue

            parts = content_obj.get('parts', [])
            
            full_text = ""
            for part in parts:
                # Only include text parts, and ensure 'thought' parts are excluded
                if 'text' in part and not part.get('thought', False):
                    full_text += part['text']
            
            if full_text: # Only add to history if there's actual extracted text content
                parsed_history.append({"role": role, "content": full_text}) # Ollama expects 'content'
        
        print(f"Loaded {len(parsed_history)} messages from external log '{file_path}'.", file=sys.stderr)
        return parsed_history
    except FileNotFoundError:
        print(f"External log '{file_path}' not found. Cannot import history.", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing external log '{file_path}'. Check JSON format: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred while parsing external log: {e}", file=sys.stderr)
        return []

def load_chat_history(history_file_path):
    """Loads chat history from the given JSON file."""
    if os.path.exists(history_file_path):
        with open(history_file_path, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
                if not isinstance(history, list):
                    print(f"Warning: {history_file_path} content is not a list. Starting new history.", file=sys.stderr)
                    return []
                print(f"Loaded {len(history)} messages from current chat history '{history_file_path}'.", file=sys.stderr)
                return history
            except json.JSONDecodeError as e:
                print(f"Warning: {history_file_path} is corrupted or empty: {e}. Starting new history.", file=sys.stderr)
                return []
    return []

def save_chat_history(history, history_file_path):
    """Saves chat history to the given JSON file."""
    with open(history_file_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# --- Main Logic ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python local_og.py \"Your message here\"")
        print(f"To initialize chat history from an external log, ensure '{EXPORTED_LOG_FILE}' exists in the script's directory and delete '{CURRENT_CHAT_HISTORY_FILE}'.")
        print(f"To start a fresh chat anytime, delete '{CURRENT_CHAT_HISTORY_FILE}'.")
        sys.exit(1)

    user_message = sys.argv[1] # Get message from command-line argument

    chat_history = []
    # Logic to decide initial history source:
    if os.path.exists(CURRENT_CHAT_HISTORY_FILE):
        chat_history = load_chat_history(CURRENT_CHAT_HISTORY_FILE)
    elif os.path.exists(EXPORTED_LOG_FILE):
        print(f"'{CURRENT_CHAT_HISTORY_FILE}' not found. Attempting to initialize from '{EXPORTED_LOG_FILE}'...", file=sys.stderr)
        chat_history = parse_external_log(EXPORTED_LOG_FILE)
        if not chat_history:
            print("Failed to load external log or it was empty. Starting a fresh chat.", file=sys.stderr)
            chat_history = []
    else:
        print("No existing chat history or external log found. Starting a fresh chat.", file=sys.stderr)
        chat_history = []
    
    # Add the current user message to the history in Ollama format
    chat_history.append({"role": "user", "content": user_message})

    # Prepare messages for Ollama API, which expects 'content' not 'parts' in messages list
    messages_for_ollama = []
    for turn in chat_history:
        # Extract text from 'parts' (our internal history format), or use 'content' if history object already has it
        content_text = ""
        if 'content' in turn: # If already in Ollama format
            content_text = turn['content']
        elif 'parts' in turn and isinstance(turn['parts'], list) and len(turn['parts']) > 0 and 'text' in turn['parts'][0]:
            content_text = turn['parts'][0]['text']
        
        # Ensure role is 'assistant' for model, as Ollama uses this
        role_ollama = 'assistant' if turn['role'] == 'model' else turn['role']
        
        messages_for_ollama.append({"role": role_ollama, "content": content_text})

    # Construct the request payload for Ollama
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "messages": messages_for_ollama,
        "stream": True # Request streaming output
    }

    print(f"Sending message to local Ollama ({OLLAMA_MODEL_NAME})... ", file=sys.stderr) # Print to stderr for cleaner stdout output

    # --- Send the message and get a streamed response from Ollama ---
    collected_ai_response = "" # Accumulate AI's response text
    try:
        with requests.post(OLLAMA_API_URL, json=payload, stream=True) as response:
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            for chunk in response.iter_content(chunk_size=None):
                if chunk:
                    try:
                        decoded_chunk = chunk.decode('utf-8')
                        for line in decoded_chunk.splitlines():
                            if line.strip():
                                data = json.loads(line)
                                if "content" in data["message"]:
                                    text_content = data["message"]["content"]
                                    print(text_content, end="") # Print each chunk as it arrives to stdout
                                    collected_ai_response += text_content
                                if data.get("done"): # Check for 'done' status indicating end of stream
                                    break
                    except json.JSONDecodeError:
                        # This can happen with incomplete JSON chunks during streaming.
                        # Do nothing, wait for the next chunk to complete the JSON.
                        pass
        print("\n", file=sys.stderr) # New line after the streamed response finishes in stderr
        
        # Add the AI's accumulated response to the chat history (in 'parts' format for consistency with Google exports)
        chat_history.append({"role": "model", "parts": [{"text": collected_ai_response}]})

        # Save the updated chat history for the next run
        save_chat_history(chat_history, CURRENT_CHAT_HISTORY_FILE)

    except requests.exceptions.ConnectionError as e:
        print(f"\nError: Could not connect to Ollama. Is the '{OLLAMA_MODEL_NAME}' model downloaded? Is `jemai_ollama` running?", file=sys.stderr)
        print(f"Connection error details: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"\nNetwork or Ollama API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred during AI interaction: {e}", file=sys.stderr)
        sys.exit(1)