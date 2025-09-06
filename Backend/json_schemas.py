"""
JSON Schema definitions and utilities for structured LLM responses.
This module ensures all LLM responses follow a consistent JSON format
to avoid markdown formatting issues.
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ResponseType(Enum):
    """Types of responses the LLM can generate"""
    REPAIR_STEPS = "repair_steps"
    DEVICE_EXTRACTION = "device_extraction"
    SEARCH_TERMS = "search_terms"
    REPAIR_PLAN = "repair_plan"
    CONVERSATION = "conversation"
    DECISION = "decision"
    PROBLEM_EXTRACTION = "problem_extraction"
    AGGREGATION = "aggregation"
    LOCAL_REPAIR_SHOPS = "local_repair_shops"


@dataclass
class JSONSchema:
    """Base class for JSON schemas"""
    response_type: ResponseType
    schema: Dict[str, Any]
    example: Dict[str, Any]


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================

def get_repair_steps_schema() -> JSONSchema:
    """Schema for repair step responses"""
    return JSONSchema(
        response_type=ResponseType.REPAIR_STEPS,
        schema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title describing the repair task"},
                "steps": {
                    "type": "object",
                    "description": "Numbered steps for the repair process",
                    "patternProperties": {
                        "^[0-9]+$": {"type": "string", "description": "Step content"}
                    }
                },
                "tools_needed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tools required"
                },
                "materials_needed": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "List of materials required"
                },
                "safety_precautions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Important safety considerations"
                },
                "estimated_time": {"type": "string", "description": "Estimated completion time"},
                "difficulty": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Difficulty rating 1-10"},
                "sources": {
                    "type": "object",
                    "description": "Source URLs used",
                    "patternProperties": {
                        "^[0-9]+$": {"type": "string", "description": "Source URL"}
                    }
                }
            },
            "required": ["title", "steps", "sources"]
        },
        example={
            "title": "Steps to fix cracked phone screen",
            "steps": {
                "1": "Power off the device completely",
                "2": "Remove the back cover carefully",
                "3": "Disconnect the battery connector",
                "4": "Remove the old screen assembly",
                "5": "Install the new screen assembly",
                "6": "Reconnect the battery and test"
            },
            "tools_needed": ["Phillips screwdriver", "Plastic pry tool", "Suction cup"],
            "materials_needed": ["Replacement screen", "Adhesive strips"],
            "safety_precautions": ["Work in a clean environment", "Avoid static electricity"],
            "estimated_time": "30-45 minutes",
            "difficulty": 6,
            "sources": {
                "1": "https://example.com/guide1",
                "2": "https://example.com/guide2"
            }
        }
    )


def get_device_extraction_schema() -> JSONSchema:
    """Schema for device and problem extraction"""
    return JSONSchema(
        response_type=ResponseType.DEVICE_EXTRACTION,
        schema={
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "The specific device type"},
                "problem": {"type": "string", "description": "The specific problem description"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Confidence score"}
            },
            "required": ["device", "problem", "confidence"]
        },
        example={
            "device": "iPhone 12",
            "problem": "cracked screen",
            "confidence": 0.9
        }
    )


def get_search_terms_schema() -> JSONSchema:
    """Schema for search term generation"""
    return JSONSchema(
        response_type=ResponseType.SEARCH_TERMS,
        schema={
            "type": "object",
            "properties": {
                "search_terms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Exactly 3 search terms"
                }
            },
            "required": ["search_terms"]
        },
        example={
            "search_terms": [
                "iPhone 12 cracked screen repair",
                "iPhone 12 screen replacement guide", 
                "fix cracked iPhone screen"
            ]
        }
    )


def get_repair_plan_schema() -> JSONSchema:
    """Schema for repair planning"""
    return JSONSchema(
        response_type=ResponseType.REPAIR_PLAN,
        schema={
            "type": "object",
            "properties": {
                "tools_required": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of required tools"
                },
                "safety_precautions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Safety considerations"
                },
                "steps": {
                    "type": "object",
                    "description": "Numbered repair steps",
                    "patternProperties": {
                        "^[0-9]+$": {"type": "string", "description": "Step content"}
                    }
                },
                "success_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "How to know if repair was successful"
                },
                "seek_help_if": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "When to seek professional help"
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Confidence score"}
            },
            "required": ["tools_required", "safety_precautions", "steps", "confidence"]
        },
        example={
            "tools_required": ["Screwdriver set", "Plastic pry tools", "Suction cup"],
            "safety_precautions": ["Power off device", "Work in clean area", "Avoid static"],
            "steps": {
                "1": "Power off the device",
                "2": "Remove back cover",
                "3": "Disconnect battery",
                "4": "Replace screen",
                "5": "Reassemble device"
            },
            "success_criteria": ["Screen displays correctly", "Touch response works", "No dead pixels"],
            "seek_help_if": ["Screen doesn't turn on", "Touch doesn't work", "Visible damage to internals"],
            "confidence": 0.8
        }
    )


def get_conversation_schema() -> JSONSchema:
    """Schema for conversational responses"""
    return JSONSchema(
        response_type=ResponseType.CONVERSATION,
        schema={
            "type": "object",
            "properties": {
                "response": {"type": "string", "description": "The conversational response"},
                "tone": {"type": "string", "description": "Tone of the response (friendly, helpful, etc.)"},
                "context_used": {"type": "boolean", "description": "Whether conversation history was used"}
            },
            "required": ["response"]
        },
        example={
            "response": "I can see your phone screen is cracked. This typically happens from drops or impacts. The good news is that screen replacements are quite common and can usually be done successfully.",
            "tone": "helpful",
            "context_used": True
        }
    )


def get_decision_schema() -> JSONSchema:
    """Schema for decision making"""
    return JSONSchema(
        response_type=ResponseType.DECISION,
        schema={
            "type": "object",
            "properties": {
                "decision": {"type": "string", "enum": ["conversation", "problem_identification"], "description": "The decision made"},
                "reasoning": {"type": "string", "description": "Brief explanation of the decision"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Confidence in the decision"}
            },
            "required": ["decision", "confidence"]
        },
        example={
            "decision": "problem_identification",
            "reasoning": "User is explicitly asking for help to fix something",
            "confidence": 0.9
        }
    )


def get_problem_extraction_schema() -> JSONSchema:
    """Schema for problem extraction"""
    return JSONSchema(
        response_type=ResponseType.PROBLEM_EXTRACTION,
        schema={
            "type": "object",
            "properties": {
                "clean_query": {"type": "string", "description": "The cleaned, searchable query"},
                "original_query": {"type": "string", "description": "The original user input"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Confidence in extraction"}
            },
            "required": ["clean_query", "confidence"]
        },
        example={
            "clean_query": "how to fix cracked phone screen",
            "original_query": "My phone is flickering a lot, I've been trying to fix it, but my dog spilled coffee on it and now it won't start",
            "confidence": 0.8
        }
    )


def get_aggregation_schema() -> JSONSchema:
    """Schema for result aggregation"""
    return JSONSchema(
        response_type=ResponseType.AGGREGATION,
        schema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title for the repair instructions"},
                "steps": {
                    "type": "object",
                    "description": "Numbered repair steps",
                    "patternProperties": {
                        "^[0-9]+$": {"type": "string", "description": "Step content"}
                    }
                },
                "tools_needed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required tools"
                },
                "materials_needed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required materials"
                },
                "sources": {
                    "type": "object",
                    "description": "Source URLs",
                    "patternProperties": {
                        "^[0-9]+$": {"type": "string", "description": "Source URL"}
                    }
                }
            },
            "required": ["title", "steps", "sources"]
        },
        example={
            "title": "Steps to fix your cracked phone screen",
            "steps": {
                "1": "Power off the device completely",
                "2": "Remove the back cover carefully",
                "3": "Disconnect the battery connector",
                "4": "Remove the old screen assembly",
                "5": "Install the new screen assembly"
            },
            "tools_needed": ["Phillips screwdriver", "Plastic pry tool"],
            "materials_needed": ["Replacement screen"],
            "sources": {
                "1": "https://example.com/guide1",
                "2": "https://example.com/guide2"
            }
        }
    )


def get_local_repair_shops_schema() -> JSONSchema:
    """Schema for local repair shop listings"""
    return JSONSchema(
        response_type=ResponseType.LOCAL_REPAIR_SHOPS,
        schema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title for the repair shops listing"},
                "shops": {
                    "type": "object",
                    "description": "Numbered repair shop listings",
                    "patternProperties": {
                        "^[0-9]+$": {"type": "string", "description": "Shop details"}
                    }
                },
                "google_maps_links": {
                    "type": "object",
                    "description": "Google Maps URLs for each shop",
                    "patternProperties": {
                        "^[0-9]+$": {"type": "string", "description": "Google Maps URL"}
                    }
                },
                "search_info": {"type": "string", "description": "Search parameters used"},
                "total_found": {"type": "integer", "description": "Number of shops found"}
            },
            "required": ["title", "shops"]
        },
        example={
            "title": "Local Repair Shops for cracked phone screen",
            "shops": {
                "1": "TechRepair Plus\nAddress: 123 Main St, City, State\nPhone: (555) 123-4567\nRating: 4.5/5\nDistance: 2.3 km away",
                "2": "QuickFix Mobile\nAddress: 456 Oak Ave, City, State\nPhone: (555) 987-6543\nRating: 4.2/5\nDistance: 3.1 km away"
            },
            "google_maps_links": {
                "1": "https://www.google.com/maps/place/?q=place_id:abc123",
                "2": "https://www.google.com/maps/place/?q=place_id:def456"
            },
            "search_info": "Searched within 5km radius for phone screen repair shops",
            "total_found": 2
        }
    )


# =============================================================================
# SCHEMA REGISTRY
# =============================================================================

SCHEMA_REGISTRY = {
    ResponseType.REPAIR_STEPS: get_repair_steps_schema(),
    ResponseType.DEVICE_EXTRACTION: get_device_extraction_schema(),
    ResponseType.SEARCH_TERMS: get_search_terms_schema(),
    ResponseType.REPAIR_PLAN: get_repair_plan_schema(),
    ResponseType.CONVERSATION: get_conversation_schema(),
    ResponseType.DECISION: get_decision_schema(),
    ResponseType.PROBLEM_EXTRACTION: get_problem_extraction_schema(),
    ResponseType.AGGREGATION: get_aggregation_schema(),
    ResponseType.LOCAL_REPAIR_SHOPS: get_local_repair_shops_schema()
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_schema_for_type(response_type: ResponseType) -> JSONSchema:
    """Get the schema for a specific response type"""
    return SCHEMA_REGISTRY.get(response_type)


def create_llm_prompt_with_schema(base_prompt: str, response_type: ResponseType) -> str:
    """Create an LLM prompt that includes JSON schema instructions"""
    schema = get_schema_for_type(response_type)
    if not schema:
        return base_prompt
    
    schema_prompt = f"""
{base_prompt}

IMPORTANT: You must respond with valid JSON only. Do not use markdown formatting, bullet points, or any other text formatting.

Use this exact JSON schema:
{json.dumps(schema.schema, indent=2)}

Example response:
{json.dumps(schema.example, indent=2)}

Return only the JSON object, no additional text or explanations.
"""
    return schema_prompt


def parse_llm_json_response(response_text: str, response_type: ResponseType) -> Dict[str, Any]:
    """Parse and validate LLM JSON response"""
    try:
        # Clean the response text
        cleaned_text = clean_json_response(response_text)
        
        # Parse JSON
        parsed_json = json.loads(cleaned_text)
        
        # Basic validation
        schema = get_schema_for_type(response_type)
        if schema:
            # Check required fields
            required_fields = schema.schema.get("required", [])
            for field in required_fields:
                if field not in parsed_json:
                    raise ValueError(f"Missing required field: {field}")
        
        return parsed_json
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response text: {response_text}")
        return create_fallback_response(response_type, response_text)
    except Exception as e:
        print(f"Response parsing error: {e}")
        return create_fallback_response(response_type, response_text)


def clean_json_response(response_text: str) -> str:
    """Clean LLM response to extract valid JSON"""
    # Remove any markdown code blocks
    response_text = re.sub(r'```json\s*', '', response_text)
    response_text = re.sub(r'```\s*$', '', response_text)
    response_text = re.sub(r'```\s*', '', response_text)
    
    # Remove any text before the first {
    first_brace = response_text.find('{')
    if first_brace != -1:
        response_text = response_text[first_brace:]
    
    # Remove any text after the last }
    last_brace = response_text.rfind('}')
    if last_brace != -1:
        response_text = response_text[:last_brace + 1]
    
    # Remove any trailing text or newlines
    response_text = response_text.strip()
    
    return response_text


def create_fallback_response(response_type: ResponseType, original_text: str) -> Dict[str, Any]:
    """Create a fallback response when JSON parsing fails"""
    fallbacks = {
        ResponseType.REPAIR_STEPS: {
            "title": "Repair Instructions",
            "steps": {"1": "Please try again with a more specific request"},
            "sources": {"1": "https://example.com"}
        },
        ResponseType.DEVICE_EXTRACTION: {
            "device": "unknown device",
            "problem": "repair needed",
            "confidence": 0.5
        },
        ResponseType.SEARCH_TERMS: {
            "search_terms": ["repair guide", "fix instructions", "troubleshooting"]
        },
        ResponseType.REPAIR_PLAN: {
            "tools_required": ["Basic tools"],
            "safety_precautions": ["Work carefully"],
            "steps": {"1": "Please provide more details"},
            "confidence": 0.5
        },
        ResponseType.CONVERSATION: {
            "response": original_text or "I'd be happy to help. Could you provide more details?"
        },
        ResponseType.DECISION: {
            "decision": "problem_identification",
            "confidence": 0.5
        },
        ResponseType.PROBLEM_EXTRACTION: {
            "clean_query": original_text or "repair help",
            "confidence": 0.5
        },
        ResponseType.AGGREGATION: {
            "title": "Repair Instructions",
            "steps": {"1": "Please try again with a more specific request"},
            "sources": {"1": "https://example.com"}
        }
    }
    
    return fallbacks.get(response_type, {"error": "Unknown response type"})


def convert_json_to_text(json_data: Dict[str, Any], response_type: ResponseType) -> str:
    """Convert structured JSON back to readable text format"""
    if response_type == ResponseType.REPAIR_STEPS or response_type == ResponseType.AGGREGATION:
        return convert_repair_steps_to_text(json_data)
    elif response_type == ResponseType.CONVERSATION:
        return json_data.get("response", "")
    elif response_type == ResponseType.DECISION:
        return json_data.get("decision", "problem_identification")
    elif response_type == ResponseType.PROBLEM_EXTRACTION:
        return json_data.get("clean_query", "")
    elif response_type == ResponseType.DEVICE_EXTRACTION:
        return f"Device: {json_data.get('device', 'unknown')}, Problem: {json_data.get('problem', 'unknown')}"
    elif response_type == ResponseType.SEARCH_TERMS:
        return "\n".join(json_data.get("search_terms", []))
    elif response_type == ResponseType.REPAIR_PLAN:
        return convert_repair_plan_to_text(json_data)
    elif response_type == ResponseType.LOCAL_REPAIR_SHOPS:
        return convert_local_repair_shops_to_text(json_data)
    else:
        return str(json_data)


def convert_repair_steps_to_text(json_data: Dict[str, Any]) -> str:
    """Convert repair steps JSON to readable text"""
    lines = []
    
    # Title
    title = json_data.get("title", "Repair Instructions")
    lines.append(f"Following are steps to fix {title.lower()}:")
    lines.append("")
    
    # Steps
    steps = json_data.get("steps", {})
    for step_num in sorted(steps.keys(), key=int):
        lines.append(f"{step_num}. {steps[step_num]}")
    
    lines.append("")
    
    # Tools needed
    tools = json_data.get("tools_needed", [])
    if tools:
        lines.append("Tools needed:")
        for i, tool in enumerate(tools, 1):
            lines.append(f"{i}. {tool}")
        lines.append("")
    
    # Materials needed
    materials = json_data.get("materials_needed", [])
    if materials:
        lines.append("Materials needed:")
        for i, material in enumerate(materials, 1):
            lines.append(f"{i}. {material}")
        lines.append("")
    
    # Sources
    sources = json_data.get("sources", {})
    if sources:
        lines.append("Sources:")
        for source_num in sorted(sources.keys(), key=int):
            lines.append(f"{source_num}. {sources[source_num]}")
    
    return "\n".join(lines)


def convert_repair_plan_to_text(json_data: Dict[str, Any]) -> str:
    """Convert repair plan JSON to readable text"""
    lines = []
    
    # Tools required
    tools = json_data.get("tools_required", [])
    if tools:
        lines.append("Tools needed:")
        for i, tool in enumerate(tools, 1):
            lines.append(f"{i}. {tool}")
        lines.append("")
    
    # Steps
    steps = json_data.get("steps", {})
    if steps:
        lines.append("Steps:")
        for step_num in sorted(steps.keys(), key=int):
            lines.append(f"{step_num}. {steps[step_num]}")
    
    return "\n".join(lines)


def convert_local_repair_shops_to_text(json_data: Dict[str, Any]) -> str:
    """Convert local repair shops JSON to readable text with clickable links"""
    lines = []
    
    # Shops - display each as individual card format
    shops = json_data.get("shops", {})
    google_maps_links = json_data.get("google_maps_links", {})
    
    if shops:
        for shop_num in sorted(shops.keys(), key=int):
            shop_info = shops[shop_num]
            lines.append(f"SHOP: {shop_info}")
            
            # Add Google Maps link if available (for Flutter to parse)
            if shop_num in google_maps_links:
                maps_url = google_maps_links[shop_num]
                lines.append(f"LINK: {maps_url}")
            lines.append("")  # Empty line between shops
    else:
        lines.append("No repair shops found in your area.")
    
    return "\n".join(lines)


# =============================================================================
# MAIN WORKFLOW FUNCTION
# =============================================================================

def process_llm_response_with_schema(
    llm_response: str, 
    response_type: ResponseType,
    return_format: str = "text"  # "text" or "json"
) -> Union[str, Dict[str, Any]]:
    """
    Main function to process LLM response using JSON schema
    
    Args:
        llm_response: Raw response from LLM
        response_type: Type of response expected
        return_format: "text" to get readable text, "json" to get parsed JSON
    
    Returns:
        Either formatted text or parsed JSON based on return_format
    """
    # Step 1: Parse JSON response
    parsed_json = parse_llm_json_response(llm_response, response_type)
    
    # Step 2: Return in requested format
    if return_format == "json":
        return parsed_json
    else:
        return convert_json_to_text(parsed_json, response_type)


if __name__ == "__main__":
    # Test the schema system
    test_response = '''
    {
        "title": "Steps to fix cracked phone screen",
        "steps": {
            "1": "Power off the device",
            "2": "Remove back cover",
            "3": "Replace screen"
        },
        "tools_needed": ["Screwdriver", "Pry tool"],
        "sources": {
            "1": "https://example.com"
        }
    }
    '''
    
    result = process_llm_response_with_schema(
        test_response, 
        ResponseType.REPAIR_STEPS, 
        return_format="text"
    )
    print("Test result:")
    print(result)
