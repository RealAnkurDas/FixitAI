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
from googlemaps_tool import search_repair_shops_advanced

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

# Import LLM utilities
from langchain_ollama import ChatOllama
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get OLLAMA_BASE_URL from environment, default to localhost:11434
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

# Import the new LocalUserStorage
from local_user_storage import local_user_storage

# Configuration
DEFAULT_LAT = 0.0  # Default coordinates
DEFAULT_LNG = 0.0
DEFAULT_RADIUS = 5000  # 5km radius
DEFAULT_MAX_RESULTS = 5


def save_query_to_file(query: str, problem_statement: str = None, user_id: str = None) -> bool:
    """
    DEPRECATED: This function is no longer used. 
    Queries are now saved directly via LocalUserStorage in the API.
    This function is kept for backward compatibility but does nothing.
    
    Args:
        query: The original user query
        problem_statement: The extracted problem statement
        user_id: Optional user ID for user-specific storage
        
    Returns:
        bool: Always returns True (no-op)
    """
    print(f"DEBUG: save_query_to_file() called but is deprecated. Use LocalUserStorage directly.")
    return True


def load_query_from_file(user_id: str = None) -> Optional[Dict[str, str]]:
    """
    DEPRECATED: This function is no longer used.
    Queries are now loaded directly via LocalUserStorage.
    This function is kept for backward compatibility but returns None.
    
    Args:
        user_id: Optional user ID for user-specific query loading
        
    Returns:
        None (deprecated function)
    """
    print(f"DEBUG: load_query_from_file() called but is deprecated. Use LocalUserStorage directly.")
    return None


def clear_query_file(user_id: str = None) -> bool:
    """
    DEPRECATED: This function is no longer used.
    Queries are now cleared directly via LocalUserStorage.
    This function is kept for backward compatibility but returns True.
    
    Args:
        user_id: Optional user ID for user-specific query clearing
        
    Returns:
        bool: Always returns True (no-op)
    """
    print(f"DEBUG: clear_query_file() called but is deprecated. Use LocalUserStorage directly.")
    return True


def call_llm_for_repair_shop_query(problem_statement: str) -> str:
    """Call the LLM to generate an intelligent repair shop search query"""
    try:
        # Initialize the LLM - using same model as FixAgent.py
        llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url=OLLAMA_BASE_URL,
            temperature=0.3  # Lower temperature for more consistent results
        )
        
        prompt = f"""You are an expert at determining the best type of repair shop to search for based on a problem description.

Given this problem statement: "{problem_statement}"

Generate a specific, accurate search query for finding local repair shops that can handle this type of repair. 

Rules:
1. Be very specific to the item and problem mentioned
2. Use common repair shop terminology
3. Focus on the type of repair shop, not the specific problem
4. Return ONLY the search query, nothing else
5. Examples:
   - "broken photo frame" → "picture frame repair shop"
   - "cracked iPhone screen" → "phone screen repair shop" 
   - "leaky faucet" → "plumbing repair shop"
   - "broken bicycle chain" → "bicycle repair shop"
   - "watch not working" → "watch repair shop"
   - "broken laptop keyboard" → "laptop repair shop"

Search query:"""

        # Call the LLM
        response = llm.invoke(prompt)
        query = response.content.strip()
        
        print(f"DEBUG: LLM generated repair shop query: '{query}'")
        return query
        
    except Exception as e:
        print(f"ERROR: LLM call failed: {e}")
        return None


def generate_repair_shop_query(problem_statement: str) -> str:
    """
    Generate a search query for finding local repair shops based on the problem statement
    Uses LLM to intelligently determine the best repair shop type
    
    Args:
        problem_statement: The extracted problem statement
        
    Returns:
        str: Search query for repair shops
    """
    print(f"DEBUG: Generating repair shop query for: '{problem_statement}'")
    
    # Try LLM first for intelligent query generation
    llm_query = call_llm_for_repair_shop_query(problem_statement)
    
    if llm_query and llm_query.strip():
        print(f"DEBUG: Using LLM-generated query: '{llm_query}'")
        return llm_query.strip()
    
    # No fallback logic - if LLM fails, return the original problem statement
    print(f"DEBUG: LLM failed, using original problem statement as search query")
    return problem_statement


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
        # Load query using the LocalUserStorage system (user_id is required)
        if not user_id:
            # Return error if no user_id provided
            json_response = {
                "title": "Local Repair Shops",
                "shops": {},
                "google_maps_links": {},
                "search_info": "User ID is required for repair shop search",
                "total_found": 0
            }
            content = convert_json_to_text(json_response, ResponseType.LOCAL_REPAIR_SHOPS)
            return {
                "success": False,
                "error": "User ID is required for repair shop search",
                "places": [],
                "content": content,
                "local_repair_links": [],
                "json_response": json_response
            }
        
        # Use the local user storage system
        query_data = local_user_storage.get_user_query(user_id)
        print(f"DEBUG: Retrieved query from LocalUserStorage for user {user_id}")
        
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
