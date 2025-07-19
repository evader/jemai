def _run_ollama(prompt, job_id, sid):
      """
      Sends a query to the STANDALONE RAG backend service running on the HOST.
      """
      try:
        # The endpoint for your dedicated RAG API microservice running on the host
        # 'host.docker.internal' is a special DNS name that resolves to the host's IP from within a container
        RAG_API_URL = "http://host.docker.internal:11435/query" 
    
        _background_emit('output', {'output': f'--- Querying local RAG Synapz (on host): "{prompt}" ---\n', 'job_id': job_id}, sid)
    
        payload = {
            "query": prompt
        }
    
        response_rag = requests.post(RAG_API_URL, json=payload)
        response_rag.raise_for_status()
    
        ai_response_data = response_rag.json()
        ai_response = ai_response_data.get("response", "No response found from RAG service.")
    
        # Update job with the final AI response
        _background_emit('output', {'output': ai_response, 'job_id': job_id}, sid)
    
        jobs[job_id]["status"] = "complete"
        jobs[job_id]["output"] += f"\n--- RAG query complete ---\n{ai_response}"
        _background_emit('output', {'output': '\n--- Job Complete ---', 'job_id': job_id, 'final_status': 'complete'}, sid)
    
      except requests.exceptions.RequestException as e:
        error_message = f'Error connecting to RAG service on host: {e}'
        jobs[job_id]["status"] = "error"
        _background_emit('output', {'output': error_message, 'job_id': job_id, 'final_status': 'error'}, sid)
      except Exception as e:
        error_message = f'An unexpected error occurred during RAG interaction: {e}'
        jobs[job_id]["status"] = "error"
        _background_emit('output', {'output': error_message, 'job_id': job_id, 'final_status': 'error'}, sid)