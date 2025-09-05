#!/usr/bin/env python3
"""
FastAPI backend for FixAgent.py integration
Provides RESTful API endpoints for the multi-agent repair system
"""

import os
import uuid
import json
import base64
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import the FixAgent system
from FixAgent import run_multiagent_system

app = FastAPI(
    title="FixAgent API",
    description="Multi-Agent Repair Assistant API powered by FixAgent.py",
    version="1.0.0"
)

# Enable CORS for Flutter frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Flutter app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

# Global session storage (in production, use Redis or database)
user_sessions: Dict[str, Dict[str, Any]] = {}

# Pydantic models for request/response
class ChatMessage(BaseModel):
    message: str
    isUser: bool
    timestamp: Optional[float] = None

class SessionCreate(BaseModel):
    title: Optional[str] = None

class MessageRequest(BaseModel):
    message: str
    image_filename: Optional[str] = None

class MessageResponse(BaseModel):
    session_id: str
    response: str
    success: bool
    processing_time: Optional[float] = None
    response_source: Optional[str] = None  # "conversation" or "problem_identification"
    local_repair_links: Optional[List[str]] = None  # Google Maps URLs for repair shops

class SessionInfo(BaseModel):
    session_id: str
    title: str
    created_at: float
    last_activity: float
    message_count: int

def get_or_create_session(session_id: str = None) -> tuple:
    """Get existing session or create new one"""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            'title': f'Session {len(user_sessions) + 1}',
            'created_at': time.time(),
            'last_activity': time.time(),
            'conversation_history': []
        }
    else:
        user_sessions[session_id]['last_activity'] = time.time()
    
    return session_id, user_sessions[session_id]

def cleanup_old_sessions():
    """Clean up sessions older than 1 hour"""
    current_time = time.time()
    expired_sessions = [
        session_id for session_id, data in user_sessions.items()
        if current_time - data.get('last_activity', 0) > 3600  # 1 hour
    ]
    for session_id in expired_sessions:
        del user_sessions[session_id]

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    cleanup_old_sessions()
    return {
        "status": "healthy",
        "service": "FixAgent API",
        "version": "1.0.0",
        "active_sessions": len(user_sessions)
    }

@app.post("/api/session")
async def create_session(session_data: Optional[SessionCreate] = None):
    """Create a new repair session"""
    cleanup_old_sessions()
    
    session_id = str(uuid.uuid4())
    _, session_info = get_or_create_session(session_id)
    
    if session_data and session_data.title:
        session_info['title'] = session_data.title
    
    return {
        "session_id": session_id,
        "status": "created",
        "title": session_info['title'],
        "message": "New repair session created. Ready to help with your repair needs!"
    }

@app.get("/api/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current session status"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = user_sessions[session_id]
    return {
        "session_id": session_id,
        "status": "active",
        "title": session_data['title'],
        "created_at": session_data['created_at'],
        "last_activity": session_data['last_activity'],
        "message_count": len(session_data.get('conversation_history', []))
    }

@app.post("/api/session/{session_id}/reset")
async def reset_session(session_id: str):
    """Reset a session for new repair"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Clear conversation history but keep session
    user_sessions[session_id]['conversation_history'] = []
    user_sessions[session_id]['last_activity'] = time.time()
    
    return {
        "session_id": session_id,
        "status": "reset",
        "message": "Session reset. Ready for new repair!"
    }

@app.post("/api/upload")
async def upload_image(
    session_id: str = Form(...),
    image: UploadFile = File(...)
):
    """Upload image for repair analysis"""
    # Validate session
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate file
    if not image.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_extension = Path(image.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    content = await image.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 16MB.")
    
    # Save file
    timestamp = str(int(time.time()))
    filename = f"{timestamp}_{image.filename}"
    file_path = UPLOAD_DIR / filename
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    return {
        "session_id": session_id,
        "filename": filename,
        "file_path": str(file_path),
        "message": "Image uploaded successfully. Now provide a description of the repair issue.",
        "upload_url": f"/api/uploads/{filename}"
    }

@app.get("/api/uploads/{filename}")
async def serve_uploaded_file(filename: str):
    """Serve uploaded files"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(file_path)

@app.post("/api/session/{session_id}/analyze", response_model=MessageResponse)
async def analyze_repair(
    session_id: str, 
    request: Request
):
    """Main repair analysis endpoint - triggers FixAgent multi-agent workflow"""
    # Validate session
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = user_sessions[session_id]
    
    # Handle both multipart form (with image) and JSON (text-only) requests
    content_type = request.headers.get("content-type", "")
    
    if "multipart/form-data" in content_type:
        # Handle multipart form data (image + text)
        form_data = await request.form()
        message = form_data.get("message", "")
        image_file = form_data.get("image")
        
        # Handle image data if provided
        image_data = None
        if image_file:
            try:
                content = await image_file.read()
                if content and len(content) > 0:
                    image_data = base64.b64encode(content).decode('utf-8')
                    print(f"DEBUG: Image processed successfully, size: {len(image_data)} characters")
                else:
                    print("DEBUG: Image file is empty")
            except Exception as e:
                print(f"DEBUG: Error processing image: {e}")
                image_data = None
    else:
        # Handle JSON data (text-only)
        try:
            json_data = await request.json()
            message = json_data.get("message", "")
            image_data = None
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid request format")
    
    # Validate message
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Add user message to conversation history
    user_message = {
        'role': 'user',
        'message': message,
        'timestamp': time.time(),
        'has_image': image_data is not None
    }
    session_data['conversation_history'].append(user_message)
    
    # Debug: Print image data status
    print(f"DEBUG: Message: '{message}'")
    print(f"DEBUG: Has image_data: {image_data is not None}")
    if image_data:
        print(f"DEBUG: Image data length: {len(image_data)}")
        print(f"DEBUG: Image data preview: {image_data[:100]}...")
    else:
        print("DEBUG: No image data provided")
    
    try:
        # Start timing
        start_time = time.time()
        
        # Run the FixAgent multi-agent system with conversation history
        conversation_history = session_data.get('conversation_history', [])
        result = run_multiagent_system(message, image_data, conversation_history)
        
        # End timing
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Extract the appropriate response based on the response_source
        response_source = result.get("response_source", "")
        local_repair_links = result.get("local_repair_links", [])
        
        # Debug logging
        print(f"DEBUG API: response_source = '{response_source}'")
        print(f"DEBUG API: local_repair_links count = {len(local_repair_links)}")
        if local_repair_links:
            print(f"DEBUG API: local_repair_links = {local_repair_links}")
        
        if response_source == "conversation":
            response_text = result.get("conversation_response", "I'm here to help with your repair needs!")
            print("DEBUG API: Using conversation response")
        else:
            response_text = result.get("final_response", "I couldn't process your request. Please try again.")
            print("DEBUG API: Using problem identification response")
        
        # Add assistant response to conversation history
        assistant_message = {
            'role': 'assistant',
            'message': response_text,
            'timestamp': time.time()
        }
        session_data['conversation_history'].append(assistant_message)
        
        # Update session activity
        session_data['last_activity'] = time.time()
        
        return MessageResponse(
            session_id=session_id,
            response=response_text,
            success=True,
            processing_time=processing_time,
            response_source=response_source,
            local_repair_links=local_repair_links
        )
        
    except Exception as e:
        # Add error message to conversation history
        error_message = {
            'role': 'assistant',
            'message': f"Sorry, I encountered an error: {str(e)}",
            'timestamp': time.time()
        }
        session_data['conversation_history'].append(error_message)
        session_data['last_activity'] = time.time()
        
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@app.get("/api/session/{session_id}/history")
async def get_conversation_history(session_id: str):
    """Get conversation history for a session"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = user_sessions[session_id]
    
    return {
        "session_id": session_id,
        "conversation_history": session_data.get('conversation_history', []),
        "session_info": {
            "title": session_data['title'],
            "created_at": session_data['created_at'],
            "last_activity": session_data['last_activity'],
            "total_messages": len(session_data.get('conversation_history', []))
        }
    }

@app.get("/api/sessions")
async def list_active_sessions():
    """List all active sessions"""
    cleanup_old_sessions()
    
    sessions_info = {}
    for session_id, data in user_sessions.items():
        sessions_info[session_id] = {
            "title": data['title'],
            "created_at": data['created_at'],
            "last_activity": data['last_activity'],
            "age_minutes": (time.time() - data['created_at']) / 60,
            "message_count": len(data.get('conversation_history', []))
        }
    
    return {
        "active_sessions": len(user_sessions),
        "sessions": sessions_info
    }

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific session"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del user_sessions[session_id]
    
    return {
        "message": f"Session {session_id} deleted successfully"
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found"}
    )

@app.exception_handler(400)
async def bad_request_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Bad request"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    print("🔧 Starting FixAgent API...")
    print("📍 Available endpoints:")
    print("  GET  /api/health              - Health check")
    print("  POST /api/session             - Create new session")
    print("  GET  /api/session/<id>/status - Get session status")
    print("  POST /api/session/<id>/reset  - Reset session")
    print("  POST /api/upload              - Upload image")
    print("  POST /api/session/<id>/analyze - Analyze repair (FixAgent)")
    print("  GET  /api/session/<id>/history - Get conversation history")
    print("  GET  /api/uploads/<filename>  - Serve uploaded files")
    print("  GET  /api/sessions            - List active sessions")
    print("  DELETE /api/session/<id>      - Delete session")
    print("\n🚀 Server starting on http://localhost:8000")
    
    uvicorn.run(
        "fixagent_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
