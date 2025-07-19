def _run_ollama(prompt, job_id, sid):
      """
      Interacts with Ollama's API service to generate a shell command from a natural language prompt.
      """
      try:
        # Use a consistent endpoint for the Ollama service within Docker Compose
        # 'jemai_ollama' is the service name, and Docker Compose handles internal DNS resolution
        OLLAMA_API_URL = "http://jemai_ollama:11434/api/generate" # Or /api/chat based on use case

        # Define the request payload for Ollama's API
        # Using a simple chat format as an example
        payload = {
            "model": "llama3:8b", # Or customize this
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                # Add other generation options as needed
            },
            "system": 'You are an expert in Linux shell commands. Your purpose is to translate the user\'s request into a single, executable shell command. Respond with ONLY a JSON object in the format {"command": "shell_command_here"}. Do not provide any other text, explanations, or markdown formatting.'
        }
        
        # Make the API call to Ollama
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        # Parse Ollama's JSON output
        ollama_response_data = response.json()
        
        # Extract content based on Ollama's API response structure
        # Standard generate API returns 'response' field
        # chat API returns 'message' field
        
        # We need to refine this based on the exact API call (generate/chat)
        # Assuming generate API behavior for now based on prompt format.
        
        # Assuming the Ollama AI response is text, and we need to parse it for the shell command
        ollama_text_response = ollama_response_data.get("response") # For /api/generate
        # If using /api/chat, it would be ollama_response_data.get("message", {}).get("content")

        command_data = json.loads(ollama_text_response) # Still expect JSON from LLM
        shell_command = command_data.get("command")
        
        if shell_command:
          _background_emit('output', {'output': f'--- Generated command: {shell_command} ---\n', 'job_id': job_id}, sid)
          _run_command(shell_command, job_id, sid) # Execute the generated command, passing sid
        else:
          _background_emit('output', {'output': 'Error: Could not parse command from AI response.', 'job_id': job_id}, sid)
          _background_emit('output', {'output': f'Full AI response: {ollama_text_response}', 'job_id': job_id}, sid) # Debugging help
          
      except requests.exceptions.RequestException as e:
        # Handle HTTP request errors (e.g., Ollama not running, connection issues)
        _background_emit('output', {'output': f'Error connecting to Ollama service: {e}', 'job_id': job_id}, sid)
      except json.JSONDecodeError as e:
        # Handle cases where Ollama's response is not valid JSON
        _background_emit('output', {'output': f'Error parsing Ollama JSON response: {e}. Raw: {ollama_text_response}', 'job_id': job_id}, sid)
      except Exception as e:
        # Catch any other unexpected errors
        _background_emit('output', {'output': f'Error during Ollama interaction: {e}', 'job_id': job_id}, sid)