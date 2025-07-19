import sys
    # Remove vertexai imports, as we're talking to Ollama now
    # import vertexai
    # from vertexai.generative_models import GenerativeModel, GenerationConfig, SafetySetting

    import json
    import os
    import requests # New import for making HTTP requests to Ollama

    # --- Configuration (for Ollama) ---
    # PROJECT_ID = "vertex-465223" # Not needed for Ollama
    # LOCATION = "global" # Not needed for Ollama
    OLLAMA_API_URL = "http://localhost:11434/api/chat" # Ollama's API endpoint inside its Docker container
    OLLAMA_MODEL_NAME = "llama3:8b" # The model you want to use on Ollama

    # File for the ongoing chat history of YOUR SCRIPT's sessions
    CURRENT_CHAT_HISTORY_FILE = "current_synapz_og_chat.json"
    # File for the history you're importing (SynapzOG's export JSON)
    EXPORTED_LOG_FILE = "synapz_og_chat.json" # <--- This is the file name for SynapzOG's export

    # --- Initialize Ollama-specific model handling ---
    # No direct model instantiation like GenerativeModel here, as it's a direct API call
    # The initial `vertexai.init` and `GenerativeModel` instantiation will be removed.

    # --- (Copy the load_chat_history, save_chat_history, parse_external_log functions exactly as they are in ask.py) ---
    # These functions are already universal for handling any JSON chat history.

    # --- Main Logic ---
    if __name__ == "__main__":
        if len(sys.argv) < 2:
            print("Usage: python local_og.py \"Your message here\"")
            print(f"To initialize chat history from SynapzOG, ensure '{EXPORTED_LOG_FILE}' exists and delete '{CURRENT_CHAT_HISTORY_FILE}'.")
            print(f"To start a fresh chat anytime, delete '{CURRENT_CHAT_HISTORY_FILE}'.")
            sys.exit(1)

        user_message = sys.argv[1]

        chat_history = []
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

        # Add the current user message to the history
        chat_history.append({"role": "user", "content": user_message}) # Ollama expects 'content' for string, not 'parts' here.

        # --- Send message to Ollama ---
        try:
            # Ollama API expects a list of messages (roles and contents)
            messages_for_ollama = []
            for turn in chat_history:
                # Ollama chat API generally expects 'content' for simple text within role, not 'parts'
                # So we extract the text from the 'parts' list assumed by our history management
                if 'parts' in turn and isinstance(turn['parts'], list) and len(turn['parts']) > 0 and 'text' in turn['parts'][0]:
                    messages_for_ollama.append({"role": turn['role'], "content": turn['parts'][0]['text']})
                else: # Fallback if history format is not 'parts' or missing text
                    messages_for_ollama.append({"role": turn['role'], "content": turn['content'] if 'content' in turn else ""}) # Use 'content' if present directly

            # Construct the request payload for Ollama
            payload = {
                "model": OLLAMA_MODEL_NAME,
                "messages": messages_for_ollama,
                "stream": True # Request streaming
            }

            print(f"Sending message to {OLLAMA_MODEL_NAME}: '{user_message}'\\n")

            # Make the streaming request to Ollama API
            collected_ai_response = ""
            with requests.post(OLLAMA_API_URL, json=payload, stream=True) as response:
                response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
                for chunk in response.iter_content(chunk_size=None): # Process full chunk
                    if chunk:
                        try:
                            # Each chunk could be a partial JSON line
                            decoded_chunk = chunk.decode('utf-8')
                            for line in decoded_chunk.splitlines():
                                if line.strip(): # Ensure line is not empty
                                    data = json.loads(line)
                                    if "content" in data["message"]:
                                        text_content = data["message"]["content"]
                                        print(text_content, end="")
                                        collected_ai_response += text_content
                                    if data.get("done"):
                                        break # End of stream
                        except json.JSONDecodeError:
                            # Handle incomplete JSON or non-JSON parts
                            pass
            print("\\n") # New line after the streamed response finishes

            # Add the AI's accumulated response to the chat history (in 'parts' format for consistency)
            chat_history.append({"role": "assistant", "parts": [{"text": collected_ai_response}]}) # Ollama uses 'assistant' for model

            # Save the updated chat history for the next run
            save_chat_history(chat_history, CURRENT_CHAT_HISTORY_FILE)

        except requests.exceptions.RequestException as e:
            print(f"\\nNetwork or API Error: {e}", file=sys.stderr)
            # You might want to remove the last user message from history if the API call failed
            sys.exit(1)
        except Exception as e:
            print(f"\\nAn unexpected error occurred: {e}", file=sys.stderr)
            sys.exit(1)