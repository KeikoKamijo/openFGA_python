# main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import Base, engine, fga_client
from app.routes import router

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(title="FastAPI OpenFGA Demo")

# CORS設定（React SPAからのアクセス用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    await fga_client.read_latest_authorization_model()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)