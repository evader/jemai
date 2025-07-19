def _start_clipboard_listener():
               """
               Start the clipboard listener thread.
               """
               global clipboard_listener_thread
               if clipboard_listener_thread and clipboard_listener_thread.is_alive():
                 return
            
               clipboard_listener_stop_event.clear()
               clipboard_listener_thread = threading.Thread(target=_start_clipboard_listener)
               clipboard_listener_thread.daemon = True
               clipboard_listener_thread.start()
            
               # Add this new check for no display *before* pyperclip.paste() is called
               if "DISPLAY" not in os.environ and not sys.stdout.isatty(): # isatty checks if it's connected to terminal
                   # If no display, and not running in an interactive terminal, cannot use pyperclip
                   try: # try to emit if socketio is available, otherwise just print
                       socketio.emit('output', {'output': "--- No display found. Clipboard listener not started. ---", 'job_id': 'system'})
                   except RuntimeError: # SocketIO not yet started, or not connected
                       print("--- No display found. Clipboard listener not started. (SocketIO not ready) ---")
                   return