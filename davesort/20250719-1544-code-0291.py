@app.route('/')
    def index():
        # Serve index.html directly from the base of the /app directory
        # This explicitly tells Flask to serve the static file and bypass templating engine entirely.
        return send_from_directory('/app/templates', 'index.html') # Serve from /app/templates directory