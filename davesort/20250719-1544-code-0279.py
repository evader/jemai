@app.route('/')
        def index():
            # Serve the index.html from the current directory (which is /app inside container) as a static file
            # This bypasses Jinja2 templating, which might be the source of truncation.
            return send_from_directory('/app', 'templates/index.html')