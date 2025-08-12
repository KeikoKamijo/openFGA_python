# main.py
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import Base, engine, fga_client
from app.routes import router

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Startup
    await fga_client.read_latest_authorization_model()
    yield

app = FastAPI(title="FastAPI OpenFGA Demo", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)