#!/usr/bin/env python3
"""
UpcycleIdeasTool - Tool for generating creative upcycling ideas
This tool reads a query from JSON files and generates creative upcycling ideas using LLM
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

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
POST_DATA_FILE_PATH = Path(__file__).parent.parent / "post_data.json"


def call_llm_for_upcycle_ideas(prompt: str) -> str:
    """Call the LLM to generate upcycling ideas"""
    try:
        # Initialize the LLM - using same model as FixAgent.py
        llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url=OLLAMA_BASE_URL,
            temperature=0.7  # Higher temperature for creative upcycling ideas
        )
        
        # Call the LLM
        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        print(f"ERROR: LLM call failed: {e}")
        return None




def load_query_from_files(user_id: str = None) -> Optional[Dict[str, str]]:
    """
    Load the query from user-specific storage or post_data.json
    Prioritizes user-specific storage when user_id is provided
    
    Args:
        user_id: Optional user ID for user-specific query loading
        
    Returns:
        Dict with 'query' and 'problem_statement' keys, or None if no files exist
    """
    try:
        # First try user-specific storage if user_id is provided
        if user_id:
            query_data = local_user_storage.get_user_query(user_id)
            if query_data:
                print(f"DEBUG: Retrieved query from LocalUserStorage for user {user_id}")
                return query_data
        
        # Try post_data.json as fallback
        if POST_DATA_FILE_PATH.exists():
            with open(POST_DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                post_data = json.load(f)
            # Extract query from post data
            query_data = {
                "query": post_data.get("query", ""),
                "problem_statement": post_data.get("item_name", post_data.get("query", "")),
            }
            print(f"DEBUG: Loaded query from {POST_DATA_FILE_PATH}")
            return query_data
        
        print("DEBUG: No query files found")
        return None
        
    except Exception as e:
        print(f"ERROR: Failed to load query from files: {e}")
        return None


def generate_upcycle_ideas(user_id: str = None) -> Dict[str, Any]:
    """
    Generate creative upcycling ideas using LLM based on the query from JSON files
    
    Args:
        user_id: Optional user ID for user-specific query loading
        
    Returns:
        Dict with upcycling ideas and metadata in JSON schema format
    """
    try:
        # Load query from files
        query_data = load_query_from_files(user_id)
        
        if not query_data:
            # Return JSON schema format for no query
            json_response = {
                "title": "Upcycling Ideas",
                "ideas": {},
                "general_tips": ["No query available for upcycling ideas generation"],
                "safety_notes": ["Please run a repair query first to get upcycling ideas"]
            }
            content = convert_json_to_text(json_response, ResponseType.UPCYCLE_IDEAS)
            return {
                "success": False,
                "error": "No query found in files. Please run a repair query first.",
                "content": content,
                "json_response": json_response
            }
        
        query = query_data.get("query", "")
        problem_statement = query_data.get("problem_statement", query)
        
        print(f"DEBUG: Generating upcycling ideas for: '{problem_statement}'")
        
        # Create the LLM prompt for upcycling ideas using the same schema system as FixAgent.py
        base_prompt = f"""You are a creative upcycling expert. Based on the following repair query, generate creative and practical upcycling ideas for the item mentioned. 

IMPORTANT: This is NOT about fixing the item - it's about creative ways to repurpose or upcycle it into something new and useful.

Original Query: "{query}"
Problem Statement: "{problem_statement}"

Generate 3-5 creative upcycling ideas that transform this SPECIFIC item into something new and useful. Be very specific to the item mentioned in the query. Focus on:
- Creative repurposing possibilities specific to this item
- Practical new uses that make sense for this item's shape, size, and material
- DIY project ideas that are realistic for this item
- Environmental benefits of upcycling this specific item
- Fun and innovative approaches tailored to this item

Each idea should include:
- A catchy title specific to the item
- Detailed description of the upcycling project
- Materials needed (beyond the original item)
- Difficulty level
- Time required
- Creative tips and variations

Also provide general upcycling tips and safety considerations."""

        # Use the same schema system as FixAgent.py
        prompt = create_llm_prompt_with_schema(base_prompt, ResponseType.UPCYCLE_IDEAS)

        # Call the LLM to generate upcycling ideas
        print(f"DEBUG: Calling LLM for upcycling ideas...")
        llm_response = call_llm_for_upcycle_ideas(prompt)
        
        if llm_response:
            print(f"DEBUG: LLM response received, length: {len(llm_response)}")
            # Parse the LLM response using JSON schema
            try:
                parsed_response = parse_llm_json_response(llm_response, ResponseType.UPCYCLE_IDEAS)
                print(f"DEBUG: Successfully parsed LLM response")
            except Exception as e:
                print(f"ERROR: Failed to parse LLM response: {e}")
                # Fallback to mock response if parsing fails
                parsed_response = {
                    "title": f"Creative Upcycling Ideas for {problem_statement}",
                    "ideas": {
                        "1": {
                            "title": "Garden Planter Transformation",
                            "description": "Transform the broken item into a unique garden planter. Clean and prepare the item, add drainage holes if needed, and fill with soil and plants for a creative garden feature.",
                            "materials_needed": ["Drill with appropriate bits", "Potting soil", "Plants or seeds", "Drainage rocks", "Paint (optional)"],
                            "difficulty": "Easy",
                            "time_required": "1-2 hours",
                            "creative_tips": ["Paint the exterior for a personalized look", "Use as a herb garden", "Create a themed planter with decorations"]
                        }
                    },
                    "general_tips": [
                        "Always clean and sanitize items thoroughly before upcycling",
                        "Consider the item's material when choosing upcycling projects",
                        "Think about the item's shape and size for creative possibilities",
                        "Upcycling reduces waste and gives items a second life"
                    ],
                    "safety_notes": [
                        "Wear appropriate safety gear when using tools",
                        "Ensure proper ventilation when using paints or adhesives",
                        "Check for sharp edges and handle carefully"
                    ]
                }
        else:
            print(f"ERROR: LLM call failed, using fallback response")
            # Fallback response if LLM fails
            parsed_response = {
                "title": f"Creative Upcycling Ideas for {problem_statement}",
                "ideas": {
                    "1": {
                        "title": "Garden Planter Transformation",
                        "description": "Transform the broken item into a unique garden planter. Clean and prepare the item, add drainage holes if needed, and fill with soil and plants for a creative garden feature.",
                        "materials_needed": ["Drill with appropriate bits", "Potting soil", "Plants or seeds", "Drainage rocks", "Paint (optional)"],
                        "difficulty": "Easy",
                        "time_required": "1-2 hours",
                        "creative_tips": ["Paint the exterior for a personalized look", "Use as a herb garden", "Create a themed planter with decorations"]
                    }
                },
                "general_tips": [
                    "Always clean and sanitize items thoroughly before upcycling",
                    "Consider the item's material when choosing upcycling projects",
                    "Think about the item's shape and size for creative possibilities",
                    "Upcycling reduces waste and gives items a second life"
                ],
                "safety_notes": [
                    "Wear appropriate safety gear when using tools",
                    "Ensure proper ventilation when using paints or adhesives",
                    "Check for sharp edges and handle carefully"
                ]
            }
        
        # Convert to readable text using JSON schema
        content = convert_json_to_text(parsed_response, ResponseType.UPCYCLE_IDEAS)
        
        return {
            "success": True,
            "content": content,
            "json_response": parsed_response,
            "metadata": {
                "source": "UpcycleIdeasTool",
                "search_type": "upcycling_ideas",
                "query": query,
                "problem_statement": problem_statement
            }
        }
        
    except Exception as e:
        # Error case - return JSON schema format
        json_response = {
            "title": "Upcycling Ideas",
            "ideas": {},
            "general_tips": [f"Error generating upcycling ideas: {str(e)}"],
            "safety_notes": ["Please try again or contact support"]
        }
        content = convert_json_to_text(json_response, ResponseType.UPCYCLE_IDEAS)
        
        return {
            "success": False,
            "error": f"Error generating upcycling ideas: {str(e)}",
            "content": content,
            "json_response": json_response
        }


def main():
    """
    Main function for testing the UpcycleIdeasTool
    """
    print("♻️ UpcycleIdeasTool - Testing...")
    
    # Test generating upcycling ideas
    print(f"\n1. Generating upcycling ideas...")
    result = generate_upcycle_ideas()
    
    print(f"   Generation successful: {result['success']}")
    
    if result['success']:
        print(f"\n2. Full Content:")
        print("=" * 60)
        print(result['content'])
        print("=" * 60)
        
        if result.get('metadata'):
            print(f"\n3. Metadata:")
            for key, value in result['metadata'].items():
                print(f"   {key}: {value}")
    else:
        print(f"   Error: {result.get('error', 'Unknown error')}")
        if result.get('content'):
            print(f"\n   Content: {result['content']}")


if __name__ == "__main__":
    main()
