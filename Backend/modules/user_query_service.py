#!/usr/bin/env python3
"""
UserQueryService - Service for managing user-specific repair queries in Firestore
This service handles storing and retrieving the last repair query for each user
"""

import json
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Firestore imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    print("WARNING: Firebase Admin SDK not available. User query storage will use local files only.")

class UserQueryService:
    """Service for managing user-specific repair queries"""
    
    def __init__(self):
        self.db = None
        if FIRESTORE_AVAILABLE:
            try:
                # Initialize Firestore if not already initialized
                if not firebase_admin._apps:
                    # Try to use default credentials (service account key file)
                    cred = credentials.ApplicationDefault()
                    firebase_admin.initialize_app(cred)
                
                self.db = firestore.client()
                print("DEBUG: UserQueryService initialized with Firestore")
            except Exception as e:
                print(f"WARNING: Failed to initialize Firestore: {e}")
                print("DEBUG: UserQueryService will use local file storage only")
                self.db = None
    
    def save_user_query(self, user_id: str, query: str, problem_statement: str = None) -> bool:
        """
        Save the user's last repair query to Firestore
        
        Args:
            user_id: The user's unique identifier
            query: The original user query
            problem_statement: The extracted problem statement
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query_data = {
                "query": query,
                "problem_statement": problem_statement or query,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "last_updated": time.time()
            }
            
            if self.db:
                # Save to Firestore
                doc_ref = self.db.collection('user_queries').document(user_id)
                doc_ref.set(query_data, merge=True)
                print(f"DEBUG: Saved user query to Firestore for user {user_id}")
            else:
                # Fallback to local file storage
                from local_repair_tool import save_query_to_file
                return save_query_to_file(query, problem_statement, user_id)
            
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to save user query: {e}")
            # Fallback to local file storage
            try:
                from local_repair_tool import save_query_to_file
                return save_query_to_file(query, problem_statement, user_id)
            except Exception as fallback_error:
                print(f"ERROR: Fallback save also failed: {fallback_error}")
                return False
    
    def get_user_query(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the user's last repair query from Firestore
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            Dict with query data or None if not found
        """
        try:
            if self.db:
                # Get from Firestore
                doc_ref = self.db.collection('user_queries').document(user_id)
                doc = doc_ref.get()
                
                if doc.exists:
                    query_data = doc.to_dict()
                    print(f"DEBUG: Retrieved user query from Firestore for user {user_id}")
                    return query_data
                else:
                    print(f"DEBUG: No user query found in Firestore for user {user_id}")
                    return None
            else:
                # Fallback to local file storage
                from local_repair_tool import load_query_from_file
                return load_query_from_file(user_id)
                
        except Exception as e:
            print(f"ERROR: Failed to get user query: {e}")
            # Fallback to local file storage
            try:
                from local_repair_tool import load_query_from_file
                return load_query_from_file(user_id)
            except Exception as fallback_error:
                print(f"ERROR: Fallback get also failed: {fallback_error}")
                return None
    
    def clear_user_query(self, user_id: str) -> bool:
        """
        Clear the user's last repair query from Firestore
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.db:
                # Delete from Firestore
                doc_ref = self.db.collection('user_queries').document(user_id)
                doc_ref.delete()
                print(f"DEBUG: Cleared user query from Firestore for user {user_id}")
            else:
                # Fallback to local file storage
                from local_repair_tool import clear_query_file
                return clear_query_file(user_id)
            
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to clear user query: {e}")
            # Fallback to local file storage
            try:
                from local_repair_tool import clear_query_file
                return clear_query_file(user_id)
            except Exception as fallback_error:
                print(f"ERROR: Fallback clear also failed: {fallback_error}")
                return False
    
    def update_user_query_timestamp(self, user_id: str) -> bool:
        """
        Update the timestamp of the user's last query (useful for session management)
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.db:
                # Update timestamp in Firestore
                doc_ref = self.db.collection('user_queries').document(user_id)
                doc_ref.update({
                    "last_updated": time.time(),
                    "timestamp": datetime.now().isoformat()
                })
                print(f"DEBUG: Updated user query timestamp in Firestore for user {user_id}")
                return True
            else:
                # For local file storage, we don't need to update timestamp separately
                return True
                
        except Exception as e:
            print(f"ERROR: Failed to update user query timestamp: {e}")
            return False


# Global instance
user_query_service = UserQueryService()


def main():
    """
    Test function for UserQueryService
    """
    print("🔧 UserQueryService - Testing...")
    
    # Test data
    test_user_id = "test_user_123"
    test_query = "Help me fix my cracked iPhone screen"
    test_problem = "how to fix cracked phone screen"
    
    print(f"\n1. Testing save user query for user: {test_user_id}")
    save_success = user_query_service.save_user_query(test_user_id, test_query, test_problem)
    print(f"   Save successful: {save_success}")
    
    print(f"\n2. Testing get user query for user: {test_user_id}")
    retrieved_data = user_query_service.get_user_query(test_user_id)
    if retrieved_data:
        print(f"   Retrieved query: '{retrieved_data.get('query')}'")
        print(f"   Retrieved problem: '{retrieved_data.get('problem_statement')}'")
        print(f"   Retrieved timestamp: '{retrieved_data.get('timestamp')}'")
    else:
        print("   No query found")
    
    print(f"\n3. Testing update timestamp for user: {test_user_id}")
    update_success = user_query_service.update_user_query_timestamp(test_user_id)
    print(f"   Update successful: {update_success}")
    
    print(f"\n4. Testing clear user query for user: {test_user_id}")
    clear_success = user_query_service.clear_user_query(test_user_id)
    print(f"   Clear successful: {clear_success}")
    
    print(f"\n5. Testing get after clear for user: {test_user_id}")
    final_data = user_query_service.get_user_query(test_user_id)
    if final_data:
        print(f"   Query still exists: '{final_data.get('query')}'")
    else:
        print("   Query successfully cleared")


if __name__ == "__main__":
    main()
