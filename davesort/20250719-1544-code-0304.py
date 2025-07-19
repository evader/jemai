# Original: threading.Thread(target=_run_ollama, args=(prompt, job_id)).start()
        socketio.start_background_task(_run_ollama, prompt, job_id) # CHANGE TO THIS