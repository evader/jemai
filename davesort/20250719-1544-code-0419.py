# Change _start_clipboard_listener to accept socketio instance and sid
            def _start_clipboard_listener(sio_instance, sid_for_clipboard_output):
                # ...
                sio_instance.emit('output', {'output': line, 'job_id': job_id}, room=sid_for_clipboard_output)
                # ...
            
            # In start_clipboard handler:
            @socketio.on('start_clipboard')
            def start_clipboard(data, sid): # <-- get sid from the client who initiated clipboard_start
                # ...
                global clipboard_listener_thread
                clipboard_global_sid = sid # Store this sid globally or pass to thread
                clipboard_listener_thread = threading.Thread(target=_start_clipboard_listener, args=(socketio, clipboard_global_sid))
                # ...