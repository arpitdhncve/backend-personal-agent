from flask import Flask, request
from src.routes import routes


app = Flask(__name__)
# app.config.from_object('config')

def create_app():
    setup_app(app)
    return app

def setup_app(app):
    app.register_blueprint(routes, url_prefix='/api')

