#!/usr/bin/env python3
"""
Test script to verify the complete user query flow
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

from local_user_storage import local_user_storage

def test_complete_flow():
    """Test the complete user query flow"""
    print("🧪 Testing Complete User Query Flow...")
    
    # Test data
    user_id = "user_12345"
    session_id = "session_67890"
    query = "How to fix a broken watch band?"
    problem_statement = "broken watch band repair"
    
    print(f"\n1. Saving user query...")
    print(f"   User ID: {user_id}")
    print(f"   Session ID: {session_id}")
    print(f"   Query: {query}")
    
    # Save the query
    success = local_user_storage.save_user_query(user_id, session_id, query, problem_statement)
    print(f"   Save successful: {success}")
    
    print(f"\n2. Retrieving user query...")
    # Get the query back
    retrieved_data = local_user_storage.get_user_query(user_id)
    if retrieved_data:
        print(f"   Retrieved query: '{retrieved_data.get('query')}'")
        print(f"   Retrieved problem: '{retrieved_data.get('problem_statement')}'")
        print(f"   Retrieved session: '{retrieved_data.get('session_id')}'")
    else:
        print("   ❌ No query found!")
        return False
    
    print(f"\n3. Testing session-specific retrieval...")
    # Get specific session query
    session_data = local_user_storage.get_user_query(user_id, session_id)
    if session_data:
        print(f"   Session query: '{session_data.get('query')}'")
    else:
        print("   ❌ No session query found!")
        return False
    
    print(f"\n4. Testing user stats...")
    stats = local_user_storage.get_user_stats(user_id)
    print(f"   Total sessions: {stats.get('total_sessions')}")
    print(f"   Has recent query: {stats.get('has_recent_query')}")
    print(f"   Most recent query: '{stats.get('most_recent_query')}'")
    
    print(f"\n5. Testing session listing...")
    sessions = local_user_storage.list_user_sessions(user_id)
    print(f"   Sessions found: {sessions}")
    
    print(f"\n6. Testing different user isolation...")
    # Test with different user
    other_user_id = "user_99999"
    other_session_id = "session_11111"
    other_query = "How to fix a laptop screen?"
    
    local_user_storage.save_user_query(other_user_id, other_session_id, other_query, "laptop screen repair")
    
    # Verify user isolation
    user1_data = local_user_storage.get_user_query(user_id)
    user2_data = local_user_storage.get_user_query(other_user_id)
    
    print(f"   User 1 query: '{user1_data.get('query') if user1_data else 'None'}'")
    print(f"   User 2 query: '{user2_data.get('query') if user2_data else 'None'}'")
    
    if user1_data and user2_data and user1_data.get('query') != user2_data.get('query'):
        print("   ✅ User isolation working correctly!")
    else:
        print("   ❌ User isolation failed!")
        return False
    
    print(f"\n✅ All tests passed! The user query system is working correctly.")
    print(f"\n📁 Folder structure created:")
    print(f"   Backend/user_queries/{user_id}/{session_id}/query.json")
    print(f"   Backend/user_queries/{other_user_id}/{other_session_id}/query.json")
    
    return True

if __name__ == "__main__":
    test_complete_flow()
