#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Streamlit Test Interface for Agentic Repair Assistant API
Interactive chat interface to test the Flask API
"""

import streamlit as st
import requests
import json
from PIL import Image
import io
import base64
import time
from datetime import datetime

# Configuration
API_BASE_URL = "https://prawn-correct-muskrat.ngrok-free.app/api"

# Page config
st.set_page_config(
    page_title="🔧 Repair Assistant Test Chat",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    """Initialize session state variables"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'api_status' not in st.session_state:
        st.session_state.api_status = "unknown"
    if 'current_mode' not in st.session_state:
        st.session_state.current_mode = "listening"
    if 'device_info' not in st.session_state:
        st.session_state.device_info = {}

def check_api_health():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            st.session_state.api_status = "healthy"
            return True
    except:
        st.session_state.api_status = "offline"
        return False
    return False

def create_session():
    """Create a new repair session"""
    try:
        response = requests.post(f"{API_BASE_URL}/session", timeout=10)
        if response.status_code == 200:
            data = response.json()
            st.session_state.session_id = data['session_id']
            st.session_state.messages = []
            st.session_state.current_mode = "listening"
            st.session_state.device_info = {}
            add_message("system", data.get('message', 'New session created'))
            return True
    except Exception as e:
        st.error(f"Failed to create session: {str(e)}")
    return False

def get_session_status():
    """Get current session status"""
    if not st.session_state.session_id:
        return None
    
    try:
        response = requests.get(f"{API_BASE_URL}/session/{st.session_state.session_id}/status", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def upload_image(uploaded_file):
    """Upload image to API"""
    if not st.session_state.session_id:
        st.error("Please create a session first")
        return False
    
    try:
        # Read bytes from Streamlit's UploadedFile
        file_bytes = uploaded_file.getvalue()
        files = {
            'image': (uploaded_file.name, file_bytes, uploaded_file.type)
        }
        data = {'session_id': st.session_state.session_id}
        
        response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            add_message("system", f"Image uploaded: {result['filename']}")
            return result['filename']
        else:
            st.error(f"Upload failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        st.error(f"Upload error: {str(e)}")
    
    return False


def analyze_repair(message, image_filename=None):
    """Send repair analysis request"""
    if not st.session_state.session_id:
        st.error("Please create a session first")
        return
    
    try:
        payload = {'message': message}
        if image_filename:
            payload['image_filename'] = image_filename
        
        with st.spinner("🤖 Multi-agent analysis in progress..."):
            response = requests.post(
                f"{API_BASE_URL}/session/{st.session_state.session_id}/analyze",
                json=payload,
                timeout=180
            )
        
        if response.status_code == 200:
            result = response.json()
            add_message("assistant", result['response'])
            
            # Update session info
            st.session_state.current_mode = result.get('mode', 'unknown')
            st.session_state.device_info = {
                'device': result.get('device'),
                'problem': result.get('problem'),
                'confidence': result.get('confidence_level', 0),
                'step': result.get('current_step', 0),
                'safety_concerns': result.get('safety_concerns', []),
                'ready_for_guidance': result.get('ready_for_guidance', False)
            }
            
            return result
        else:
            error_msg = response.json().get('error', 'Analysis failed')
            add_message("system", f"❌ Error: {error_msg}")
    
    except Exception as e:
        add_message("system", f"❌ Request failed: {str(e)}")

def get_guidance(message):
    """Get step-by-step guidance"""
    if not st.session_state.session_id:
        st.error("Please create a session first")
        return
    
    try:
        payload = {'message': message}
        
        with st.spinner("💬 Getting guidance..."):
            response = requests.post(
                f"{API_BASE_URL}/session/{st.session_state.session_id}/guide",
                json=payload,
                timeout=180
            )
        
        if response.status_code == 200:
            result = response.json()
            add_message("assistant", result['response'])
            
            # Update step info
            if 'current_step' in result:
                st.session_state.device_info['step'] = result['current_step']
            
            return result
        else:
            error_msg = response.json().get('error', 'Guidance failed')
            add_message("system", f"❌ Error: {error_msg}")
    
    except Exception as e:
        add_message("system", f"❌ Request failed: {str(e)}")

def add_message(role, content):
    """Add message to chat history"""
    st.session_state.messages.append({
        'role': role,
        'content': content,
        'timestamp': datetime.now().strftime("%H:%M:%S")
    })

def reset_session():
    """Reset current session"""
    if not st.session_state.session_id:
        return
    
    try:
        response = requests.post(f"{API_BASE_URL}/session/{st.session_state.session_id}/reset", timeout=10)
        if response.status_code == 200:
            st.session_state.messages = []
            st.session_state.current_mode = "listening"
            st.session_state.device_info = {}
            add_message("system", "Session reset successfully!")
    except Exception as e:
        st.error(f"Reset failed: {str(e)}")

# Initialize session state
init_session_state()

# Main app
st.title("🔧 Repair Assistant Test Chat")

# Sidebar
with st.sidebar:
    st.header("🎛️ Control Panel")
    
    # API Status
    is_healthy = check_api_health()
    status_color = "🟢" if is_healthy else "🔴"
    st.metric("API Status", f"{status_color} {st.session_state.api_status.title()}")
    
    if not is_healthy:
        st.error("⚠️ API is not running! Please start your Flask API first.")
        st.code("python your_flask_api.py", language="bash")
    
    st.divider()
    
    # Session Management
    st.subheader("📋 Session")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 New Session", disabled=not is_healthy):
            create_session()
            st.rerun()
    
    with col2:
        if st.button("🔄 Reset", disabled=not st.session_state.session_id):
            reset_session()
            st.rerun()
    
    if st.session_state.session_id:
        st.success(f"Session: {st.session_state.session_id[:8]}...")
        
        # Session Status
        status = get_session_status()
        if status:
            st.info(f"Mode: {status.get('mode', 'unknown').title()}")
            if status.get('device'):
                st.info(f"Device: {status['device']}")
            if status.get('problem'):
                st.info(f"Problem: {status['problem']}")
    else:
        st.warning("No active session")
    
    st.divider()
    
    # Image Upload
    st.subheader("📷 Image Upload")
    uploaded_file = st.file_uploader(
        "Upload repair image", 
        type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
        disabled=not st.session_state.session_id
    )
    
    if uploaded_file and st.session_state.session_id:
        # Show image preview
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        if st.button("📤 Upload Image"):
            filename = upload_image(uploaded_file)
            if filename:
                st.success("Image uploaded successfully!")
                st.session_state.uploaded_filename = filename
    
    st.divider()
    
    # Device Info
    if st.session_state.device_info:
        st.subheader("📊 Repair Info")
        info = st.session_state.device_info
        
        if info.get('device'):
            st.metric("Device", info['device'])
        if info.get('problem'):
            st.metric("Problem", info['problem'])
        if 'confidence' in info:
            st.metric("Confidence", f"{info['confidence']:.1%}")
        if 'step' in info:
            st.metric("Current Step", info['step'])
        if info.get('safety_concerns'):
            st.warning("⚠️ Safety: " + ", ".join(info['safety_concerns']))

# Main chat interface
if not is_healthy:
    st.error("🚫 API is offline. Please start your Flask API server first.")
    st.stop()

if not st.session_state.session_id:
    st.info("👋 Welcome! Please create a new session to start chatting with the repair assistant.")
    if st.button("🚀 Start New Session", type="primary"):
        create_session()
        st.rerun()
    st.stop()

# Chat messages
st.subheader("💬 Chat")

# Display chat history
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        role = message['role']
        content = message['content']
        timestamp = message['timestamp']
        
        if role == "user":
            with st.chat_message("user"):
                st.write(content)
                st.caption(f"⏰ {timestamp}")
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.write(content)
                st.caption(f"⏰ {timestamp}")
        else:  # system
            st.info(f"🔧 {content} ⏰ {timestamp}")

# Chat input
st.divider()

# Mode-specific input
if st.session_state.current_mode == "conversational":
    st.success("🎯 **Guidance Mode Active** - Ask questions about repair steps!")
    
    # Quick action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔧 What tools do I need?"):
            add_message("user", "What tools do I need?")
            get_guidance("What tools do I need?")
            st.rerun()
    
    with col2:
        if st.button("👆 What's the next step?"):
            add_message("user", "What's the next step?")
            get_guidance("What's the next step?")
            st.rerun()
    
    with col3:
        if st.button("⚠️ Any safety concerns?"):
            add_message("user", "Any safety concerns?")
            get_guidance("Any safety concerns?")
            st.rerun()

# Text input
user_input = st.chat_input("Type your message here...")

if user_input:
    add_message("user", user_input)
    
    if st.session_state.current_mode == "conversational":
        get_guidance(user_input)
    else:
        # Check if we have an uploaded image
        image_filename = getattr(st.session_state, 'uploaded_filename', None)
        analyze_repair(user_input, image_filename)
    
    st.rerun()

# Quick start examples
if len(st.session_state.messages) == 1:  # Only system message
    st.divider()
    st.subheader("🚀 Quick Start Examples")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Text-based requests:**")
        examples = [
            "My laptop screen is cracked",
            "iPhone battery drains quickly", 
            "Framework laptop won't charge",
            "Samsung phone overheating"
        ]
        
        for example in examples:
            if st.button(f"💬 {example}"):
                add_message("user", example)
                analyze_repair(example)
                st.rerun()
    
    with col2:
        st.write("**With image:**")
        st.info("1. Upload an image using the sidebar\n2. Then type: 'Help me fix this device'")
        
        if st.button("📷 Help me fix this device"):
            if hasattr(st.session_state, 'uploaded_filename'):
                add_message("user", "Help me fix this device")
                analyze_repair("Help me fix this device", st.session_state.uploaded_filename)
                st.rerun()
            else:
                st.warning("Please upload an image first!")

# Footer
st.divider()
st.caption("🔧 Agentic Repair Assistant Test Interface | Built with Streamlit")