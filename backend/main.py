from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import init_db
from activity.controller import router as activity_router
from analytics.controller import router as analytics_router
from config.controller import router as config_router
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Create FastAPI app
app = FastAPI(title="Surface Defect Detection API", version="1.0.0")

# Initialize database tables
init_db()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # change to my frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(activity_router)
app.include_router(analytics_router)
app.include_router(config_router)

# Root endpoint
@app.get("/")
def root():
    return {"message": "Surface Defect Detection API is running"}