# Original: threading.Thread(target=_run_esphome, args=(yaml_file, job_id)).start()
        socketio.start_background_task(_run_esphome, yaml_file, job_id) # CHANGE TO THIS