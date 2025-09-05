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

# Import working search modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

try:
    from test_ifixit_api import search_ifixit_advanced
    from test_medium import search_medium_advanced  
    from test_wikihow import search_wikihow_advanced
    from test_tavilysearch import search_tavily
    from test_googlemaps import search_repair_shops_advanced
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
    googlemaps_results: Dict[str, Any]
    local_repair_results: Dict[str, Any]  # Separate local repair information
    final_response: str
    response_source: str  # "conversation" or "problem_identification" - tells frontend where response came from
    local_repair_links: List[str]  # Google Maps URLs for frontend to display in button


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
    decision_prompt = ChatPromptTemplate.from_template("""
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
    
    Return ONLY "conversation" or "problem_identification" - no additional text.
    """)
    
    try:
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=decision_prompt.format(query=query))])
        decision = response.content.strip().lower()
        
        # Validate decision
        if decision not in ["conversation", "problem_identification"]:
            decision = "problem_identification"  # Default fallback
        
    except Exception as e:
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
        conversation_prompt = ChatPromptTemplate.from_template("""
        You are a helpful and friendly assistant. The user has asked a question and provided an image.
        Provide a conversational, informative response that addresses their question.
        
        Previous Conversation History:
        {conversation_history}
        
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
        """)
        
        try:
            # Create message with both text and image
            from langchain_core.messages import HumanMessage
            # Format conversation history for the prompt
            history_text = _format_conversation_history(conversation_history)
            
            message_content = [
                {"type": "text", "text": conversation_prompt.format(query=query, conversation_history=history_text)},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
            response = llm.invoke([HumanMessage(content=message_content)])
            conversation_response = response.content.strip()
            
        except Exception as e:
            print(f"Image analysis failed in conversation node, falling back to text-only: {e}")
            # Fallback to text-only conversation
            conversation_response = _generate_conversation_text_only(query, conversation_history, llm)
    else:
        # Text-only conversation
        conversation_response = _generate_conversation_text_only(query, conversation_history, llm)
    
    return {
        "conversation_response": conversation_response,
        "response_source": "conversation",
        "local_repair_links": []  # No local repair links for conversation responses
    }


def _generate_conversation_text_only(query: str, conversation_history: List[Dict[str, Any]], llm: ChatOllama) -> str:
    """
    Generate conversational response based on text input only (fallback method)
    """
    conversation_prompt = ChatPromptTemplate.from_template("""
    You are a helpful and friendly assistant. The user has asked a question.
    Provide a conversational, informative response that addresses their question.
    
    Previous Conversation History:
    {conversation_history}
    
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
    """)
    
    try:
        # Format conversation history for the prompt
        history_text = _format_conversation_history(conversation_history)
        
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=conversation_prompt.format(query=query, conversation_history=history_text))])
        conversation_response = response.content.strip()
        
        # Fallback if LLM fails
        if not conversation_response or len(conversation_response) < 10:
            conversation_response = f"I'd be happy to help with your question: '{query}'. Could you provide more details about what you'd like to know?"
        
    except Exception as e:
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
        problem_extraction_prompt = ChatPromptTemplate.from_template("""
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
        
        Return ONLY the clean, simple search query. No explanations, no additional text.
        """)
        
        try:
            # Create message with both text and image
            from langchain_core.messages import HumanMessage
            message_content = [
                {"type": "text", "text": problem_extraction_prompt.format(query=query)},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
            response = llm.invoke([HumanMessage(content=message_content)])
            clean_query = response.content.strip()
            
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
    problem_extraction_prompt = ChatPromptTemplate.from_template("""
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
    
    Return ONLY the clean, simple search query. No explanations, no additional text.
    """)
    
    try:
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=problem_extraction_prompt.format(query=query))])
        clean_query = response.content.strip()
        
        # Fallback if LLM fails
        if not clean_query or len(clean_query) < 3:
            clean_query = query
        
    except Exception as e:
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


def googlemaps_node(state: AgentState) -> Dict[str, Any]:
    """
    Searches for local repair shops using Google Maps Places API
    """
    query = state["problem_statement"]
    
    try:
        # Create LLM instance to generate repair shop search query
        llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url=OLLAMA_BASE_URL,
            temperature=0.3
        )
        
        # Generate repair shop search query using LLM
        search_query_prompt = ChatPromptTemplate.from_template("""
        Based on this repair problem, generate a search query for finding local repair shops.
        
        Problem: {query}
        
        Your task:
        1. Identify what needs to be repaired
        2. Create a search query in the format: "repair shop for [what needs to be repaired]"
        
        Examples:
        - "how to fix cracked phone screen" → "repair shop for phone screen"
        - "laptop won't turn on" → "repair shop for laptop"
        - "car battery dead" → "repair shop for car battery"
        - "iPhone charging port broken" → "repair shop for iPhone charging port"
        
        Return ONLY the search query in the format: "repair shop for [item]" - no additional text.
        """)
        
        try:
            response = llm.invoke([HumanMessage(content=search_query_prompt.format(query=query))])
            repair_shop_query = response.content.strip()
            
            # Clean up the query
            if not repair_shop_query or len(repair_shop_query) < 5:
                repair_shop_query = f"repair shop for {query}"
        except Exception as e:
            print(f"Error generating repair shop query: {e}")
            repair_shop_query = f"repair shop for {query}"
        
        print(f"DEBUG: Google Maps search query: '{repair_shop_query}'")
        
        # For now, use default coordinates (San Francisco) - in production, get from user location
        # TODO: Get actual user location from request
        default_lat = 37.7749
        default_lng = -122.4194
        
        # Extract device type from query for better search
        device_type = "phone"  # Default
        if any(word in query.lower() for word in ["laptop", "computer", "pc"]):
            device_type = "laptop"
        elif any(word in query.lower() for word in ["car", "vehicle", "automobile"]):
            device_type = "car"
        elif any(word in query.lower() for word in ["phone", "iphone", "android", "smartphone"]):
            device_type = "phone"
        
        # Use the Google Maps search module
        places = search_repair_shops_advanced(
            query=repair_shop_query,
            latitude=default_lat,
            longitude=default_lng,
            radius=5000,  # 5km radius
            max_results=5,
            device_type=device_type
        )
        
        print(f"DEBUG: Google Maps search returned {len(places) if places else 0} places")
        
        if places and len(places) > 0:
            # Format the places into detailed content for local repair section
            content_parts = []
            
            content_parts.append(f"🔧 **Local Repair Shops for {query}:**\n")
            
            for i, place in enumerate(places, 1):
                place_info = f"{i}. **{place['name']}**\n"
                place_info += f"   📍 {place['address']}\n"
                
                if place.get('distance_km'):
                    place_info += f"   📏 {place['distance_km']} km away\n"
                
                if place.get('phone'):
                    place_info += f"   📞 {place['phone']}\n"
                
                if place.get('website'):
                    place_info += f"   🌐 {place['website']}\n"
                
                if place.get('rating'):
                    place_info += f"   ⭐ {place['rating']}/5.0 rating\n"
                
                if place.get('business_status'):
                    status_emoji = "🟢" if place['business_status'] == "OPERATIONAL" else "🔴"
                    place_info += f"   {status_emoji} {place['business_status']}\n"
                
                content_parts.append(place_info)
            
            content = "\n".join(content_parts)
            
            # Create separate local repair results (not included in sources)
            local_repair_data = {
                "content": content,
                "places": places,  # Store raw place data for detailed formatting
                "metadata": {
                    "source": "Google Maps",
                    "search_type": "local_repair_shops",
                    "places_found": len(places),
                    "device_type": device_type,
                    "search_radius_km": 5,
                    "search_query": repair_shop_query,
                    "google_maps_api": True
                },
                "success": True
            }
            
            # Create empty result for googlemaps_results (no sources)
            result = AgentResult(
                content="",  # Empty content since we're using local_repair_results
                source_urls=[],  # No sources from Google Maps
                metadata={
                    "source": "Google Maps",
                    "search_type": "local_repair_shops",
                    "places_found": len(places),
                    "device_type": device_type,
                    "search_radius_km": 5,
                    "search_query": repair_shop_query,
                    "google_maps_api": True
                },
                success=True
            )
            
            print(f"DEBUG: Returning {len(places)} local repair shops")
            return {
                "googlemaps_results": result.model_dump(),
                "local_repair_results": local_repair_data
            }
        else:
            # Fallback if no results
            result = AgentResult(
                content="",  # Empty content since we're using local_repair_results
                source_urls=[],  # No sources from Google Maps
                metadata={"source": "Google Maps", "search_type": "local_repair_shops", "places_found": 0},
                success=False
            )
            
            print("DEBUG: No local repair shops found")
            return {
                "googlemaps_results": result.model_dump(),
                "local_repair_results": {
                    "content": f"🔧 **Local Repair Shops:**\nNo repair shops found for: {query}",
                    "places": [],
                    "metadata": {"source": "Google Maps", "places_found": 0},
                    "success": False
                }
            }
        
    except Exception as e:
        result = AgentResult(
            content="",  # Empty content since we're using local_repair_results
            source_urls=[],  # No sources from Google Maps
            metadata={"source": "Google Maps", "error": str(e)},
            success=False
        )
        
        return {
            "googlemaps_results": result.model_dump(),
            "local_repair_results": {
                "content": f"🔧 **Local Repair Shops:**\nError searching for repair shops: {str(e)}",
                "places": [],
                "metadata": {"source": "Google Maps", "error": str(e)},
                "success": False
            }
        }


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
    
    for result_key in ["wikihow_results", "ifixit_results", "medium_results", "tavily_results", "googlemaps_results"]:
        if result_key in state and state[result_key]:
            result_data = state[result_key]
            if result_data.get("success"):
                all_results.append(result_data)
                # Extract URLs from the source_urls field (Google Maps has empty source_urls)
                source_urls = result_data.get("source_urls", [])
                all_sources.extend(source_urls)
    
    # Handle local repair results separately
    if "local_repair_results" in state and state["local_repair_results"]:
        local_repair_info = state["local_repair_results"]
    
    # Create LLM instance for aggregation
    llm = ChatOllama(
        model="qwen2.5vl:7b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )
    
    # LLM-based aggregation
    aggregation_prompt = ChatPromptTemplate.from_template("""
    You are an expert repair technician analyzing information from multiple sources to create the best possible solution.
    
    Original Query: {query}
    Problem Statement: {problem_statement}
    
    Available Information from Multiple Sources:
    {results_summary}
    
    Local Repair Information:
    {local_repair_summary}
    
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
    4. Includes local repair shop information if available
    
    OUTPUT FORMAT - Use EXACTLY this structure:
    
    Steps to fix your [specific problem]:
    1. [First step]
    2. [Second step]
    3. [Third step]
    [Continue with numbered steps as needed]
    
    Tools Needed:
    1. [Tool 1]
    2. [Tool 2]
    [Continue with numbered tools as needed]
    
    Materials Needed:
    1. [Material 1]
    2. [Material 2]
    [Continue with numbered materials as needed]
    
    {local_repair_section}
    
    Sources:
    1. [Source URL 1]
    2. [Source URL 2]
    [Continue with numbered sources as needed]
    
    IMPORTANT: 
    - Replace "[specific problem]" with the actual problem from the query
    - Make steps specific and actionable
    - List only essential tools and materials
    - Include local repair information if available
    - Include all source URLs that provided useful information (but NOT Google Maps URLs)
    - Use numbered lists only
    - No additional text, explanations, or sections
    """)
    
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
        
        # Prepare local repair summary
        local_repair_summary = ""
        local_repair_section = ""
        
        if local_repair_info and local_repair_info.get("success"):
            local_repair_summary = local_repair_info.get("content", "")
            local_repair_section = "Local Repair Shops:\n" + local_repair_info.get("content", "")
        else:
            local_repair_summary = "No local repair shops found."
            local_repair_section = ""
        
        # Debug: Print available sources
        print(f"DEBUG: Available sources: {all_sources}")
        print(f"DEBUG: Local repair info available: {local_repair_info is not None}")
        if local_repair_info:
            print(f"DEBUG: Local repair success: {local_repair_info.get('success', False)}")
            print(f"DEBUG: Local repair content length: {len(local_repair_info.get('content', ''))}")
        
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=aggregation_prompt.format(
            query=query,
            problem_statement=problem_statement,
            results_summary=results_summary,
            local_repair_summary=local_repair_summary,
            local_repair_section=local_repair_section
        ))])
        instructions = response.content
        
        # Always ensure local repair information is included if available
        if local_repair_info and local_repair_info.get("success"):
            import re
            # Check if local repair section already exists
            if "Local Repair Shops:" not in instructions:
                # Add local repair section before sources
                local_repair_section = "\n\nLocal Repair Shops:\n" + local_repair_info.get("content", "")
                # Insert before sources section
                instructions = re.sub(r'(\n\nSources:)', local_repair_section + r'\1', instructions)
        
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
        # Fallback instructions
        instructions = f"Unable to process query: {query}. Please try again."
        
        # Ensure local repair information is included even in fallback
        if local_repair_info and local_repair_info.get("success"):
            local_repair_section = "\n\nLocal Repair Shops:\n" + local_repair_info.get("content", "")
            instructions += local_repair_section
        
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
    
    for result_key in ["wikihow_results", "ifixit_results", "medium_results", "tavily_results", "googlemaps_results"]:
        if result_key in state and state[result_key]:
            result_data = state[result_key]
            if result_data.get("success"):
                source_urls = result_data.get("source_urls", [])
                all_sources.extend(source_urls)
    
    # Get local repair information separately
    local_repair_links = []
    if "local_repair_results" in state and state["local_repair_results"]:
        local_repair_info = state["local_repair_results"]
        # Extract Google Maps links from the places data
        if local_repair_info.get("success") and local_repair_info.get("places"):
            for place in local_repair_info["places"]:
                if place.get("place_id"):
                    google_maps_url = f"https://www.google.com/maps/place/?q=place_id:{place['place_id']}"
                    local_repair_links.append(google_maps_url)
    
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
        
        # Always ensure local repair information is included if available
        if local_repair_info and local_repair_info.get("success"):
            import re
            # Check if local repair section already exists
            if "Local Repair Shops:" not in final_response:
                # Add local repair section before sources
                local_repair_section = "\n\nLocal Repair Shops:\n" + local_repair_info.get("content", "")
                # Insert before sources section
                final_response = re.sub(r'(\n\nSources:)', local_repair_section + r'\1', final_response)
        
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
        
        # Ensure local repair information is included even in fallback
        if local_repair_info and local_repair_info.get("success"):
            import re
            # Check if local repair section already exists
            if "Local Repair Shops:" not in final_response:
                # Add local repair section before sources
                local_repair_section = "\n\nLocal Repair Shops:\n" + local_repair_info.get("content", "")
                # Insert before sources section
                final_response = re.sub(r'(\n\nSources:)', local_repair_section + r'\1', final_response)
        
        # Ensure sources are included even in fallback
        if all_sources:
            import re
            final_response = re.sub(r'\n\nSources:.*$', '', final_response, flags=re.DOTALL)
            sources_section = "\n\nSources:\n"
            for i, source in enumerate(all_sources, 1):
                sources_section += f"{i}. {source}\n"
            final_response += sources_section
    
    # Return the final response with metadata for frontend
    return {
        "final_response": final_response,
        "response_source": "problem_identification",
        "local_repair_links": local_repair_links
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
    workflow.add_node("googlemaps", googlemaps_node)
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
    
    # Sequential to parallel: problem_identification -> all 5 agents
    workflow.add_edge("problem_identification", "wikihow")
    workflow.add_edge("problem_identification", "ifixit") 
    workflow.add_edge("problem_identification", "medium")
    workflow.add_edge("problem_identification", "tavily")
    workflow.add_edge("problem_identification", "googlemaps")
    
    # Parallel to aggregator: all agents -> aggregator
    workflow.add_edge("wikihow", "aggregator")
    workflow.add_edge("ifixit", "aggregator")
    workflow.add_edge("medium", "aggregator")
    workflow.add_edge("tavily", "aggregator")
    workflow.add_edge("googlemaps", "aggregator")
    
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
        "googlemaps_results": {},
        "local_repair_results": {},  # Add local repair results field
        "final_response": "",
        "response_source": "",  # Will be set by conversation or examine node
        "local_repair_links": []  # Will be populated with Google Maps URLs
    }
    
    # Run the workflow
    result = app.invoke(initial_state)
    
    return result


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
        local_repair_links = result.get("local_repair_links", [])
        
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
                print(f"=== LOCAL REPAIR BUTTON SHOULD SHOW (found {len(local_repair_links)} repair shops) ===")
                if local_repair_links:
                    print("Google Maps Links for Frontend:")
                    for i, link in enumerate(local_repair_links, 1):
                        print(f"  {i}. {link}")
            else:
                print("No repair response generated")
        
        # Show timing
        print(f"\n⏱️ Total time: {elapsed_time:.2f} seconds")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'elapsed_time' in locals():
            print(f"⏱️ Time before error: {elapsed_time:.2f} seconds")