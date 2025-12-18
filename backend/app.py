"""
FastAPI server for NYC 311 Analytics Agent
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import os
from dotenv import load_dotenv
from agent import NYC311AnalyticsAgent
import traceback
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="NYC 311 Analytics API",
    description="Production-grade data analytics agent for NYC 311 service requests",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
agent = None
df = None
dataset_loaded = False

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    visualization: Optional[str] = None
    success: bool = True
    code_executed: Optional[str] = None
    visualization_code: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Load dataset and initialize agent on startup"""
    global agent, df, dataset_loaded
    
    try:
        csv_path = "311_Service_Requests_from_2010_to_Present.csv"
        
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found at: {csv_path}")
            logger.info("Please download the NYC 311 dataset and place it in the backend directory")
            logger.info("Download from: https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9")
            return
        
        logger.info("Loading NYC 311 dataset...")
        logger.info("This may take a few minutes for large files...")
        
        # Load with optimizations
        df = pd.read_csv(
            csv_path,
            low_memory=False,
            parse_dates=['Created Date', 'Closed Date'],
            nrows=None  # Load all rows; change to 100000 for testing
        )
        
        logger.info(f"✓ Dataset loaded successfully!")
        logger.info(f"  - Records: {len(df):,}")
        logger.info(f"  - Columns: {len(df.columns)}")
        logger.info(f"  - Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        
        # Initialize agent
        logger.info("Initializing AI agent...")
        agent = NYC311AnalyticsAgent(df)
        dataset_loaded = True
        logger.info("✓ Agent initialized successfully!")
        logger.info("Server ready to accept requests!")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        traceback.print_exc()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "NYC 311 Analytics API",
        "status": "online",
        "dataset_loaded": dataset_loaded,
        "endpoints": {
            "health": "/health",
            "chat": "/api/chat (POST)",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "dataset_loaded": dataset_loaded,
        "records": len(df) if df is not None else 0,
        "columns": len(df.columns) if df is not None else 0,
        "agent_ready": agent is not None
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for processing user queries
    """
    global agent, df
    
    if not dataset_loaded or agent is None or df is None:
        raise HTTPException(
            status_code=503,
            detail="Dataset not loaded. Please ensure the CSV file is in the backend directory and restart the server."
        )
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        logger.info(f"Processing query: {request.message[:100]}...")
        
        # Process query through agent
        result = agent.process_query(request.message)
        
        logger.info(f"Query processed successfully. Visualization: {bool(result.get('visualization'))}")
        
        return ChatResponse(
            response=result["response"],
            visualization=result.get("visualization") or None,
            success=result.get("success", True),
            code_executed=result.get("code_executed") or None,
            visualization_code=result.get("visualization_code") or None
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting NYC 311 Analytics API Server...")
    logger.info("Make sure you have:")
    logger.info("  1. Downloaded the NYC 311 CSV file")
    logger.info("  2. Placed it in the backend directory")
    logger.info("  3. Set DEEPSEEK_API_KEY in .env file")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )