import sys
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, SafetySetting
import json
import os # For checking if the file exists

# --- Configuration ---
PROJECT_ID = "vertex-465223"
LOCATION = "global"
MODEL_NAME = "gemini-2.5-flash"

# File for the ongoing chat history of YOUR SCRIPT's sessions (will be managed by this script)
CURRENT_CHAT_HISTORY_FILE = "current_chat_history_for_imported_chat.json" # Renamed for clarity!
# File for the history you're importing (e.g., this conversation's export JSON)
EXPORTED_LOG_FILE = "exported_chat.json" # Make sure your conversation export is named this

# --- Initialize Vertex AI ---
vertexai.init(project=PROJECT_ID, location=LOCATION)

# --- Instantiate the GenerativeModel ---
model = GenerativeModel(MODEL_NAME)

# --- Define Generation Configuration ---
generation_config = GenerationConfig(
    max_output_tokens=65535,
    temperature=1,
    top_p=1,
)

# --- Define Safety Settings ---
safety_settings = [
    SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
    SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
    SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
]

# --- Functions for History Management ---
def parse_external_log(file_path):
    """
    Parses a specific JSON export format (like the one from our chat)
    into the chat_history list format expected by the Vertex AI API.
    Excludes parts marked as "thought".
    """
    parsed_history = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)

        messages = export_data.get('messages', [])

        for message in messages:
            content_obj = message.get('content', {})
            role = content_obj.get('role')

            # Remap 'bot' role to 'model' for Vertex AI API
            if role == 'bot':
                role = 'model'
            elif role != 'user' and role != 'model': # Skip unknown or non-standard roles
                continue

            parts = content_obj.get('parts', [])
            
            full_text = ""
            for part in parts:
                # Only include text parts, and ensure 'thought' parts are excluded
                if 'text' in part and not part.get('thought', False): # .get('thought', False) handles if 'thought' key is missing
                    full_text += part['text']
            
            if full_text: # Only add to history if there's actual extracted text content
                parsed_history.append({"role": role, "parts": [{"text": full_text}]})
        
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
        # ensure_ascii=False crucial for properly saving non-ASCII characters (like emojis, non-English text)
        json.dump(history, f, indent=2, ensure_ascii=False)

# --- Main Logic ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ask_imported_chat.py \"Your message here\"") # Updated usage message
        print(f"To initialize chat history from an external log, ensure '{EXPORTED_LOG_FILE}' exists in the script's directory and '{CURRENT_CHAT_HISTORY_FILE}' does NOT.")
        print(f"To start a fresh chat anytime, delete '{CURRENT_CHAT_HISTORY_FILE}'.")
        sys.exit(1)

    user_message = sys.argv[1] # Get message from command-line argument

    chat_history = []
    # Logic to decide initial history source:
    if os.path.exists(CURRENT_CHAT_HISTORY_FILE):
        # Continue existing chat if 'current_chat_history_for_imported_chat.json' file exists
        chat_history = load_chat_history(CURRENT_CHAT_HISTORY_FILE)
    elif os.path.exists(EXPORTED_LOG_FILE):
        # If no current chat, and an exported log exists, use that as the starting point
        print(f"'{CURRENT_CHAT_HISTORY_FILE}' not found. Attempting to initialize from '{EXPORTED_LOG_FILE}'...", file=sys.stderr)
        chat_history = parse_external_log(EXPORTED_LOG_FILE)
        if not chat_history: # If parsing failed or log was empty, start fresh
            print("Failed to load external log or it was empty. Starting a fresh chat.", file=sys.stder)
            chat_history = []
    else:
        # If neither exists, start a brand new chat
        print("No existing chat history or external log found. Starting a fresh chat.", file=sys.stderr)
        chat_history = []
    
    # Add the current user message to the history
    chat_history.append({"role": "user", "parts": [{"text": user_message}]})

    # --- Send the message and get a streamed response ---
    try:
        # Send the entire chat_history as contents for context
        response_stream = model.generate_content(
            chat_history, # <--- Sending the full history here
            generation_config=generation_config,
            safety_settings=safety_settings,
            stream=True
        )

        collected_ai_response = "" # Accumulate AI's response text

        for chunk in response_stream:
            if chunk.text:
                collected_ai_response += chunk.text
        
        # Print only the AI's response to stdout (standard output, so it can be piped)
        print(collected_ai_response)

        # Add the AI's accumulated response to the chat history
        chat_history.append({"role": "model", "parts": [{"text": collected_ai_response}]})

        # Save the updated chat history for the next run
        save_chat_history(chat_history, CURRENT_CHAT_HISTORY_FILE)

    except Exception as e:
        print(f"\nAn error occurred during AI interaction: {e}", file=sys.stderr) # Print errors to stderr
        import google.api_core.exceptions
        if isinstance(e, google.api_core.exceptions.GoogleAPICallError):
            print(f"Google API Call Error details: {e.details}", file=sys.stderr)
            if hasattr(e, 'message'):
                print(f"Message from error: {e.message}", file=sys.stderr)
        sys.exit(1) # Exit with an error code