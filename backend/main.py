"""
FastAPI backend for LLM Council
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.council import LLMCouncil
from backend.config import CONVERSATIONS_DIR, API_HOST, API_PORT


# Initialize FastAPI app
app = FastAPI(title="LLM Council API", version="1.0.0")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global council instance
council: Optional[LLMCouncil] = None


class QueryRequest(BaseModel):
    """Request model for queries"""
    query: str


class QueryResponse(BaseModel):
    """Response model for queries"""
    conversation_id: str
    result: dict


@app.on_event("startup")
async def startup_event():
    """Initialize the council on startup"""
    global council
    council = LLMCouncil()
    
    # Ensure conversations directory exists
    Path(CONVERSATIONS_DIR).mkdir(parents=True, exist_ok=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global council
    if council:
        await council.close()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LLM Council API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint - verifies all LLMs are accessible"""
    if not council:
        raise HTTPException(status_code=503, detail="Council not initialized")
    
    health_status = await council.health_check()
    all_healthy = all(health_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": health_status
    }


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a user query through the full council workflow
    
    This is a synchronous endpoint - for real-time updates use WebSocket
    """
    if not council:
        raise HTTPException(status_code=503, detail="Council not initialized")
    
    # Process the query
    result = await council.process_query(request.query)
    
    # Save conversation
    conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    conversation_path = Path(CONVERSATIONS_DIR) / f"{conversation_id}.json"
    
    with open(conversation_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return QueryResponse(
        conversation_id=conversation_id,
        result=result
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time council processing with progress updates
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive query from client
            data = await websocket.receive_json()
            query = data.get("query", "")
            
            if not query:
                await websocket.send_json({
                    "type": "error",
                    "message": "No query provided"
                })
                continue
            
            # Progress callback
            async def progress_callback(stage: str, message: str):
                await websocket.send_json({
                    "type": "progress",
                    "stage": stage,
                    "message": message
                })
            
            # Process query with progress updates
            result = await council.process_query(query, progress_callback)
            
            # Save conversation
            conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            conversation_path = Path(CONVERSATIONS_DIR) / f"{conversation_id}.json"
            
            with open(conversation_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            # Send final result
            await websocket.send_json({
                "type": "result",
                "conversation_id": conversation_id,
                "data": result
            })
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Retrieve a saved conversation by ID"""
    conversation_path = Path(CONVERSATIONS_DIR) / f"{conversation_id}.json"
    
    if not conversation_path.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    with open(conversation_path, 'r', encoding='utf-8') as f:
        conversation = json.load(f)
    
    return conversation


@app.get("/conversations")
async def list_conversations():
    """List all saved conversations"""
    conversations_path = Path(CONVERSATIONS_DIR)
    
    if not conversations_path.exists():
        return {"conversations": []}
    
    conversations = []
    for file in conversations_path.glob("*.json"):
        conversations.append({
            "id": file.stem,
            "timestamp": file.stem
        })
    
    return {"conversations": sorted(conversations, key=lambda x: x["id"], reverse=True)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
