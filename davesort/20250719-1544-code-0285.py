@app.route('/')
    def index():
        # Serve the index.html from the 'templates' directory as a static file
        # This explicitly bypasses Jinja2 templating, ensuring the full file is sent.
        return send_from_directory('/app', 'templates/index.html')