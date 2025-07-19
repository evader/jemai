# Original: threading.Thread(target=_run_command, args=(command, job_id)).start()
        socketio.start_background_task(_run_command, command, job_id) # CHANGE TO THIS