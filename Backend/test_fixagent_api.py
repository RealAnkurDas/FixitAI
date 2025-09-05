#!/usr/bin/env python3
"""
Test script for FixAgent API
Tests the main endpoints to ensure they work correctly
"""

import requests
import json
import time
import base64
from pathlib import Path

# API Configuration
BASE_URL = "http://localhost:8000/api"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_create_session():
    """Test session creation"""
    print("🔍 Testing session creation...")
    try:
        response = requests.post(f"{BASE_URL}/session")
        if response.status_code == 200:
            data = response.json()
            session_id = data['session_id']
            print(f"✅ Session created: {session_id}")
            return session_id
        else:
            print(f"❌ Session creation failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Session creation error: {e}")
        return None

def test_analyze_repair(session_id, message):
    """Test repair analysis"""
    print(f"🔍 Testing repair analysis: '{message}'")
    try:
        response = requests.post(
            f"{BASE_URL}/session/{session_id}/analyze",
            json={"message": message}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analysis successful")
            print(f"   Response: {data['response'][:100]}...")
            print(f"   Processing time: {data.get('processing_time', 'N/A')}s")
            return True
        else:
            print(f"❌ Analysis failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return False

def test_conversation_memory(session_id):
    """Test conversation memory by asking follow-up questions"""
    print("🔍 Testing conversation memory...")
    
    # Test memory with follow-up questions
    memory_tests = [
        "What did we discuss earlier about my phone?",
        "Can you remember what problem I mentioned?",
        "As we talked about before, what should I do next?",
        "What was the issue with my device that we discussed?"
    ]
    
    success_count = 0
    for i, question in enumerate(memory_tests, 1):
        print(f"   Memory test {i}: '{question}'")
        try:
            response = requests.post(
                f"{BASE_URL}/session/{session_id}/analyze",
                json={"message": question}
            )
            if response.status_code == 200:
                data = response.json()
                response_text = data['response']
                print(f"   ✅ Response: {response_text[:80]}...")
                
                # Check if response shows memory (contains references to previous conversation)
                memory_indicators = [
                    "earlier", "before", "discussed", "mentioned", "phone", "cracked", "screen"
                ]
                has_memory = any(indicator.lower() in response_text.lower() for indicator in memory_indicators)
                
                if has_memory:
                    print(f"   🧠 Memory detected in response!")
                    success_count += 1
                else:
                    print(f"   ⚠️  No clear memory references found")
            else:
                print(f"   ❌ Request failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"✅ Memory tests completed: {success_count}/{len(memory_tests)} showed memory")
    return success_count > 0

def test_conversation_history(session_id):
    """Test conversation history retrieval"""
    print("🔍 Testing conversation history...")
    try:
        response = requests.get(f"{BASE_URL}/session/{session_id}/history")
        if response.status_code == 200:
            data = response.json()
            history = data['conversation_history']
            print(f"✅ History retrieved: {len(history)} messages")
            return True
        else:
            print(f"❌ History retrieval failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ History retrieval error: {e}")
        return False

def test_with_image(session_id):
    """Test analysis with image"""
    print("🔍 Testing analysis with image...")
    
    # Look for a test image
    test_image_path = Path(__file__).parent / "testimgs" / "iphone_cracked.jpg"
    
    if not test_image_path.exists():
        print("⚠️  No test image found, skipping image test")
        return True
    
    try:
        # Upload image
        with open(test_image_path, 'rb') as f:
            files = {'image': f}
            data = {'session_id': session_id}
            response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
        
        if response.status_code == 200:
            upload_data = response.json()
            filename = upload_data['filename']
            print(f"✅ Image uploaded: {filename}")
            
            # Analyze with image
            analyze_response = requests.post(
                f"{BASE_URL}/session/{session_id}/analyze",
                json={
                    "message": "Help me fix this cracked phone screen",
                    "image_filename": filename
                }
            )
            
            if analyze_response.status_code == 200:
                data = analyze_response.json()
                print(f"✅ Image analysis successful")
                print(f"   Response: {data['response'][:100]}...")
                return True
            else:
                print(f"❌ Image analysis failed: {analyze_response.status_code}")
                return False
        else:
            print(f"❌ Image upload failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Image test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 FixAgent API Test Suite")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health_check():
        print("❌ Health check failed, stopping tests")
        return
    
    # Test 2: Create session
    session_id = test_create_session()
    if not session_id:
        print("❌ Session creation failed, stopping tests")
        return
    
    # Test 3: Simple repair analysis
    test_analyze_repair(session_id, "Help me fix my cracked phone screen")
    
    # Test 4: Conversational query
    test_analyze_repair(session_id, "What do you think is wrong with my phone?")
    
    # Test 5: Test multiple messages in same session (this was the bug)
    test_analyze_repair(session_id, "Can you give me more details?")
    test_analyze_repair(session_id, "What tools do I need?")
    
    # Test 5: Test conversation memory
    test_conversation_memory(session_id)
    
    # Test 6: Conversation history
    test_conversation_history(session_id)
    
    # Test 7: Analysis with image (if available)
    test_with_image(session_id)
    
    print("=" * 50)
    print("🎉 Test suite completed!")
    print("💡 Check the responses above to verify FixAgent is working correctly")

if __name__ == "__main__":
    main()
