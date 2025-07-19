@app.route("/")
        def index():
          """Serves the main HTML user interface."""
          # Explicitly set the base directory for serving static files
          base_dir = os.path.dirname(os.path.abspath(__file__))
          return send_from_directory(base_dir, 'index.html') # Serve index.html as a static file