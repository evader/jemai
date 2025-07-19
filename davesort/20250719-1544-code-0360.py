def _run_ollama(prompt, job_id, sid):
  """
  Sends a query to the synapz_core.py RAG backend.
  """
  try:
    # This is the endpoint for your local, RAG-enabled AI
    SYNAPZ_API_URL = "http://localhost:11434/query"

    _background_emit('output', {'output': f'--- Querying local Synapz-Core: "{prompt}" ---\n', 'job_id': job_id}, sid)

    # The payload for synapz_core.py's /query endpoint
    payload = {
        "query": prompt
    }

    # Make the API call
    response_synapz = requests.post(SYNAPZ_API_URL, json=payload)
    response_synapz.raise_for_status()

    # The response from synapz_core.py should be the AI's direct answer
    ai_response = response_synapz.text # Or .json() if it returns structured data

    # Update job with the final AI response
    _background_emit('output', {'output': ai_response, 'job_id': job_id}, sid)

    # Mark the job as complete
    jobs[job_id]["status"] = "complete"
    jobs[job_id]["output"] += f"\n--- Synapz-Core query complete ---\n{ai_response}"
    _background_emit('output', {'output': '\n--- Job Complete ---', 'job_id': job_id, 'final_status': 'complete'}, sid)

  except requests.exceptions.RequestException as e:
    error_message = f'Error connecting to Synapz-Core service: {e}'
    jobs[job_id]["status"] = "error"
    _background_emit('output', {'output': error_message, 'job_id': job_id, 'final_status': 'error'}, sid)
  except Exception as e:
    error_message = f'An unexpected error occurred during Synapz-Core interaction: {e}'
    jobs[job_id]["status"] = "error"
    _background_emit('output', {'output': error_message, 'job_id': job_id, 'final_status': 'error'}, sid)