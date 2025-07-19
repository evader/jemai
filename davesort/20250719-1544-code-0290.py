# Change this line:
    # app = Flask(__name__)

    # TO THIS (explicitly tell Flask where its templates are):
    app = Flask(__name__,
                static_folder='templates',       # This tells Flask where to look for static files IF served by send_static_file
                template_folder='templates')     # This tells Flask where render_template looks