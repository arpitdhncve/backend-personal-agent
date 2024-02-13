from flask import Flask, request
from src.routes import routes


app = Flask(__name__)

def create_app():
    setup_app(app)
    return app

def setup_app(app):
    app.register_blueprint(routes, url_prefix='/api')

