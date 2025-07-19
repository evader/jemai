from flask import Flask, render_template, request, jsonify, send_from_directory
            # Ensure 'emit' is imported from flask_socketio, or explicitly use socketio.emit
            # For simplicity and clarity, let's explicitly use socketio.emit everywhere.