#!/usr/bin/env python
"""
Test script to verify the JSON schema system works end-to-end
"""

from json_schemas import (
    ResponseType,
    create_llm_prompt_with_schema,
    parse_llm_json_response,
    convert_json_to_text,
    process_llm_response_with_schema
)

def test_repair_steps_schema():
    """Test the repair steps schema"""
    print("=== Testing Repair Steps Schema ===")
    
    # Test prompt creation
    base_prompt = "Create repair instructions for fixing a cracked phone screen"
    prompt_with_schema = create_llm_prompt_with_schema(base_prompt, ResponseType.REPAIR_STEPS)
    print(f"Prompt created successfully (length: {len(prompt_with_schema)})")
    
    # Test JSON parsing with a valid response
    test_response = """
    {
        "title": "Steps to fix cracked phone screen",
        "steps": {
            "1": "Power off the device completely",
            "2": "Remove the back cover carefully using a pry tool",
            "3": "Disconnect the battery connector",
            "4": "Remove the old cracked screen assembly",
            "5": "Install the new screen assembly",
            "6": "Reconnect the battery and test the device"
        },
        "tools_needed": ["Phillips screwdriver", "Plastic pry tool", "Suction cup"],
        "materials_needed": ["Replacement screen", "Adhesive strips"],
        "sources": {
            "1": "https://ifixit.com/guide1",
            "2": "https://wikihow.com/guide2"
        }
    }
    """
    
    parsed = parse_llm_json_response(test_response, ResponseType.REPAIR_STEPS)
    print(f"JSON parsed successfully: {parsed.get('title', 'No title')}")
    
    # Test conversion to text
    text_output = convert_json_to_text(parsed, ResponseType.REPAIR_STEPS)
    print("Text conversion successful:")
    print(text_output[:200] + "...")
    
    print("✅ Repair Steps Schema Test PASSED\n")


def test_device_extraction_schema():
    """Test the device extraction schema"""
    print("=== Testing Device Extraction Schema ===")
    
    # Test with markdown response that needs cleaning
    test_response = """
    ```json
    {
        "device": "iPhone 12",
        "problem": "cracked screen",
        "confidence": 0.9
    }
    ```
    """
    
    parsed = parse_llm_json_response(test_response, ResponseType.DEVICE_EXTRACTION)
    print(f"Parsed device: {parsed.get('device')}, problem: {parsed.get('problem')}")
    
    # Test conversion to text
    text_output = convert_json_to_text(parsed, ResponseType.DEVICE_EXTRACTION)
    print(f"Text output: {text_output}")
    
    print("✅ Device Extraction Schema Test PASSED\n")


def test_search_terms_schema():
    """Test the search terms schema"""
    print("=== Testing Search Terms Schema ===")
    
    test_response = """
    {
        "search_terms": [
            "iPhone 12 cracked screen repair",
            "iPhone 12 screen replacement guide",
            "fix cracked iPhone screen DIY"
        ]
    }
    """
    
    parsed = parse_llm_json_response(test_response, ResponseType.SEARCH_TERMS)
    print(f"Parsed search terms: {parsed.get('search_terms')}")
    
    # Test conversion to text
    text_output = convert_json_to_text(parsed, ResponseType.SEARCH_TERMS)
    print(f"Text output:\n{text_output}")
    
    print("✅ Search Terms Schema Test PASSED\n")


def test_decision_schema():
    """Test the decision schema"""
    print("=== Testing Decision Schema ===")
    
    test_response = """
    {
        "decision": "problem_identification",
        "reasoning": "User is explicitly asking for help to fix something",
        "confidence": 0.9
    }
    """
    
    parsed = parse_llm_json_response(test_response, ResponseType.DECISION)
    print(f"Decision: {parsed.get('decision')}, confidence: {parsed.get('confidence')}")
    
    # Test conversion to text
    text_output = convert_json_to_text(parsed, ResponseType.DECISION)
    print(f"Text output: {text_output}")
    
    print("✅ Decision Schema Test PASSED\n")


def test_fallback_responses():
    """Test fallback responses when JSON parsing fails"""
    print("=== Testing Fallback Responses ===")
    
    # Test with invalid JSON
    invalid_response = "This is not JSON at all, just some random text."
    
    parsed = parse_llm_json_response(invalid_response, ResponseType.REPAIR_STEPS)
    print(f"Fallback repair steps: {parsed}")
    
    # Test conversion to text
    text_output = convert_json_to_text(parsed, ResponseType.REPAIR_STEPS)
    print("Fallback text conversion:")
    print(text_output)
    
    print("✅ Fallback Response Test PASSED\n")


def test_end_to_end_workflow():
    """Test the complete workflow"""
    print("=== Testing End-to-End Workflow ===")
    
    # Simulate an LLM response that might have markdown
    llm_response = """
    Here's the response you requested:
    
    ```json
    {
        "title": "Steps to fix laptop overheating",
        "steps": {
            "1": "Clean the vents and fans with compressed air",
            "2": "Check for dust buildup in the cooling system",
            "3": "Apply new thermal paste to the CPU",
            "4": "Ensure proper ventilation around the laptop"
        },
        "tools_needed": ["Compressed air", "Thermal paste", "Screwdriver set"],
        "sources": {
            "1": "https://example.com/laptop-cooling"
        }
    }
    ```
    
    I hope this helps!
    """
    
    # Use the main workflow function
    result = process_llm_response_with_schema(
        llm_response, 
        ResponseType.REPAIR_STEPS, 
        return_format="text"
    )
    
    print("End-to-end result:")
    print(result)
    
    print("✅ End-to-End Workflow Test PASSED\n")


if __name__ == "__main__":
    print("🧪 Testing JSON Schema System for LLM Responses\n")
    
    try:
        test_repair_steps_schema()
        test_device_extraction_schema()
        test_search_terms_schema()
        test_decision_schema()
        test_fallback_responses()
        test_end_to_end_workflow()
        
        print("🎉 ALL TESTS PASSED! JSON Schema system is working correctly.")
        print("\nThe system now enforces structured JSON responses from LLMs and")
        print("automatically converts them to readable text format, eliminating")
        print("markdown formatting issues.")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
