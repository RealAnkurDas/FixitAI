"""
FixAgent.py - Core Multi-Agent System for FixitAI

This module implements a LangGraph-based multi-agent workflow that orchestrates
repair assistance by combining LLM analysis with external data sources.

Architecture:
- conversation_node: Handles user queries and context management
- examine_node: Analyzes uploaded images using vision models  
- search_node: Coordinates external data source searches
- synthesize_node: Combines findings into comprehensive repair guidance

LLM Models:
- Qwen2.5vl:7b: Primary model for text and vision analysis
- Secondary model support for specific tasks

External Data Sources:
- iFixit: Repair guides and tutorials
- WikiHow: Step-by-step instructions
- Medium: Technical articles
- Tavily: AI-powered web search
- Google Maps: Local repair shop discovery
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from enum import Enum
import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

# Import JSON schema utilities
from json_schemas import (
    ResponseType, 
    create_llm_prompt_with_schema, 
    process_llm_response_with_schema,
    parse_llm_json_response,
    convert_json_to_text
)

# Import working search modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

try:
    from modules.ifixit_tool import search_ifixit_advanced
    from modules.medium_tool import search_medium_advanced  
    from modules.wikihow_tool import search_wikihow_advanced
    from modules.tavily_tool import search_tavily
    from modules.googlemaps_tool import search_repair_shops_advanced
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the Backend directory")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Get OLLAMA_BASE_URL from environment, default to localhost:11434
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')


# Define the state schema - FIX: Remove potential conflicts
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    query: str
    disambiguated_query: str  # Add disambiguated query field
    image_data: Optional[str]  # Add image data field
    conversation_history: List[Dict[str, Any]]  # Add conversation history
    decision_result: str  # "conversation" or "problem_identification"
    conversation_response: str  # Response from conversation node
    problem_statement: str
    wikihow_results: Dict[str, Any]
    ifixit_results: Dict[str, Any]
    medium_results: Dict[str, Any]
    tavily_results: Dict[str, Any]
    final_response: str
    response_source: str  # "conversation" or "problem_identification" - tells frontend where response came from
    local_repair_available: bool  # True if local repair search is available


# Query type classification
class QueryType(str, Enum):
    WIKIHOW = "wikihow"
    IFIXIT = "ifixit"
    MEDIUM = "medium"


# Pydantic models for structured outputs
class QueryClassification(BaseModel):
    """Classification of the user query"""
    query_type: QueryType = Field(description="The type of content needed for this query")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Brief explanation of the classification")


class AgentResult(BaseModel):
    """Standard result format for specialized agents"""
    content: str = Field(description="Main content found")
    source_urls: List[str] = Field(description="URLs of sources")
    metadata: Dict[str, Any] = Field(description="Additional metadata")
    success: bool = Field(description="Whether the agent succeeded")


class FinalResponse(BaseModel):
    """Final aggregated response"""
    instructions: str = Field(description="Coherent instruction set")
    difficulty_rating: int = Field(description="Difficulty from 1-10")
    safety_tips: List[str] = Field(description="Important safety considerations")
    sources: List[str] = Field(description="All source URLs used")
    estimated_time: str = Field(description="Estimated completion time")
    tools_needed: List[str] = Field(description="Tools required for the repair")
    materials_needed: List[str] = Field(description="Materials required for the repair")


# =============================================================================
# DISAMBIGUATION NODE
# =============================================================================

def disambiguation_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes the user query for ambiguous references and resolves them using conversation history.
    If the query is clear, it passes through unchanged. If ambiguous, it fills in missing details.
    """
    query = state["query"]
    conversation_history = state.get("conversation_history", [])
    
    # Create LLM instance
    llm = ChatOllama(
        model="qwen2.5vl:7b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )
    
    # Check if query has ambiguous references
    is_ambiguous = _check_ambiguity(query, conversation_history, llm)
    
    if is_ambiguous:
        # Resolve ambiguity using conversation history
        disambiguated_query = _resolve_ambiguity(query, conversation_history, llm)
        print(f"DEBUG: Disambiguation - Original: '{query}' -> Resolved: '{disambiguated_query}'")
    else:
        # Query is clear, pass through unchanged
        disambiguated_query = query
        print(f"DEBUG: Disambiguation - Query is clear: '{query}'")
    
    return {"disambiguated_query": disambiguated_query}


def _check_ambiguity(query: str, conversation_history: List[Dict[str, Any]], llm: ChatOllama) -> bool:
    """
    Check if the query contains ambiguous references that need clarification
    """
    ambiguity_prompt = ChatPromptTemplate.from_template("""
    Analyze this user query to determine if it contains ambiguous references that need clarification from conversation history.
    
    User Query: {query}
    
    Conversation History:
    {conversation_history}
    
    AMBIGUOUS INDICATORS:
    - Pronouns without clear antecedents: "it", "this", "that", "the problem", "the issue"
    - Vague references: "fix it", "help with that", "what about this", "the thing we discussed"
    - Incomplete requests: "how to fix", "what should I do", "can you help"
    - References to previous topics without context: "the phone", "the car", "the laptop"
    
    CLEAR INDICATORS:
    - Specific device/problem mentioned: "fix my iPhone screen", "repair the laptop battery"
    - Complete descriptions: "my phone won't turn on", "the car makes weird noises"
    - New topics with full context: "how to fix a leaky faucet"
    
    EXAMPLES:
    - "fix it" → AMBIGUOUS (what is "it"?)
    - "help me with that problem" → AMBIGUOUS (what problem?)
    - "what should I do about the phone" → AMBIGUOUS (which phone, what's wrong?)
    - "fix my cracked iPhone screen" → CLEAR (specific device and problem)
    - "how to repair a laptop that won't start" → CLEAR (complete description)
    
    Return ONLY "AMBIGUOUS" or "CLEAR" - no additional text.
    """)
    
    try:
        # Format conversation history for the prompt
        history_text = _format_conversation_history(conversation_history)
        
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=ambiguity_prompt.format(
            query=query,
            conversation_history=history_text
        ))])
        result = response.content.strip().upper()
        
        return result == "AMBIGUOUS"
        
    except Exception as e:
        print(f"DEBUG: Error checking ambiguity: {e}")
        # Default to ambiguous if we can't determine
        return True


def _resolve_ambiguity(query: str, conversation_history: List[Dict[str, Any]], llm: ChatOllama) -> str:
    """
    Resolve ambiguous references in the query using conversation history
    """
    resolution_prompt = ChatPromptTemplate.from_template("""
    You are a helpful assistant that resolves ambiguous references in user queries using conversation history.
    
    User Query: {query}
    
    Conversation History:
    {conversation_history}
    
    TASK:
    1. Identify what the user is referring to in their ambiguous query
    2. Find the relevant context from conversation history
    3. Create a clear, specific version of their query by filling in the missing details
    4. Keep the user's intent and tone intact
    5. Only add necessary context - don't change the core request
    
    EXAMPLES:
    - Query: "fix it" + History: "My iPhone screen is cracked" → "fix my cracked iPhone screen"
    - Query: "what should I do about that" + History: "The AC is not cooling down" → "what should I do about the AC not cooling down"
    - Query: "help me with the phone" + History: "My Samsung phone won't turn on" → "help me with my Samsung phone that won't turn on"
    - Query: "how to repair this" + History: "The laptop battery dies quickly" → "how to repair the laptop battery that dies quickly"
    
    IMPORTANT RULES:
    - Only resolve ambiguity, don't change the user's intent
    - Use information from conversation history to fill in missing details
    - Keep the original query structure and tone
    - If no relevant context is found, return the original query unchanged
    - Don't add information that wasn't mentioned in the conversation
    
    Return ONLY the resolved query - no explanations or additional text.
    """)
    
    try:
        # Format conversation history for the prompt
        history_text = _format_conversation_history(conversation_history)
        
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=resolution_prompt.format(
            query=query,
            conversation_history=history_text
        ))])
        resolved_query = response.content.strip()
        
        # Fallback if resolution fails
        if not resolved_query or len(resolved_query) < 3:
            resolved_query = query
        
        return resolved_query
        
    except Exception as e:
        print(f"DEBUG: Error resolving ambiguity: {e}")
        # Fallback to original query
        return query


# =============================================================================
# DECISION NODE
# =============================================================================

def decision_node(state: AgentState) -> Dict[str, Any]:
    """
    Decides if the user query can be explained by conversation or if the problem identification node should be used.
    Returns "conversation" for conversational queries or "problem_identification" for repair/technical queries.
    Uses the disambiguated query for better decision making.
    """
    query = state.get("disambiguated_query", state["query"])  # Use disambiguated query if available
    
    # Create LLM instance
    llm = ChatOllama(
        model="qwen2.5vl:7b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )
    
    # Always use text-only decision making (ignore images)
    decision = _make_decision_text_only(query, llm)
    
    return {"decision_result": decision}


def _make_decision_text_only(query: str, llm: ChatOllama) -> str:
    """
    Make decision based on text input only (fallback method)
    """
    base_prompt = f"""
    Analyze this user query to decide if this needs a conversational response or technical repair guidance.
    
    User Query: {query}
    
    DECISION CRITERIA:
    Choose "conversation" if the query is:
    - General questions about what happened or what's wrong (without asking for fix)
    - Questions about warranty, cost, or general information
    - Asking for explanations or information
    - Casual conversation or chit-chat
    - Questions about features, specifications, or general knowledge
    - "What do you think...", "What happened to...", "How much warranty...", "What is...", "How does...", "Tell me about...", "Explain..."
    
    Choose "problem_identification" if the query is:
    - Explicitly asking for help to fix or repair something
    - Urging the need for a fix or solution
    - Asking for step-by-step repair instructions
    - "Help me fix...", "How to fix...", "How to repair...", "What should I do to fix...", "Can you help me fix..."
    
    EXAMPLES:
    - "What do you think happened to my phone?" → conversation
    - "How much warranty can I get on this phone?" → conversation
    - "What is a smartphone?" → conversation
    - "Help me fix my cracked screen" → problem_identification
    - "How to fix a broken screen" → problem_identification
    - "My phone screen is cracked, what should I do to fix it?" → problem_identification
    - "What do you think is wrong with my phone?" → conversation
    """
    
    try:
        # Create prompt with JSON schema
        prompt_with_schema = create_llm_prompt_with_schema(base_prompt, ResponseType.DECISION)
        
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=prompt_with_schema)])
        
        # Parse JSON response
        parsed_response = parse_llm_json_response(response.content, ResponseType.DECISION)
        decision = parsed_response.get("decision", "problem_identification")
        
        # Validate decision
        if decision not in ["conversation", "problem_identification"]:
            decision = "problem_identification"  # Default fallback
        
    except Exception as e:
        print(f"Error in decision making: {e}")
        # Fallback to problem_identification for safety
        decision = "problem_identification"
    
    return decision


# =============================================================================
# CONVERSATION NODE
# =============================================================================

def conversation_node(state: AgentState) -> Dict[str, Any]:
    """
    Processes the user query and image conversationally, providing helpful responses
    without going through the technical repair workflow.
    """
    query = state.get("disambiguated_query", state["query"])  # Use disambiguated query if available
    image_data = state.get("image_data")
    conversation_history = state.get("conversation_history", [])
    
    # Create LLM instance
    llm = ChatOllama(
        model="qwen2.5vl:7b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.7  # Higher temperature for more conversational responses
    )
    
    # Check if we have valid image data
    has_image = image_data and image_data != "base64_image_data_here" and len(image_data) > 50
    
    # Debug: Print image status
    print(f"DEBUG: Conversation node - has_image: {has_image}")
    if image_data:
        print(f"DEBUG: Conversation node - image_data length: {len(image_data)}")
        print(f"DEBUG: Conversation node - image_data preview: {image_data[:50]}...")
    
    if has_image:
        # Conversational prompt with image analysis and conversation history
        base_prompt = f"""
        You are a helpful and friendly assistant. The user has asked a question and provided an image.
        Provide a conversational, informative response that addresses their question.
        
        Previous Conversation History:
        {_format_conversation_history(conversation_history)}
        
        Current User Question: {query}
        Image: [Image data provided]
        
        INSTRUCTIONS:
        1. Consider the conversation history to understand context and remember previous discussions
        2. Analyze the image to understand what the user is asking about
        3. If they're asking "what happened" or "what's wrong", describe what you see in the image
        4. If they're asking about warranty, cost, or general info, provide helpful information
        5. Be informative but not overly technical
        6. If you see damage or issues in the image, describe them clearly
        7. Offer helpful information or suggestions
        8. Keep the tone friendly and approachable
        9. Reference previous conversation when relevant (e.g., "As we discussed earlier...", "Remember when you mentioned...")
        10. DO NOT provide step-by-step repair instructions - just describe what you see and offer general advice
        
        EXAMPLES:
        - "What do you think happened to my phone?" + cracked screen image → "I can see your phone screen is cracked. This typically happens from drops or impacts..."
        - "How much warranty can I get?" + damaged device → "Based on what I can see, here's some general warranty information..."
        
        Respond naturally as if you're having a conversation with a friend, remembering what you've discussed before.
        """
        
        try:
            # Create prompt with JSON schema
            prompt_with_schema = create_llm_prompt_with_schema(base_prompt, ResponseType.CONVERSATION)
            
            # Create message with both text and image
            from langchain_core.messages import HumanMessage
            
            message_content = [
                {"type": "text", "text": prompt_with_schema},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
            response = llm.invoke([HumanMessage(content=message_content)])
            
            # Parse JSON response
            parsed_response = parse_llm_json_response(response.content, ResponseType.CONVERSATION)
            conversation_response = parsed_response.get("response", "I'd be happy to help with your question.")
            
        except Exception as e:
            print(f"Image analysis failed in conversation node, falling back to text-only: {e}")
            # Fallback to text-only conversation
            conversation_response = _generate_conversation_text_only(query, conversation_history, llm)
    else:
        # Text-only conversation
        conversation_response = _generate_conversation_text_only(query, conversation_history, llm)
    
    # Note: No need to clear query file for conversation responses
    # User-specific queries are managed by LocalUserStorage in the API
    print("DEBUG: Conversation response - no query file clearing needed")
    
    return {
        "conversation_response": conversation_response,
        "response_source": "conversation",
        "local_repair_available": False  # No local repair available for conversation responses
    }


def _generate_conversation_text_only(query: str, conversation_history: List[Dict[str, Any]], llm: ChatOllama) -> str:
    """
    Generate conversational response based on text input only (fallback method)
    """
    base_prompt = f"""
    You are a helpful and friendly assistant. The user has asked a question.
    Provide a conversational, informative response that addresses their question.
    
    Previous Conversation History:
    {_format_conversation_history(conversation_history)}
    
    Current User Question: {query}
    
    INSTRUCTIONS:
    1. Consider the conversation history to understand context and remember previous discussions
    2. Provide a helpful, conversational response
    3. Be informative but not overly technical
    4. Offer helpful information or suggestions when appropriate
    5. Keep the tone friendly and approachable
    6. If it's a general knowledge question, provide useful information
    7. If it's asking for advice, give thoughtful suggestions
    8. Reference previous conversation when relevant (e.g., "As we discussed earlier...", "Remember when you mentioned...")
    
    Respond naturally as if you're having a conversation with a friend, remembering what you've discussed before.
    """
    
    try:
        # Create prompt with JSON schema
        prompt_with_schema = create_llm_prompt_with_schema(base_prompt, ResponseType.CONVERSATION)
        
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=prompt_with_schema)])
        
        # Parse JSON response
        parsed_response = parse_llm_json_response(response.content, ResponseType.CONVERSATION)
        conversation_response = parsed_response.get("response", "")
        
        # Fallback if LLM fails
        if not conversation_response or len(conversation_response) < 10:
            conversation_response = f"I'd be happy to help with your question: '{query}'. Could you provide more details about what you'd like to know?"
        
    except Exception as e:
        print(f"Error in conversation generation: {e}")
        # Fallback response
        conversation_response = f"I'd be happy to help with your question: '{query}'. Could you provide more details about what you'd like to know?"
    
    return conversation_response


def _format_conversation_history(conversation_history: List[Dict[str, Any]]) -> str:
    """
    Format conversation history for inclusion in prompts
    """
    if not conversation_history:
        return "No previous conversation history."
    
    formatted_history = []
    for msg in conversation_history[-10:]:  # Only include last 10 messages to avoid token limits
        role = msg.get('role', 'unknown')
        message = msg.get('message', '')
        timestamp = msg.get('timestamp', 0)
        
        if role == 'user':
            formatted_history.append(f"User: {message}")
        elif role == 'assistant':
            formatted_history.append(f"Assistant: {message}")
    
    if not formatted_history:
        return "No previous conversation history."
    
    return "\n".join(formatted_history)


# =============================================================================
# PROBLEM IDENTIFICATION NODE
# =============================================================================

def problem_identification_node(state: AgentState) -> AgentState:
    """
    Extracts the core problem from messy user input and creates a clean search query.
    If image data is provided, it will be analyzed along with the text input.
    """
    query = state.get("disambiguated_query", state["query"])  # Use disambiguated query if available
    image_data = state.get("image_data")  # Get image data if provided
    
    # Create LLM instance
    llm = ChatOllama(
        model="qwen2.5vl:7b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )
    
    # Check if we have valid image data
    has_image = image_data and image_data != "base64_image_data_here" and len(image_data) > 50
    
    if has_image:
        # LLM-based problem extraction with image analysis
        base_prompt = f"""
        Analyze this repair request with the provided image and create a simple, searchable query.
        
        User Input: {query}
        Image: [Image data provided]
        
        Your task:
        1. Analyze the image to identify the device and visible problems
        2. Combine image analysis with the user's text description
        3. Create a simple, direct search query that websites like WikiHow, iFixit, and Medium can find results for
        
        Examples:
        - Image shows cracked phone screen + "My phone is flickering" → "how to fix cracked phone screen"
        - Image shows laptop + "It won't turn on" → "how to fix laptop won't turn on"
        - Image shows device + "Battery issues" → "how to fix device battery"
        """
        
        try:
            # Create prompt with JSON schema
            prompt_with_schema = create_llm_prompt_with_schema(base_prompt, ResponseType.PROBLEM_EXTRACTION)
            
            # Create message with both text and image
            from langchain_core.messages import HumanMessage
            message_content = [
                {"type": "text", "text": prompt_with_schema},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
            response = llm.invoke([HumanMessage(content=message_content)])
            
            # Parse JSON response
            parsed_response = parse_llm_json_response(response.content, ResponseType.PROBLEM_EXTRACTION)
            clean_query = parsed_response.get("clean_query", query)
            
        except Exception as e:
            print(f"Image analysis failed, falling back to text-only: {e}")
            # Fallback to text-only analysis
            clean_query = _extract_query_from_text_only(query, llm)
    else:
        # Text-only analysis (original logic)
        clean_query = _extract_query_from_text_only(query, llm)
    
    # Create a new state dict to avoid mutation issues
    new_state = state.copy()
    new_state["problem_statement"] = clean_query
    
    return new_state


def _extract_query_from_text_only(query: str, llm: ChatOllama) -> str:
    """
    Extract search query from text input only (fallback method)
    """
    base_prompt = f"""
    Extract the core problem from this user input and create a simple, searchable query.
    
    User Input: {query}
    
    Your task:
    1. Identify the main problem or issue the user is facing
    2. Remove irrelevant details, backstory, and emotional context
    3. Create a simple, direct search query that websites like WikiHow, iFixit, and Medium can find results for
    
    Examples:
    - "My phone is flickering a lot, I've been trying to fix it, but my dog spilled coffee on it and now it won't start" → "how to fix flickering phone"
    - "I'm so frustrated! My laptop keeps overheating and shutting down randomly, I think it's because I dropped it last week" → "how to fix laptop overheating"
    - "My car won't start in the morning, it makes weird noises, I think the battery is dead but I'm not sure" → "how to fix car won't start"
    """
    
    try:
        # Create prompt with JSON schema
        prompt_with_schema = create_llm_prompt_with_schema(base_prompt, ResponseType.PROBLEM_EXTRACTION)
        
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=prompt_with_schema)])
        
        # Parse JSON response
        parsed_response = parse_llm_json_response(response.content, ResponseType.PROBLEM_EXTRACTION)
        clean_query = parsed_response.get("clean_query", query)
        
        # Fallback if LLM fails
        if not clean_query or len(clean_query) < 3:
            clean_query = query
        
    except Exception as e:
        print(f"Error in problem extraction: {e}")
        # Fallback to original query
        clean_query = query
    
    return clean_query


# =============================================================================
# SPECIALIZED AGENTS - FIX: Return only the specific key each node should update
# =============================================================================

def wikihow_node(state: AgentState) -> Dict[str, Any]:
    """
    Searches WikiHow and returns results in correct format to next agent
    """
    query = state["problem_statement"]
    
    try:
        # Use the working WikiHow search module
        articles = search_wikihow_advanced(query, max_articles=3)
        
        if articles and len(articles) > 0:
            # Extract content from the first article
            article = articles[0]
            content = article['content'][0]['content'] if article['content'] else "No content available"
            url = article.get('link', 'https://wikihow.com')
            
            result = AgentResult(
                content=content,
                source_urls=[url],
                metadata={
                    "source": "WikiHow",
                    "search_type": "how_to_guide",
                    "title": article.get('title', 'Unknown'),
                    "date": article.get('date', 'Unknown'),
                    "views": article.get('views', 'Unknown')
                },
                success=True
            )
        else:
            # Fallback if no results
            result = AgentResult(
                content=f"No WikiHow results found for: {query}",
                source_urls=["https://wikihow.com"],
                metadata={"source": "WikiHow", "search_type": "how_to_guide", "results_count": 0},
                success=False
            )
        
    except Exception as e:
        result = AgentResult(
            content=f"Error searching WikiHow for: {query}",
            source_urls=["https://wikihow.com"],
            metadata={"source": "WikiHow", "error": str(e)},
            success=False
        )
    
    # Return only the key this node should update
    return {"wikihow_results": result.model_dump()}


def ifixit_node(state: AgentState) -> Dict[str, Any]:
    """
    Searches iFixit website using LangChain document loader and returns results in correct format
    """
    query = state["problem_statement"]
    
    try:
        # Use the working iFixit search module
        guides = search_ifixit_advanced(query, max_guides=3)
        
        if guides and len(guides) > 0:
            # Extract content from the first guide
            guide = guides[0]
            content = guide['content'][0]['content'] if guide['content'] else "No content available"
            url = guide.get('url', 'https://ifixit.com')
            
            result = AgentResult(
                content=content,
                source_urls=[url],
                metadata={
                    "source": "iFixit",
                    "search_type": "repair_guide",
                    "title": guide.get('title', 'Unknown'),
                    "device": guide.get('device', 'Unknown'),
                    "langchain_loader": True
                },
                success=True
            )
        else:
            # Fallback if no results
            result = AgentResult(
                content=f"No iFixit guides found for: {query}",
                source_urls=["https://ifixit.com"],
                metadata={"source": "iFixit", "search_type": "repair_guide", "guides_found": 0},
                success=False
            )
        
    except Exception as e:
        result = AgentResult(
            content=f"Error searching iFixit for: {query}",
            source_urls=["https://ifixit.com"],
            metadata={"source": "iFixit", "error": str(e)},
            success=False
        )
    
    # Return only the key this node should update
    return {"ifixit_results": result.model_dump()}


def medium_node(state: AgentState) -> Dict[str, Any]:
    """
    Searches Medium articles using Google PSE and returns results in correct format
    """
    query = state["problem_statement"]
    
    try:
        # Use the working Medium search module
        articles = search_medium_advanced(query, max_articles=3)
        
        if articles and len(articles) > 0:
            # Extract content from the first article
            article = articles[0]
            content = article['content'][0]['content'] if article['content'] else "No content available"
            url = article.get('url', 'https://medium.com')
            
            result = AgentResult(
                content=content,
                source_urls=[url],
                metadata={
                    "source": "Medium",
                    "search_type": "article",
                    "title": article.get('title', 'Unknown'),
                    "author": article.get('author', 'Unknown'),
                    "google_pse": True
                },
                success=True
            )
        else:
            # Fallback if no results
            result = AgentResult(
                content=f"No Medium articles found for: {query}",
                source_urls=["https://medium.com"],
                metadata={"source": "Medium", "search_type": "article", "articles_found": 0},
                success=False
            )
        
    except Exception as e:
        result = AgentResult(
            content=f"Error searching Medium for: {query}",
            source_urls=["https://medium.com"],
            metadata={"source": "Medium", "error": str(e)},
            success=False
        )
    
    # Return only the key this node should update
    return {"medium_results": result.model_dump()}


def tavily_node(state: AgentState) -> Dict[str, Any]:
    """
    Searches multiple sources using Tavily and returns results in correct format
    """
    query = state["problem_statement"]
    
    try:
        # Use the working Tavily search module
        articles = search_tavily(query, max_results=6)
        
        if articles and len(articles) > 0:
            # Extract content from the first article
            article = articles[0]
            content = article['content'][0]['content'] if article['content'] else "No content available"
            url = article.get('url', 'https://tavily.com')
            
            result = AgentResult(
                content=content,
                source_urls=[url],
                metadata={
                    "source": "Tavily",
                    "search_type": "multi_source_search",
                    "title": article.get('title', 'Unknown'),
                    "sources_searched": 6,
                    "tavily_api": True
                },
                success=True
            )
        else:
            # Fallback if no results
            result = AgentResult(
                content=f"No Tavily results found for: {query}",
                source_urls=["https://tavily.com"],
                metadata={"source": "Tavily", "search_type": "multi_source_search", "results_found": 0},
                success=False
            )
        
    except Exception as e:
        result = AgentResult(
            content=f"Error searching Tavily for: {query}",
            source_urls=["https://tavily.com"],
            metadata={"source": "Tavily", "error": str(e)},
            success=False
        )
    
    # Return only the key this node should update
    return {"tavily_results": result.model_dump()}


# =============================================================================
# AGGREGATOR/SUMMARIZER AGENT
# =============================================================================

def aggregator_agent(state: AgentState) -> Dict[str, Any]:
    """
    Combines results from multiple sources into coherent instructions
    """
    query = state["query"]
    problem_statement = state["problem_statement"]
    
    # Collect all available results and extract URLs (excluding Google Maps from sources)
    all_results = []
    all_sources = []
    local_repair_info = None
    
    for result_key in ["wikihow_results", "ifixit_results", "medium_results", "tavily_results"]:
        if result_key in state and state[result_key]:
            result_data = state[result_key]
            if result_data.get("success"):
                all_results.append(result_data)
                # Extract URLs from the source_urls field
                source_urls = result_data.get("source_urls", [])
                all_sources.extend(source_urls)
    
    # Local repair is now handled separately via LocalRepairTool
    
    # Create LLM instance for aggregation
    llm = ChatOllama(
        model="qwen2.5vl:7b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )
    
    try:
        # Prepare results summary for LLM with clear source identification
        results_summary = ""
        for i, result in enumerate(all_results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            source_name = metadata.get("source", f"Source {i}")
            success = result.get("success", False)
            source_urls = result.get("source_urls", [])
            
            results_summary += f"=== {source_name.upper()} (Source {i}) ===\n"
            results_summary += f"Success: {'✅ YES' if success else '❌ NO'}\n"
            results_summary += f"Content: {content}\n"
            if source_urls:
                results_summary += f"Source URLs: {', '.join(source_urls)}\n"
            if metadata:
                results_summary += f"Additional Info: {metadata}\n"
            results_summary += "\n"
        
        # Debug: Print available sources
        print(f"DEBUG: Available sources: {all_sources}")
        
        # LLM-based aggregation prompt with results summary
        base_prompt = f"""
        You are an expert repair technician analyzing information from multiple sources to create the best possible solution.
        
        Original Query: {query}
        Problem Statement: {problem_statement}
        
        Available Information from Multiple Sources:
        {results_summary}
        
        CRITICAL EVALUATION TASK:
        First, evaluate each source for usefulness:
        1. Rate each source (1-10) for relevance and quality of information
        2. Identify which source provides the most practical, actionable steps
        3. Note any sources that are too generic, irrelevant, or unhelpful
        4. Prioritize sources with specific, detailed instructions over vague ones
        
        SOURCE EVALUATION CRITERIA:
        - Specificity: Does it address the exact problem mentioned?
        - Actionability: Are the steps clear and doable?
        - Completeness: Does it cover tools, materials, safety, and time estimates?
        - Accuracy: Does the information seem technically sound?
        - Practicality: Is it realistic for a DIY repair?
        
        INSTRUCTIONS:
        Based on your evaluation, create a solution that:
        1. Uses the BEST information from the most useful sources
        2. IGNORES or minimally uses information from poor sources
        3. Combines the strongest elements from multiple good sources
        
        Create a title that describes the specific problem being fixed and provide numbered steps for the repair process.
        Include required tools and materials. List all source URLs that provided useful information.
        """
        
        # Create prompt with JSON schema
        prompt_with_schema = create_llm_prompt_with_schema(base_prompt, ResponseType.AGGREGATION)
        
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=prompt_with_schema)])
        
        # Parse JSON response
        parsed_response = parse_llm_json_response(response.content, ResponseType.AGGREGATION)
        
        # Convert JSON to text and add sources
        instructions = convert_json_to_text(parsed_response, ResponseType.AGGREGATION)
        
        # Always ensure ALL sources are included
        if all_sources:
            # Remove any existing Sources section and replace with complete list
            import re
            # Remove existing sources section if it exists
            instructions = re.sub(r'\n\nSources:.*$', '', instructions, flags=re.DOTALL)
            
            # Add complete sources section
            sources_section = "\n\nSources:\n"
            for i, source in enumerate(all_sources, 1):
                sources_section += f"{i}. {source}\n"
            instructions += sources_section
        
    except Exception as e:
        print(f"Error in aggregation: {e}")
        # Fallback instructions
        instructions = f"Unable to process query: {query}. Please try again."
        
        if all_sources:
            sources_section = "\n\nSources:\n"
            for i, source in enumerate(all_sources, 1):
                sources_section += f"{i}. {source}\n"
            instructions += sources_section
    
    # Return only the clean instructions
    return {"final_response": instructions}


# =============================================================================
# EXAMINE NODE - FIX: Check if results actually answer the user's question
# =============================================================================

def examine_node(state: AgentState) -> Dict[str, Any]:
    """
    Checks if the aggregated results actually answer the user's question.
    If not, provides a direct answer based on reasoning.
    """
    query = state["query"]
    problem_statement = state["problem_statement"]
    current_response = state.get("final_response", "")
    
    # Collect all available sources from the state (excluding Google Maps)
    all_sources = []
    local_repair_info = None
    
    for result_key in ["wikihow_results", "ifixit_results", "medium_results", "tavily_results"]:
        if result_key in state and state[result_key]:
            result_data = state[result_key]
            if result_data.get("success"):
                source_urls = result_data.get("source_urls", [])
                all_sources.extend(source_urls)
    
    # Local repair is now handled separately via LocalRepairTool
    
    # Create LLM instance
    llm = ChatOllama(
        model="qwen2.5vl:7b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )
    
    # LLM-based examination and validation
    examine_prompt = ChatPromptTemplate.from_template("""
    You are an expert repair technician. Your job is to decide if the provided solution should be kept or replaced.
    
    Original User Question: {query}
    Extracted Problem: {problem_statement}
    Current Solution: {current_response}
    
    CRITICAL INSTRUCTION: You should ALMOST ALWAYS keep the current solution. Only replace it in extreme cases.
    
    REPLACE ONLY IF:
    - The solution is about something completely different (like if user asks about fixing a phone but solution is about cooking pasta)
    - The solution is completely nonsensical or gibberish
    - The solution is about a completely different device/problem than what was asked
    
    KEEP THE CURRENT SOLUTION IF:
    - It addresses the same general type of problem (even if not perfect)
    - It has reasonable steps and tools
    - It's about the same category of device/repair
    - It's helpful in any way to the user's problem
    
    EXAMPLES:
    - User asks about phone screen repair, solution is about phone screen repair → KEEP_CURRENT
    - User asks about phone screen repair, solution is about laptop overheating → KEEP_CURRENT (both are tech repairs)
    - User asks about phone screen repair, solution is about cooking recipes → REPLACE_WITH_REASONING
    - User asks about phone screen repair, solution is about car engine repair → KEEP_CURRENT (both are repairs)
    
    BE EXTREMELY CONSERVATIVE. When in doubt, KEEP_CURRENT.
    
    Return ONLY "KEEP_CURRENT" or "REPLACE_WITH_REASONING" - no additional text.
    """)
    
    try:
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=examine_prompt.format(
            query=query,
            problem_statement=problem_statement,
            current_response=current_response
        ))])
        examine_result = response.content.strip()
        
        # Check if we should keep current or replace
        if examine_result.strip().upper() == "KEEP_CURRENT":
            # Keep the current response
            final_response = current_response
        else:
            # Use the examine-based response
            final_response = examine_result
        
        # Always ensure ALL actual sources are included (overwrite any hallucinated sources)
        if all_sources:
            import re
            # Remove any existing sources section if it exists
            final_response = re.sub(r'\n\nSources:.*$', '', final_response, flags=re.DOTALL)
            
            # Add actual sources section
            sources_section = "\n\nSources:\n"
            for i, source in enumerate(all_sources, 1):
                sources_section += f"{i}. {source}\n"
            final_response += sources_section
        
    except Exception as e:
        # Fallback to current response
        final_response = current_response
        
        # Ensure sources are included even in fallback
        if all_sources:
            import re
            final_response = re.sub(r'\n\nSources:.*$', '', final_response, flags=re.DOTALL)
            sources_section = "\n\nSources:\n"
            for i, source in enumerate(all_sources, 1):
                sources_section += f"{i}. {source}\n"
            final_response += sources_section
    
    # Note: Query saving is now handled by LocalUserStorage in the API
    # No need to save query here as it's already saved when the user sends the message
    print("DEBUG: Repair response - query already saved via LocalUserStorage in API")
    
    # Generate title and extract item name using LLM
    print(f"DEBUG: About to extract item name for query: {query}")
    item_name = _extract_item_name(query)
    print(f"DEBUG: Extracted item name: {item_name}")
    
    print(f"DEBUG: About to generate post title for query: {query}")
    post_title = _generate_post_title(query, final_response)
    print(f"DEBUG: Generated post title: {post_title}")
    
    # Save LLM-generated data to JSON file for frontend to access
    try:
        import json
        import os
        from datetime import datetime
        
        post_data = {
            "query": query,
            "item_name": item_name,
            "post_title": post_title,
            "final_response": final_response,
            "timestamp": datetime.now().isoformat(),
            "user_id": None  # Can be populated if user_id is available
        }
        
        # Save to JSON file
        json_file_path = os.path.join(os.path.dirname(__file__), "post_data.json")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, indent=2, ensure_ascii=False)
        
        print(f"DEBUG: Saved post data to {json_file_path}")
        print(f"DEBUG: Post data: {post_data}")
        
    except Exception as e:
        print(f"DEBUG: Failed to save post data to JSON file: {e}")
    
    # Return the final response with metadata for frontend
    return {
        "final_response": final_response,
        "response_source": "problem_identification",
        "local_repair_available": True,  # Changed from local_repair_links to local_repair_available
        "item_name": item_name,
        "post_title": post_title
    }


# =============================================================================
# GRAPH CONSTRUCTION - FIX: Use conditional routing to handle parallel execution properly
# =============================================================================

def create_multiagent_graph():
    """
    Creates and returns the LangGraph workflow with disambiguation, decision routing and parallel execution
    """
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("disambiguation", disambiguation_node)
    workflow.add_node("decision", decision_node)
    workflow.add_node("conversation", conversation_node)
    workflow.add_node("problem_identification", problem_identification_node)
    workflow.add_node("wikihow", wikihow_node)
    workflow.add_node("ifixit", ifixit_node)
    workflow.add_node("medium", medium_node)
    workflow.add_node("tavily", tavily_node)
    workflow.add_node("aggregator", aggregator_agent)
    workflow.add_node("examine", examine_node)
    
    # Set entry point to disambiguation node
    workflow.set_entry_point("disambiguation")
    
    # Disambiguation always goes to decision
    workflow.add_edge("disambiguation", "decision")
    
    # Decision routing: decision -> conversation OR problem_identification
    workflow.add_conditional_edges(
        "decision",
        lambda state: state["decision_result"],
        {
            "conversation": "conversation",
            "problem_identification": "problem_identification"
        }
    )
    
    # Conversation node routes directly to end
    workflow.add_edge("conversation", END)
    
    # Sequential to parallel: problem_identification -> all 4 agents
    workflow.add_edge("problem_identification", "wikihow")
    workflow.add_edge("problem_identification", "ifixit") 
    workflow.add_edge("problem_identification", "medium")
    workflow.add_edge("problem_identification", "tavily")
    
    # Parallel to aggregator: all agents -> aggregator
    workflow.add_edge("wikihow", "aggregator")
    workflow.add_edge("ifixit", "aggregator")
    workflow.add_edge("medium", "aggregator")
    workflow.add_edge("tavily", "aggregator")
    
    # Aggregator to examine: aggregator -> examine
    workflow.add_edge("aggregator", "examine")
    
    # Examine routes to end
    workflow.add_edge("examine", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


def generate_workflow_diagram():
    """
    Generate a Mermaid diagram of the workflow for visualization
    """
    workflow = create_multiagent_graph()
    mermaid_code = workflow.get_graph().draw_mermaid()
    return mermaid_code


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

def run_multiagent_system(query: str, image_data: Optional[str] = None, conversation_history: Optional[List[Dict[str, Any]]] = None):
    """
    Example of how to run the multiagent system
    """
    # Create the graph
    app = create_multiagent_graph()
    
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "disambiguated_query": "",  # Will be filled by disambiguation node
        "image_data": image_data,
        "conversation_history": conversation_history or [],
        "decision_result": "",
        "conversation_response": "",
        "problem_statement": "",
        "wikihow_results": {},
        "ifixit_results": {},
        "medium_results": {},
        "tavily_results": {},
        "final_response": "",
        "response_source": "",  # Will be set by conversation or examine node
        "local_repair_available": False  # Will be set based on response source
    }
    
    # Run the workflow
    result = app.invoke(initial_state)
    
    return result


def _extract_item_name(user_input: str) -> str:
    """Extract item name from user input using LLM"""
    try:
        print(f"DEBUG: Starting item name extraction for: {user_input}")
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        # Use the same LLM setup as the main system
        llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url="http://100.94.111.126:11434",
            temperature=0.3
        )
        
        prompt = f"""Extract the main item/device name from this repair request.

User input: "{user_input}"

Return ONLY the item name (e.g., "iPhone", "laptop", "chair", "bicycle", "TV").
Do not include model numbers or additional details.
If unclear, return "device".

Item name:"""

        print(f"DEBUG: Calling LLM for item name extraction")
        response = llm.invoke([HumanMessage(content=prompt)])
        print(f"DEBUG: LLM response for item name: '{response.content}'")
        
        result = response.content.strip() if response.content.strip() else "device"
        print(f"DEBUG: Final item name: '{result}'")
        return result
    except Exception as e:
        print(f"ERROR extracting item name: {e}")
        import traceback
        traceback.print_exc()
        return "device"

def _generate_post_title(user_input: str, guidance: str) -> str:
    """Generate a short, engaging title for social media post using LLM"""
    try:
        print(f"DEBUG: Starting title generation for: {user_input}")
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        # Use the same LLM setup as the main system
        llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url="http://100.94.111.126:11434",
            temperature=0.3
        )
        
        prompt = f"""Create a very short social media post title for a repair success story.

User input: "{user_input}"

Repair guidance: "{guidance[:200]}..."

REQUIREMENTS:
- EXACTLY 3-4 words only
- No quotes, no punctuation
- Positive and encouraging
- Mention what was fixed

GOOD EXAMPLES:
Fixed iPhone Screen
Chair Fixed
Laptop Working
Bike Repaired
TV Fixed
Watch Working

BAD EXAMPLES (too long):
How I Fixed My Broken iPhone Screen
Successfully Repaired My Laptop Computer
My Washing Machine is Now Working Perfectly

Respond with ONLY the title, no quotes, no extra text:"""

        print(f"DEBUG: Calling LLM for title generation")
        response = llm.invoke([HumanMessage(content=prompt)])
        print(f"DEBUG: LLM response for title: '{response.content}'")
        
        title = response.content.strip() if response.content.strip() else "Repair Success!"
        
        # Remove extra quotes if present
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1]
        elif title.startswith("'") and title.endswith("'"):
            title = title[1:-1]
        
        # Remove any trailing punctuation except exclamation marks
        title = title.rstrip('.,;:')
        
        # Ensure title is 3-4 words maximum
        words = title.split()
        if len(words) > 4:
            title = ' '.join(words[:4])
        elif len(words) < 2:
            # If too short, use a default
            title = "Repair Success"
        
        # Final validation - ensure it's not too long
        if len(title) > 50:
            title = "Repair Success"
        
        print(f"DEBUG: Final title: '{title}' (length: {len(title)}, words: {len(title.split())})")
        return title
    except Exception as e:
        print(f"ERROR generating post title: {e}")
        import traceback
        traceback.print_exc()
        return "Repair Success!"


if __name__ == "__main__":
    import time
    import base64
    from pathlib import Path
    
    # Generate and display workflow diagram
    print("🔄 Generating workflow diagram...")
    mermaid_code = generate_workflow_diagram()
    print("\n📊 WORKFLOW DIAGRAM (Mermaid):")
    print("=" * 50)
    print(mermaid_code)
    print("=" * 50)
    
    # Test with a simple query
    #test_query = "I'm so scared, my iPhone dropped from my hand and its screen broke what do I do. My mom will be pissed at me"#"How to fix a leaky faucet"
    #test_query = "What do you think is wrong with my phone?"
    #test_query = "How much warranty can i get on this phone?"
    test_query = "Help me fix my cracked phone"

    # Try to load a test image if available
    test_image_data = None
    test_image_path = Path(__file__).parent / "testimgs" / "iphone_cracked.jpg"
    
    if test_image_path.exists():
        print(f"📸 Loading test image: {test_image_path}")
        try:
            with open(test_image_path, "rb") as image_file:
                test_image_data = base64.b64encode(image_file.read()).decode('utf-8')
            print(f"✅ Image loaded and encoded ({len(test_image_data)} characters)")
        except Exception as e:
            print(f"❌ Failed to load image: {e}")
    
    try:
        # Start timing
        start_time = time.time()
        
        # Run the multi-agent system with optional image data
        result = run_multiagent_system(test_query, test_image_data)
        
        # End timing
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Show the appropriate response based on the response_source
        response_source = result.get("response_source", "")
        local_repair_available = result.get("local_repair_available", False)
        
        if response_source == "conversation":
            if result.get("conversation_response"):
                print("=== CONVERSATION RESPONSE ===")
                print(result["conversation_response"])
                print("=== NO LOCAL REPAIR BUTTON (conversation response) ===")
            else:
                print("No conversation response generated")
        else:
            # ANY response that's NOT from conversation should show the button
            if result.get("final_response"):
                print("=== NON-CONVERSATION RESPONSE ===")
                print(result["final_response"])
                print(f"=== LOCAL REPAIR BUTTON SHOULD SHOW (available: {local_repair_available}) ===")
                if local_repair_available:
                    print("Query saved to JSON file for LocalRepairTool")
                else:
                    print("No query saved (local repair not available)")
            else:
                print("No repair response generated")
        
        # Show timing
        print(f"\n⏱️ Total time: {elapsed_time:.2f} seconds")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'elapsed_time' in locals():
            print(f"⏱️ Time before error: {elapsed_time:.2f} seconds")