from flask import Flask, render_template, request, jsonify, send_from_directory # Add send_from_directory

        # ... other imports ...

        # ... other code ...

        @app.route('/')
        def index():
            # Serve the index.html from the 'templates' directory as a static file
            return send_from_directory('templates', 'index.html')