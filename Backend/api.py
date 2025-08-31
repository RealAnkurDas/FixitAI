#!/usr/bin/env python
# -- coding: utf-8 --
"""
Flask API for True Agentic Multi-Agent Repair Assistant
RESTful API endpoints for repair assistance with multi-agent coordination
"""

import os
import uuid
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import base64
from PIL import Image
import threading
from typing import Dict, Any, Optional
import time

# Import your existing system components
from AIAgent import SimpleRepairAssistant, WorkingMultiAgentSystem

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global session storage (in production, use Redis or database)
user_sessions: Dict[str, Dict[str, Any]] = {}
session_cleanup_lock = threading.Lock()

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def cleanup_old_sessions():
    """Clean up sessions older than 1 hour"""
    current_time = time.time()
    with session_cleanup_lock:
        expired_sessions = [
            session_id for session_id, data in user_sessions.items()
            if current_time - data.get('last_activity', 0) > 3600  # 1 hour
        ]
        for session_id in expired_sessions:
            del user_sessions[session_id]

def get_or_create_session(session_id: str = None) -> tuple:
    """Get existing session or create new one"""
    cleanup_old_sessions()
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            'assistant': SimpleRepairAssistant(),
            'created_at': time.time(),
            'last_activity': time.time(),
            'conversation_history': []
        }
    else:
        user_sessions[session_id]['last_activity'] = time.time()
    
    return session_id, user_sessions[session_id]

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Agentic Repair Assistant API',
        'version': '1.0.0',
        'active_sessions': len(user_sessions)
    })

@app.route('/api/session', methods=['POST'])
def create_session():
    """Create a new repair session"""
    session_id = str(uuid.uuid4())
    _, session_data = get_or_create_session(session_id)
    
    return jsonify({
        'session_id': session_id,
        'status': 'created',
        'mode': 'listening',
        'message': 'New repair session created. Upload an image or describe your repair issue.'
    })

@app.route('/api/session/<session_id>/status', methods=['GET'])
def get_session_status(session_id):
    """Get current session status"""
    if session_id not in user_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_data = user_sessions[session_id]
    assistant = session_data['assistant']
    
    return jsonify({
        'session_id': session_id,
        'status': 'active',
        'assistant_type': 'SimpleRepairAssistant',
        'created_at': session_data['created_at'],
        'last_activity': session_data['last_activity']
    })

@app.route('/api/session/<session_id>/reset', methods=['POST'])
def reset_session(session_id):
    """Reset a session for new repair"""
    if session_id not in user_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    # Create fresh assistant
    user_sessions[session_id]['assistant'] = SimpleRepairAssistant()
    user_sessions[session_id]['last_activity'] = time.time()
    
    return jsonify({
        'session_id': session_id,
        'status': 'reset',
        'message': 'Session reset. Ready for new repair!'
    })

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """Upload image for repair analysis"""
    try:
        # Check if session_id is provided
        session_id = request.form.get('session_id')
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        # Get or create session
        session_id, session_data = get_or_create_session(session_id)
        
        # Check if file is provided
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'File type not allowed',
                'allowed_types': list(app.config['ALLOWED_EXTENSIONS'])
            }), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        timestamp = str(int(time.time()))
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Validate it's actually an image
        try:
            with Image.open(file_path) as img:
                img.verify()
        except Exception as e:
            os.remove(file_path)  # Clean up invalid file
            return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
        
        return jsonify({
            'session_id': session_id,
            'filename': filename,
            'file_path': file_path,
            'message': 'Image uploaded successfully. Now provide a description of the repair issue.',
            'upload_url': f'/api/uploads/{filename}'
        })
        
    except RequestEntityTooLarge:
        return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/session/<session_id>/analyze', methods=['POST'])
def analyze_repair(session_id):
    """Main repair analysis endpoint - triggers multi-agent workflow"""
    try:
        # Get session
        if session_id not in user_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session_data = user_sessions[session_id]
        assistant = session_data['assistant']
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400
        
        user_input = data.get('message', '').strip()
        if not user_input:
            return jsonify({'error': 'Message is required'}), 400
        
        # Handle optional image
        image_data = None
        if 'image_filename' in data:
            image_filename = secure_filename(data['image_filename'])
            potential_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            if os.path.exists(potential_path):
                # Read and encode the image
                with open(potential_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Add user message to conversation history
        session_data['conversation_history'].append({
            'role': 'user',
            'message': user_input,
            'timestamp': time.time(),
            'has_image': image_data is not None
        })
        
        # Process through the multi-agent system
        result = assistant.analyze_repair(user_input, image_data)
        
        # Add assistant response to conversation history
        session_data['conversation_history'].append({
            'role': 'assistant',
            'message': result['guidance'],
            'timestamp': time.time()
        })
        
        # Update session activity
        session_data['last_activity'] = time.time()
        
        return jsonify({
            'session_id': session_id,
            'success': result['success'],
            'response': result['guidance'],
            'overall_confidence': result['overall_confidence'],
            'processing_time': result['processing_time'],
            'agent_results': {
                agent: {
                    'success': agent_result.success,
                    'confidence': agent_result.confidence,
                    'processing_time': agent_result.processing_time
                } for agent, agent_result in result['agent_results'].items()
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Analysis failed: {str(e)}',
            'session_id': session_id
        }), 500

@app.route('/api/session/<session_id>/guide', methods=['POST'])
def conversational_guidance(session_id):
    """Conversational step-by-step guidance endpoint"""
    try:
        # Get session
        if session_id not in user_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session_data = user_sessions[session_id]
        assistant = session_data['assistant']
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400
        
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Add user message to conversation history
        session_data['conversation_history'].append({
            'role': 'user',
            'message': user_message,
            'timestamp': time.time(),
            'has_image': False
        })
        
        # For now, just run another analysis with the follow-up question
        # In a more sophisticated system, you'd want to maintain conversation context
        result = assistant.analyze_repair(user_message, None)
        
        # Add assistant response to conversation history
        session_data['conversation_history'].append({
            'role': 'assistant',
            'message': result['guidance'],
            'timestamp': time.time()
        })
        
        # Update session activity
        session_data['last_activity'] = time.time()
        
        return jsonify({
            'session_id': session_id,
            'response': result['guidance'],
            'success': result['success'],
            'overall_confidence': result['overall_confidence']
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Guidance failed: {str(e)}',
            'session_id': session_id
        }), 500

@app.route('/api/session/<session_id>/history', methods=['GET'])
def get_conversation_history(session_id):
    """Get conversation history for a session"""
    if session_id not in user_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_data = user_sessions[session_id]
    
    return jsonify({
        'session_id': session_id,
        'conversation_history': session_data.get('conversation_history', []),
        'session_info': {
            'created_at': session_data['created_at'],
            'last_activity': session_data['last_activity'],
            'assistant_type': 'SimpleRepairAssistant',
            'total_messages': len(session_data.get('conversation_history', []))
        }
    })

@app.route('/api/sessions', methods=['GET'])
def list_active_sessions():
    """List all active sessions (for debugging)"""
    cleanup_old_sessions()
    
    sessions_info = {}
    for session_id, data in user_sessions.items():
        sessions_info[session_id] = {
            'created_at': data['created_at'],
            'last_activity': data['last_activity'],
            'age_minutes': (time.time() - data['created_at']) / 60
        }
    
    return jsonify({
        'active_sessions': len(user_sessions),
        'sessions': sessions_info
    })

@app.route('/api/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a specific session"""
    if session_id not in user_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    del user_sessions[session_id]
    
    return jsonify({
        'message': f'Session {session_id} deleted successfully'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

if __name__ == '__main__':
    print("🔧 Starting Agentic Repair Assistant API...")
    print("📍 Available endpoints:")
    print("  GET  /api/health              - Health check")
    print("  POST /api/session             - Create new session")
    print("  GET  /api/session/<id>/status - Get session status")
    print("  POST /api/session/<id>/reset  - Reset session")
    print("  POST /api/upload              - Upload image")
    print("  POST /api/session/<id>/analyze - Analyze repair (multi-agent)")
    print("  POST /api/session/<id>/guide  - Get step-by-step guidance")
    print("  GET  /api/session/<id>/history - Get conversation history")
    print("  GET  /api/uploads/<filename>  - Serve uploaded files")
    print("  GET  /api/sessions            - List active sessions")
    print("  DELETE /api/session/<id>      - Delete session")
    print("\n🚀 Server starting on http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=False)