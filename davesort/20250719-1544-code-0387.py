@app.route("/")
    def index():
      """Serves the main HTML user interface."""
      return render_template('index.html')