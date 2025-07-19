# clean_chat_export.py
    import json
    import os
    
    # --- Configuration ---
    # File for the history you're importing (e.g., this conversation's export JSON)
    INPUT_CHAT_FILE = "/home/jemai/exported_chat.json" # Your source chat export
    OUTPUT_CLEAN_CHAT_FILE = "/home/jemai/cleaned_exported_chat.json" # Output cleaned chat
    
    def clean_chat_export(input_file_path, output_file_path):
        """
        Parses a chat export JSON, strips out image/multimodal parts,
        and 'thought' blocks, saving the cleaned version.
        """
        try:
            with open(input_file_path, 'r', encoding='utf-8') as f:
                export_data = json.load(f)
    
            cleaned_messages = []
            messages = export_data.get('messages', [])
    
            for message in messages:
                content_obj = message.get('content', {})
                role = content_obj.get('role')
                parts = content_obj.get('parts', [])
    
                cleaned_parts = []
                for part in parts:
                    # Keep only 'text' parts, and exclude parts marked as 'thought'
                    if 'text' in part and not part.get('thought', False):
                        cleaned_parts.append({"text": part['text']})
                
                # Only include message if there's actual text content after cleaning
                if cleaned_parts:
                    cleaned_messages.append({
                        "author": message.get("author"),
                        "content": {
                            "role": role,
                            "parts": cleaned_parts
                        }
                    })
    
            # Update the original export_data structure with cleaned messages
            export_data['messages'] = cleaned_messages
    
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully cleaned '{input_file_path}'. Cleaned data saved to '{output_file_path}'.")
            print(f"Original messages: {len(messages)}, Cleaned messages: {len(cleaned_messages)}")
            return True
    
        except FileNotFoundError:
            print(f"Error: Input chat file '{input_file_path}' not found.", file=sys.stderr)
            return False
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from '{input_file_path}': {e}. Check file format.", file=sys.stderr)
            return False
        except Exception as e:
            print(f"An unexpected error occurred during cleaning: {e}", file=sys.stderr)
            return False
    
    if __name__ == "__main__":
        print("Starting chat export cleaning process...")
        clean_chat_export(INPUT_CHAT_FILE, OUTPUT_CLEAN_CHAT_FILE)
        print("Cleaning process finished.")