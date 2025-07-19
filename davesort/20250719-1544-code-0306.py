if shell_command:
            emit('output', {'output': f'--- Generated command: {shell_command} ---\n', 'job_id': job_id})
            # Original: _run_command(shell_command, job_id) # This needs proper context
            socketio.start_background_task(_run_command, shell_command, job_id) # CHANGE TO THIS