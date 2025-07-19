if __name__ == '__main__':
    print("--- Initializing JEM AI Unified Core ---")
    initialize_rag()
    print("--- Starting Web Server on port 5000 in DEBUG MODE with LIVE RELOAD ---")
    # debug=True enables stack traces in the browser on error.
    # use_reloader=True tells the server to automatically restart when it detects a code change.
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)