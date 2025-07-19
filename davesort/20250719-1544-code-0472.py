if __name__ == '__main__':
            # ...
            # Add 'debug=True' to enable auto-reloading on code changes
            socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)