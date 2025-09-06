#!/usr/bin/env python3
"""
LocalUserStorage - Local file-based storage for user-specific repair queries
Creates a folder structure: Backend/user_queries/{user_id}/{session_id}/query.json
"""

import json
import os
import time
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

class LocalUserStorage:
    """Local file-based storage for user queries with folder structure"""
    
    def __init__(self):
        # Base directory for user queries
        self.base_dir = Path(__file__).parent.parent / "user_queries"
        self.base_dir.mkdir(exist_ok=True)
        print(f"DEBUG: LocalUserStorage initialized with base directory: {self.base_dir}")
    
    def _get_user_dir(self, user_id: str) -> Path:
        """Get or create user directory"""
        user_dir = self.base_dir / user_id
        user_dir.mkdir(exist_ok=True)
        return user_dir
    
    def _get_session_dir(self, user_id: str, session_id: str) -> Path:
        """Get or create session directory within user directory"""
        user_dir = self._get_user_dir(user_id)
        session_dir = user_dir / session_id
        session_dir.mkdir(exist_ok=True)
        return session_dir
    
    def save_user_query(self, user_id: str, session_id: str, query: str, problem_statement: str = None) -> bool:
        """
        Save the user's repair query for a specific session
        
        Args:
            user_id: The user's unique identifier
            session_id: The session's unique identifier
            query: The original user query
            problem_statement: The extracted problem statement
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            session_dir = self._get_session_dir(user_id, session_id)
            query_file = session_dir / "query.json"
            
            query_data = {
                "query": query,
                "problem_statement": problem_statement or query,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "session_id": session_id,
                "last_updated": time.time()
            }
            
            with open(query_file, 'w', encoding='utf-8') as f:
                json.dump(query_data, f, indent=2, ensure_ascii=False)
            
            print(f"DEBUG: Saved user query to {query_file}")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to save user query: {e}")
            return False
    
    def get_user_query(self, user_id: str, session_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve the user's repair query
        
        Args:
            user_id: The user's unique identifier
            session_id: Optional session ID. If None, gets the most recent query
            
        Returns:
            Dict with query data or None if not found
        """
        try:
            user_dir = self._get_user_dir(user_id)
            
            if session_id:
                # Get specific session query
                session_dir = user_dir / session_id
                query_file = session_dir / "query.json"
                
                if query_file.exists():
                    with open(query_file, 'r', encoding='utf-8') as f:
                        query_data = json.load(f)
                    print(f"DEBUG: Retrieved user query from {query_file}")
                    return query_data
                else:
                    print(f"DEBUG: No query found for user {user_id}, session {session_id}")
                    return None
            else:
                # Get the most recent query across all sessions
                most_recent_query = None
                most_recent_time = 0
                
                for session_dir in user_dir.iterdir():
                    if session_dir.is_dir():
                        query_file = session_dir / "query.json"
                        if query_file.exists():
                            try:
                                with open(query_file, 'r', encoding='utf-8') as f:
                                    query_data = json.load(f)
                                
                                last_updated = query_data.get('last_updated', 0)
                                if last_updated > most_recent_time:
                                    most_recent_time = last_updated
                                    most_recent_query = query_data
                            except Exception as e:
                                print(f"DEBUG: Error reading query file {query_file}: {e}")
                                continue
                
                if most_recent_query:
                    print(f"DEBUG: Retrieved most recent user query for user {user_id}")
                    return most_recent_query
                else:
                    print(f"DEBUG: No queries found for user {user_id}")
                    return None
                
        except Exception as e:
            print(f"ERROR: Failed to get user query: {e}")
            return None
    
    def clear_user_query(self, user_id: str, session_id: str = None) -> bool:
        """
        Clear the user's repair query
        
        Args:
            user_id: The user's unique identifier
            session_id: Optional session ID. If None, clears all queries for the user
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            user_dir = self._get_user_dir(user_id)
            
            if session_id:
                # Clear specific session query
                session_dir = user_dir / session_id
                query_file = session_dir / "query.json"
                
                if query_file.exists():
                    query_file.unlink()
                    print(f"DEBUG: Cleared user query for user {user_id}, session {session_id}")
                else:
                    print(f"DEBUG: No query file to clear for user {user_id}, session {session_id}")
            else:
                # Clear all queries for the user
                for session_dir in user_dir.iterdir():
                    if session_dir.is_dir():
                        query_file = session_dir / "query.json"
                        if query_file.exists():
                            query_file.unlink()
                            print(f"DEBUG: Cleared query file {query_file}")
                
                print(f"DEBUG: Cleared all queries for user {user_id}")
            
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to clear user query: {e}")
            return False
    
    def list_user_sessions(self, user_id: str) -> list:
        """
        List all sessions for a user that have queries
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            List of session IDs with queries
        """
        try:
            user_dir = self._get_user_dir(user_id)
            sessions = []
            
            for session_dir in user_dir.iterdir():
                if session_dir.is_dir():
                    query_file = session_dir / "query.json"
                    if query_file.exists():
                        sessions.append(session_dir.name)
            
            print(f"DEBUG: Found {len(sessions)} sessions with queries for user {user_id}")
            return sessions
            
        except Exception as e:
            print(f"ERROR: Failed to list user sessions: {e}")
            return []
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about user's queries
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            Dict with user query statistics
        """
        try:
            user_dir = self._get_user_dir(user_id)
            sessions = self.list_user_sessions(user_id)
            
            total_queries = len(sessions)
            most_recent_query = self.get_user_query(user_id)
            
            stats = {
                "user_id": user_id,
                "total_sessions": total_queries,
                "has_recent_query": most_recent_query is not None,
                "most_recent_query": most_recent_query.get("query", "") if most_recent_query else "",
                "most_recent_timestamp": most_recent_query.get("timestamp", "") if most_recent_query else ""
            }
            
            return stats
            
        except Exception as e:
            print(f"ERROR: Failed to get user stats: {e}")
            return {"user_id": user_id, "error": str(e)}


# Global instance
local_user_storage = LocalUserStorage()


def main():
    """
    Test function for LocalUserStorage
    """
    print("🔧 LocalUserStorage - Testing...")
    
    # Test data
    test_user_id = "test_user_123"
    test_session_id = "session_456"
    test_query = "Help me fix my cracked iPhone screen"
    test_problem = "how to fix cracked phone screen"
    
    print(f"\n1. Testing save user query for user: {test_user_id}, session: {test_session_id}")
    save_success = local_user_storage.save_user_query(test_user_id, test_session_id, test_query, test_problem)
    print(f"   Save successful: {save_success}")
    
    print(f"\n2. Testing get user query for specific session")
    retrieved_data = local_user_storage.get_user_query(test_user_id, test_session_id)
    if retrieved_data:
        print(f"   Retrieved query: '{retrieved_data.get('query')}'")
        print(f"   Retrieved problem: '{retrieved_data.get('problem_statement')}'")
        print(f"   Retrieved timestamp: '{retrieved_data.get('timestamp')}'")
    else:
        print("   No query found")
    
    print(f"\n3. Testing get most recent query (no session specified)")
    recent_data = local_user_storage.get_user_query(test_user_id)
    if recent_data:
        print(f"   Most recent query: '{recent_data.get('query')}'")
    else:
        print("   No recent query found")
    
    print(f"\n4. Testing list user sessions")
    sessions = local_user_storage.list_user_sessions(test_user_id)
    print(f"   Sessions found: {sessions}")
    
    print(f"\n5. Testing get user stats")
    stats = local_user_storage.get_user_stats(test_user_id)
    print(f"   User stats: {stats}")
    
    print(f"\n6. Testing clear specific session query")
    clear_success = local_user_storage.clear_user_query(test_user_id, test_session_id)
    print(f"   Clear successful: {clear_success}")
    
    print(f"\n7. Testing get after clear")
    final_data = local_user_storage.get_user_query(test_user_id, test_session_id)
    if final_data:
        print(f"   Query still exists: '{final_data.get('query')}'")
    else:
        print("   Query successfully cleared")


if __name__ == "__main__":
    main()
