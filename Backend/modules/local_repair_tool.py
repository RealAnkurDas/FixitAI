#!/usr/bin/env python3
"""
LocalRepairTool - Standalone tool for finding local repair shops
This tool reads a query from a JSON file and searches for nearby repair shops using Google Maps API
"""

import json
import os
import urllib.parse
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import the Google Maps search function
from test_googlemaps import search_repair_shops_advanced

# Import JSON schema utilities
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from json_schemas import (
    ResponseType,
    create_llm_prompt_with_schema,
    convert_json_to_text,
    parse_llm_json_response
)

# Import the new LocalUserStorage
from local_user_storage import local_user_storage

# Configuration
QUERY_FILE_PATH = Path(__file__).parent.parent / "local_repair_query.json"
DEFAULT_LAT = 0.0  # Default coordinates
DEFAULT_LNG = 0.0
DEFAULT_RADIUS = 5000  # 5km radius
DEFAULT_MAX_RESULTS = 5


def save_query_to_file(query: str, problem_statement: str = None, user_id: str = None) -> bool:
    """
    Save the query and problem statement to a JSON file for LocalRepairTool to use
    Now supports user-specific storage when user_id is provided
    
    Args:
        query: The original user query
        problem_statement: The extracted problem statement
        user_id: Optional user ID for user-specific storage
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        query_data = {
            "query": query,
            "problem_statement": problem_statement or query,
            "timestamp": str(Path().cwd()),  # Simple timestamp placeholder
            "user_id": user_id  # Store user ID for user-specific queries
        }
        
        # Use user-specific file path if user_id is provided
        if user_id:
            query_file_path = Path(__file__).parent.parent / f"user_queries_{user_id}.json"
        else:
            query_file_path = QUERY_FILE_PATH
        
        with open(query_file_path, 'w', encoding='utf-8') as f:
            json.dump(query_data, f, indent=2, ensure_ascii=False)
        
        print(f"DEBUG: Saved query to {query_file_path}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to save query to file: {e}")
        return False


def load_query_from_file(user_id: str = None) -> Optional[Dict[str, str]]:
    """
    Load the query and problem statement from the JSON file
    Now supports user-specific loading when user_id is provided
    
    Args:
        user_id: Optional user ID for user-specific query loading
        
    Returns:
        Dict with 'query' and 'problem_statement' keys, or None if file doesn't exist or error
    """
    try:
        # Use user-specific file path if user_id is provided
        if user_id:
            query_file_path = Path(__file__).parent.parent / f"user_queries_{user_id}.json"
        else:
            query_file_path = QUERY_FILE_PATH
            
        if not query_file_path.exists():
            print(f"DEBUG: Query file {query_file_path} does not exist")
            return None
            
        with open(query_file_path, 'r', encoding='utf-8') as f:
            query_data = json.load(f)
        
        print(f"DEBUG: Loaded query from {query_file_path}")
        return query_data
        
    except Exception as e:
        print(f"ERROR: Failed to load query from file: {e}")
        return None


def clear_query_file(user_id: str = None) -> bool:
    """
    Clear/delete the query JSON file (used when conversation response is generated)
    Now supports user-specific clearing when user_id is provided
    
    Args:
        user_id: Optional user ID for user-specific query clearing
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Use user-specific file path if user_id is provided
        if user_id:
            query_file_path = Path(__file__).parent.parent / f"user_queries_{user_id}.json"
        else:
            query_file_path = QUERY_FILE_PATH
            
        if query_file_path.exists():
            query_file_path.unlink()
            print(f"DEBUG: Cleared query file {query_file_path}")
        else:
            print(f"DEBUG: Query file {query_file_path} does not exist (already clear)")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to clear query file: {e}")
        return False


def generate_repair_shop_query(problem_statement: str) -> str:
    """
    Generate a search query for finding local repair shops based on the problem statement
    
    Args:
        problem_statement: The extracted problem statement
        
    Returns:
        str: Search query for repair shops
    """
    # Simple logic to generate repair shop search query
    problem_lower = problem_statement.lower()
    
    # Extract device type and create search query
    if any(word in problem_lower for word in ["phone", "iphone", "android", "smartphone", "mobile"]):
        if "screen" in problem_lower or "cracked" in problem_lower:
            return "phone screen repair shop"
        elif "battery" in problem_lower:
            return "phone battery repair shop"
        else:
            return "phone repair shop"
    
    elif any(word in problem_lower for word in ["laptop", "computer", "pc", "macbook"]):
        if "screen" in problem_lower or "display" in problem_lower:
            return "laptop screen repair shop"
        elif "battery" in problem_lower:
            return "laptop battery repair shop"
        elif "keyboard" in problem_lower:
            return "laptop keyboard repair shop"
        else:
            return "laptop repair shop"
    
    elif any(word in problem_lower for word in ["car", "vehicle", "automobile", "auto"]):
        if "battery" in problem_lower:
            return "car battery repair shop"
        elif "engine" in problem_lower:
            return "car engine repair shop"
        elif "brake" in problem_lower:
            return "car brake repair shop"
        else:
            return "auto repair shop"
    
    elif any(word in problem_lower for word in ["tv", "television", "monitor", "display"]):
        return "TV repair shop"
    
    elif any(word in problem_lower for word in ["appliance", "refrigerator", "washer", "dryer"]):
        return "appliance repair shop"
    
    elif any(word in problem_lower for word in ["light", "switch", "electrical", "wiring", "outlet", "socket", "bulb", "lamp", "fixture"]):
        return "electrical repair shop"
    
    elif any(word in problem_lower for word in ["plumbing", "pipe", "faucet", "toilet", "sink", "drain", "leak"]):
        return "plumbing repair shop"
    
    elif any(word in problem_lower for word in ["furniture", "chair", "table", "desk", "cabinet", "wood"]):
        return "furniture repair shop"
    
    elif any(word in problem_lower for word in ["bicycle", "bike", "cycle"]):
        return "bicycle repair shop"
    
    elif any(word in problem_lower for word in ["watch", "clock", "timepiece"]):
        return "watch repair shop"
    
    elif any(word in problem_lower for word in ["jewelry", "ring", "necklace", "bracelet"]):
        return "jewelry repair shop"
    
    else:
        # Generic repair shop search - but be more specific
        return "general repair shop"


def search_local_repair_shops(
    latitude: float = DEFAULT_LAT,
    longitude: float = DEFAULT_LNG,
    radius: int = DEFAULT_RADIUS,
    max_results: int = DEFAULT_MAX_RESULTS,
    user_id: str = None
) -> Dict[str, Any]:
    """
    Search for local repair shops using the query from the JSON file
    Now supports user-specific query loading when user_id is provided
    
    Args:
        latitude: Latitude for search location
        longitude: Longitude for search location  
        radius: Search radius in meters
        max_results: Maximum number of results to return
        user_id: Optional user ID for user-specific query loading
        
    Returns:
        Dict with search results and metadata in JSON schema format
    """
    try:
        # Load query using the new LocalUserStorage system
        if user_id:
            # Use the new local user storage system
            query_data = local_user_storage.get_user_query(user_id)
            print(f"DEBUG: Retrieved query from LocalUserStorage for user {user_id}")
        else:
            # Fallback to old file system for backward compatibility
            query_data = load_query_from_file()
            print(f"DEBUG: Retrieved query from legacy file system")
        
        if not query_data:
            # Return JSON schema format for no query
            json_response = {
                "title": "Local Repair Shops",
                "shops": {},
                "google_maps_links": {},
                "search_info": "No query available for repair shop search",
                "total_found": 0
            }
            content = convert_json_to_text(json_response, ResponseType.LOCAL_REPAIR_SHOPS)
            return {
                "success": False,
                "error": "No query found in file. Please run a repair query first.",
                "places": [],
                "content": content,
                "local_repair_links": [],
                "json_response": json_response
            }
        
        problem_statement = query_data.get("problem_statement", query_data.get("query", ""))
        
        # Generate repair shop search query
        repair_shop_query = generate_repair_shop_query(problem_statement)
        print(f"DEBUG: Generated repair shop query: '{repair_shop_query}'")
        
        # Extract device type for better search
        device_type = "general"  # Default
        problem_lower = problem_statement.lower()
        if any(word in problem_lower for word in ["laptop", "computer", "pc"]):
            device_type = "laptop"
        elif any(word in problem_lower for word in ["car", "vehicle", "automobile"]):
            device_type = "car"
        elif any(word in problem_lower for word in ["phone", "iphone", "android", "smartphone"]):
            device_type = "phone"
        elif any(word in problem_lower for word in ["light", "switch", "electrical", "wiring", "outlet", "socket", "bulb", "lamp", "fixture"]):
            device_type = "electrical"
        elif any(word in problem_lower for word in ["plumbing", "pipe", "faucet", "toilet", "sink", "drain", "leak"]):
            device_type = "plumbing"
        elif any(word in problem_lower for word in ["furniture", "chair", "table", "desk", "cabinet", "wood"]):
            device_type = "furniture"
        elif any(word in problem_lower for word in ["bicycle", "bike", "cycle"]):
            device_type = "bicycle"
        elif any(word in problem_lower for word in ["watch", "clock", "timepiece"]):
            device_type = "watch"
        elif any(word in problem_lower for word in ["jewelry", "ring", "necklace", "bracelet"]):
            device_type = "jewelry"
        elif any(word in problem_lower for word in ["appliance", "refrigerator", "washer", "dryer"]):
            device_type = "appliance"
        
        # Search for repair shops using Google Maps
        print(f"DEBUG: Calling Google Maps API with - lat: {latitude}, lng: {longitude}, radius: {radius}")
        
        places = search_repair_shops_advanced(
            query=repair_shop_query,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            max_results=max_results,
            device_type=device_type
        )
        
        print(f"DEBUG: Google Maps search returned {len(places) if places else 0} places")
        
        if places and len(places) > 0:
            # Format the places into JSON schema format
            shops = {}
            google_maps_links = {}
            local_repair_links = []
            
            for i, place in enumerate(places, 1):
                # Create shop details string
                shop_details = f"{place['name']}\n"
                shop_details += f"Address: {place['address']}\n"
                
                if place.get('distance_km'):
                    shop_details += f"Distance: {place['distance_km']} km away\n"
                
                if place.get('phone'):
                    shop_details += f"Phone: {place['phone']}\n"
                
                if place.get('website'):
                    shop_details += f"Website: {place['website']}\n"
                
                if place.get('rating'):
                    shop_details += f"Rating: {place['rating']}/5.0\n"
                
                if place.get('business_status'):
                    status_text = "Open" if place['business_status'] == "OPERATIONAL" else "Closed"
                    shop_details += f"Status: {status_text}"
                
                shops[str(i)] = shop_details.strip()
                
                # Add Google Maps URL using business name + address (most reliable)
                query = f"{place['name']}, {place['address']}"
                encoded_query = urllib.parse.quote_plus(query)
                google_maps_url = f"https://www.google.com/maps/search/{encoded_query}"
                
                google_maps_links[str(i)] = google_maps_url
                local_repair_links.append(google_maps_url)
            
            # Create JSON schema response
            json_response = {
                "title": f"Local Repair Shops for {problem_statement}",
                "shops": shops,
                "google_maps_links": google_maps_links,
                "search_info": f"Searched within {radius // 1000}km radius for {repair_shop_query}",
                "total_found": len(places)
            }
            
            # Convert to readable text using JSON schema
            content = convert_json_to_text(json_response, ResponseType.LOCAL_REPAIR_SHOPS)
            
            return {
                "success": True,
                "places": places,
                "content": content,
                "local_repair_links": local_repair_links,
                "json_response": json_response,
                "metadata": {
                    "source": "Google Maps",
                    "search_type": "local_repair_shops",
                    "places_found": len(places),
                    "device_type": device_type,
                    "search_radius_km": radius // 1000,
                    "search_query": repair_shop_query,
                    "problem_statement": problem_statement
                }
            }
        else:
            # No results found - return JSON schema format
            json_response = {
                "title": f"Local Repair Shops for {problem_statement}",
                "shops": {},
                "google_maps_links": {},
                "search_info": f"No repair shops found for: {problem_statement}",
                "total_found": 0
            }
            content = convert_json_to_text(json_response, ResponseType.LOCAL_REPAIR_SHOPS)
            
            return {
                "success": False,
                "error": "No repair shops found",
                "places": [],
                "content": content,
                "local_repair_links": [],
                "json_response": json_response,
                "metadata": {
                    "source": "Google Maps",
                    "search_type": "local_repair_shops",
                    "places_found": 0,
                    "problem_statement": problem_statement
                }
            }
        
    except Exception as e:
        # Error case - return JSON schema format
        json_response = {
            "title": "Local Repair Shops",
            "shops": {},
            "google_maps_links": {},
            "search_info": f"Error searching for repair shops: {str(e)}",
            "total_found": 0
        }
        content = convert_json_to_text(json_response, ResponseType.LOCAL_REPAIR_SHOPS)
        
        return {
            "success": False,
            "error": f"Error searching for repair shops: {str(e)}",
            "places": [],
            "content": content,
            "local_repair_links": [],
            "json_response": json_response
        }


def main():
    """
    Main function for testing the LocalRepairTool
    """
    print("🔧 LocalRepairTool - Testing...")
    
    # Test saving a query
    test_query = "Help me fix my cracked iPhone screen"
    test_problem = "how to fix cracked phone screen"
    
    print(f"\n1. Saving test query: '{test_query}'")
    save_success = save_query_to_file(test_query, test_problem)
    print(f"   Save successful: {save_success}")
    
    # Test loading the query
    print(f"\n2. Loading query from file...")
    loaded_data = load_query_from_file()
    if loaded_data:
        print(f"   Loaded query: '{loaded_data.get('query')}'")
        print(f"   Loaded problem: '{loaded_data.get('problem_statement')}'")
    else:
        print("   Failed to load query")
        return
    
    # Test searching for repair shops
    print(f"\n3. Searching for local repair shops...")
    result = search_local_repair_shops()
    
    print(f"   Search successful: {result['success']}")
    print(f"   Places found: {len(result.get('places', []))}")
    print(f"   Links generated: {len(result.get('local_repair_links', []))}")
    
    if result['success']:
        print(f"\n4. Full Content:")
        print("=" * 60)
        print(result['content'])
        print("=" * 60)
        
        if result.get('local_repair_links'):
            print(f"\n5. Google Maps Links:")
            for i, link in enumerate(result['local_repair_links'], 1):
                print(f"   {i}. {link}")
        
        if result.get('metadata'):
            print(f"\n6. Metadata:")
            for key, value in result['metadata'].items():
                print(f"   {key}: {value}")
    else:
        print(f"   Error: {result.get('error', 'Unknown error')}")
        if result.get('content'):
            print(f"\n   Content: {result['content']}")


if __name__ == "__main__":
    main()
