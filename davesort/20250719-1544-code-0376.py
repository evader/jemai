def _run_ollama(prompt, job_id, sid):
      """
      Sends a query to the dedicated RAG backend service.
      """
      try:
        # The endpoint for your dedicated RAG API microservice
        RAG_API_URL = "http://jemai_rag_lt_backend:11435/query" # Use internal service name
    
        _background_emit('output', {'output': f'--- Querying local RAG Synapz: "{prompt}" ---\n', 'job_id': job_id}, sid)
    
        payload = {
            "query": prompt
        }
    
        response_rag = requests.post(RAG_API_URL, json=payload)
        response_rag.raise_for_status()
    
        ai_response_data = response_rag.json()
        ai_response = ai_response_data.get("response", "No response found from RAG service.")
    
        _background_emit('output', {'output': ai_response, 'job_id': job_id}, sid)
    
        jobs[job_id]["status"] = "complete"
        jobs[job_id]["output"] += f"\n--- RAG query complete ---\n{ai_response}"
        _background_emit('output', {'output': '\n--- Job Complete ---', 'job_id': job_id, 'final_status': 'complete'}, sid)
    
      except requests.exceptions.RequestException as e:
        error_message = f'Error connecting to RAG service: {e}'
        jobs[job_id]["status"] = "error"
        _background_emit('output', {'output': error_message, 'job_id': job_id, 'final_status': 'error'}, sid)
      except Exception as e:
        error_message = f'An unexpected error occurred during RAG interaction: {e}'
        jobs[job_id]["status"] = "error"
        _background_emit('output', {'output': error_message, 'job_id': job_id, 'final_status': 'error'}, sid)