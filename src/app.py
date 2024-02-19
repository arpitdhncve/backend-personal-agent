from fastapi import FastAPI
from src.routes import router as api_router

def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(api_router, prefix='/api')
    # Any additional configuration or setup can be added here
    return app

