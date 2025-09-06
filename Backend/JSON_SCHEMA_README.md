# JSON Schema System for LLM Responses

## Overview

This JSON Schema system solves a critical problem in LLM-based applications: **inconsistent and markdown-formatted responses**. Instead of receiving unpredictable text with markdown formatting, bullet points, and inconsistent structure, this system enforces structured JSON responses from LLMs and automatically converts them to clean, readable text.

## The Problem We Solved

### Before (Problematic LLM Responses)
```
LLM Response: "## Here are the steps to fix your phone:

**Step 1:** Power off the device
- Make sure to hold the power button
- *Wait for complete shutdown*

**Step 2:** Remove the back cover
- Use a plastic tool
- **Be very careful!**

### Tools needed:
- Screwdriver 
- Plastic pry tool

**Sources:**
1. [iFixit Guide](https://ifixit.com/guide1)
2. [WikiHow Article](https://wikihow.com/article1)"
```

**Issues:**
- ❌ Markdown formatting (##, **, *, etc.)
- ❌ Inconsistent structure
- ❌ Mixed formatting styles
- ❌ Hard to parse programmatically
- ❌ Unpredictable output format

### After (Structured JSON System)
```json
{
  "title": "Steps to fix cracked phone screen",
  "steps": {
    "1": "Power off the device completely",
    "2": "Remove the back cover carefully using a pry tool",
    "3": "Disconnect the battery connector",
    "4": "Replace the screen assembly"
  },
  "tools_needed": ["Phillips screwdriver", "Plastic pry tool"],
  "materials_needed": ["Replacement screen", "Adhesive strips"],
  "sources": {
    "1": "https://ifixit.com/guide1",
    "2": "https://wikihow.com/article1"
  }
}
```

**Benefits:**
- ✅ Consistent structure
- ✅ No markdown formatting
- ✅ Easily parseable
- ✅ Predictable output
- ✅ Automatic text conversion

## How It Works

### 1. Schema Definition
Each type of LLM response has a predefined JSON schema:

```python
from json_schemas import ResponseType

# Available schema types:
- ResponseType.REPAIR_STEPS      # Step-by-step repair instructions
- ResponseType.DEVICE_EXTRACTION # Device and problem identification
- ResponseType.SEARCH_TERMS      # Search term generation
- ResponseType.REPAIR_PLAN       # Comprehensive repair planning
- ResponseType.CONVERSATION      # Conversational responses
- ResponseType.DECISION          # Decision making
- ResponseType.PROBLEM_EXTRACTION # Problem extraction from text
- ResponseType.AGGREGATION       # Result aggregation
```

### 2. Prompt Enhancement
The system automatically adds JSON schema instructions to any prompt:

```python
from json_schemas import create_llm_prompt_with_schema

# Original prompt
base_prompt = "Create repair instructions for fixing a cracked phone screen"

# Enhanced with JSON schema
enhanced_prompt = create_llm_prompt_with_schema(base_prompt, ResponseType.REPAIR_STEPS)

# The enhanced prompt now includes:
# - The original instructions
# - JSON schema definition
# - Example JSON response
# - Strict formatting requirements
```

### 3. Response Processing
The system handles LLM responses automatically:

```python
from json_schemas import parse_llm_json_response

# Raw LLM response (may include markdown, extra text, etc.)
llm_response = '''
Here's what you need to do:

```json
{
  "title": "Steps to fix cracked phone screen",
  "steps": {
    "1": "Power off device",
    "2": "Remove back cover"
  },
  "sources": {"1": "https://example.com"}
}
```

Hope this helps!
'''

# Automatically cleaned and parsed
parsed_json = parse_llm_json_response(llm_response, ResponseType.REPAIR_STEPS)
# Result: Clean JSON object with validated structure
```

### 4. Text Conversion
Finally, convert structured JSON back to readable text:

```python
from json_schemas import convert_json_to_text

readable_text = convert_json_to_text(parsed_json, ResponseType.REPAIR_STEPS)

# Output:
# Following are steps to fix cracked phone screen:
# 
# 1. Power off device
# 2. Remove back cover
# 
# Sources:
# 1. https://example.com
```

## Implementation Examples

### Example 1: Device Extraction
```python
# In VisionAgent - extract device and problem from image analysis
base_prompt = f"""
Analyze this device and extract the device type and problem.
Analysis: {analysis_text}
"""

# Add JSON schema
prompt = create_llm_prompt_with_schema(base_prompt, ResponseType.DEVICE_EXTRACTION)

# Get LLM response
response = llm.invoke([HumanMessage(content=prompt)])

# Parse and extract
parsed = parse_llm_json_response(response.content, ResponseType.DEVICE_EXTRACTION)
device = parsed.get("device", "unknown")
problem = parsed.get("problem", "unknown")
confidence = parsed.get("confidence", 0.5)
```

### Example 2: Search Terms Generation
```python
# In ResearchAgent - generate search terms
base_prompt = f"""
Generate 3 search terms for finding repair guides for {device} {problem}.
"""

prompt = create_llm_prompt_with_schema(base_prompt, ResponseType.SEARCH_TERMS)
response = llm.invoke([HumanMessage(content=prompt)])
parsed = parse_llm_json_response(response.content, ResponseType.SEARCH_TERMS)
search_terms = parsed.get("search_terms", [])
```

### Example 3: Complete Workflow
```python
# End-to-end processing with automatic error handling
from json_schemas import process_llm_response_with_schema

# Raw LLM response (with potential markdown)
llm_response = "```json\n{\"steps\": {\"1\": \"Fix it\"}}\n```"

# Process and get clean text
final_text = process_llm_response_with_schema(
    llm_response, 
    ResponseType.REPAIR_STEPS, 
    return_format="text"
)
```

## Schema Definitions

### Repair Steps Schema
```json
{
  "title": "string - Description of the repair task",
  "steps": {
    "1": "string - First step",
    "2": "string - Second step"
  },
  "tools_needed": ["array of required tools"],
  "materials_needed": ["array of required materials"],
  "safety_precautions": ["array of safety notes"],
  "sources": {
    "1": "string - Source URL",
    "2": "string - Another source URL"
  }
}
```

### Device Extraction Schema
```json
{
  "device": "string - Device type (e.g., iPhone 12)",
  "problem": "string - Problem description (e.g., cracked screen)",
  "confidence": "number - Confidence score 0-1"
}
```

### Search Terms Schema
```json
{
  "search_terms": [
    "string - Search term 1",
    "string - Search term 2", 
    "string - Search term 3"
  ]
}
```

## Error Handling & Fallbacks

The system is robust and handles various failure scenarios:

### 1. Invalid JSON
```python
# LLM returns: "I can't help with that"
# System automatically provides fallback response
fallback = {
  "title": "Repair Instructions",
  "steps": {"1": "Please try again with a more specific request"},
  "sources": {"1": "https://example.com"}
}
```

### 2. Partial JSON
```python
# LLM returns: "```json\n{\"steps\": {\"1\": \"Fix\"}}\nSome extra text"
# System extracts valid JSON and ignores extra text
```

### 3. Missing Required Fields
```python
# System validates required fields and fills in defaults
# Ensures consistent structure even with incomplete responses
```

## Integration in Codebase

### Files Updated
1. **`json_schemas.py`** - Core schema system
2. **`FixAgent.py`** - All decision, conversation, aggregation nodes
3. **`AIAgent.py`** - VisionAgent, ResearchAgent, PlanningAgent
4. **`test_json_schemas.py`** - Comprehensive test suite

### Key Functions Modified
- `_make_decision_text_only()` - Now returns structured decision JSON
- `_generate_conversation_text_only()` - Returns structured conversation JSON
- `aggregator_agent()` - Uses JSON schema for result aggregation
- `VisionAgent._do_actual_work()` - Structured device extraction
- `ResearchAgent._do_actual_work()` - Structured search term generation
- `PlanningAgent._do_actual_work()` - Structured repair plan generation

## Benefits Achieved

### 1. Consistency
- **Before:** "## Steps:\n**1.** Do this\n- And that"
- **After:** "1. Do this\n2. Do that"

### 2. Reliability
- **Before:** Parsing failures with unexpected formats
- **After:** Guaranteed structure with fallbacks

### 3. Maintainability
- **Before:** Complex regex parsing for different formats
- **After:** Simple JSON parsing with validation

### 4. User Experience
- **Before:** Inconsistent formatting confuses users
- **After:** Clean, consistent instructions every time

### 5. Integration
- **Before:** Hard to integrate LLM responses with other systems
- **After:** Structured data easy to process and display

## Testing

Run the comprehensive test suite:

```bash
cd Backend
python test_json_schemas.py
```

Test results show:
- ✅ All schema types working correctly
- ✅ JSON parsing and cleaning functions
- ✅ Fallback responses for error cases
- ✅ End-to-end workflow validation
- ✅ Markdown cleanup functionality

## Usage Guidelines

### 1. Always Use Schemas for LLM Calls
```python
# ❌ Don't do this
response = llm.invoke([HumanMessage(content=raw_prompt)])
text = response.content  # Unpredictable format

# ✅ Do this instead
prompt = create_llm_prompt_with_schema(raw_prompt, ResponseType.REPAIR_STEPS)
response = llm.invoke([HumanMessage(content=prompt)])
parsed = parse_llm_json_response(response.content, ResponseType.REPAIR_STEPS)
text = convert_json_to_text(parsed, ResponseType.REPAIR_STEPS)
```

### 2. Choose Appropriate Schema Types
- Use `REPAIR_STEPS` for step-by-step instructions
- Use `DEVICE_EXTRACTION` for identifying devices and problems
- Use `CONVERSATION` for conversational responses
- Use `DECISION` for binary decisions

### 3. Handle Errors Gracefully
The system provides automatic fallbacks, but you can also check:
```python
parsed = parse_llm_json_response(response, ResponseType.REPAIR_STEPS)
if "error" in parsed:
    # Handle error case
    pass
```

## Future Enhancements

### Possible Extensions
1. **Additional Schema Types**
   - Diagnostic schemas for troubleshooting
   - Shopping schemas for parts/tools lists
   - Safety assessment schemas

2. **Validation Enhancements**
   - More strict validation rules
   - Custom validators for specific fields
   - Automatic quality scoring

3. **Multilingual Support**
   - Schema adaptations for different languages
   - Localized fallback responses

4. **Performance Optimizations**
   - Caching for frequently used schemas
   - Compressed schema representations

## Conclusion

This JSON Schema system transforms unreliable, markdown-heavy LLM responses into consistent, structured, and user-friendly text. It's a foundational improvement that makes the entire repair assistant system more reliable and maintainable.

The system follows the principle: **"Structure first, formatting second"** - ensuring that the semantic content is preserved and consistently formatted regardless of how the LLM initially responds.
