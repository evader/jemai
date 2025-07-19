import os
    import subprocess
    import threading
    import json
    import time
    import pyperclip
    import psutil
    import sys

    # --- CRITICAL: Eventlet monkey patching MUST happen at the very top ---
    try:
        import eventlet
        eventlet.monkey_patch()
    except ImportError:
        print("Eventlet not found, Flask-SocketIO might fall back to a less performant server. Consider installing.", file=sys.stderr)

    # ADDED: send_from_directory for serving static files directly
    from flask import Flask, render_template, request, jsonify, send_from_directory
    from flask_socketio import SocketIO # Removed 'emit' as it's used via socketio.emit
    
    # ... rest of your lt.py code ...