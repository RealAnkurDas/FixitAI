from typing import TypedDict, Annotated, List, Dict, Any
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
    problem_statement: str
    wikihow_results: Dict[str, Any]
    ifixit_results: Dict[str, Any]
    medium_results: Dict[str, Any]
    final_response: str


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
# PROBLEM IDENTIFICATION NODE
# =============================================================================

def problem_identification_node(state: AgentState) -> AgentState:
    """
    Simple pass-through node that just copies the query to problem_statement
    """
    # Create a new state dict to avoid mutation issues
    new_state = state.copy()
    new_state["problem_statement"] = state["query"]
    
    return new_state


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


# =============================================================================
# AGGREGATOR/SUMMARIZER AGENT
# =============================================================================

def aggregator_agent(state: AgentState) -> Dict[str, Any]:
    """
    Combines results from multiple sources into coherent instructions
    """
    query = state["query"]
    problem_statement = state["problem_statement"]
    
    # Collect all available results and extract URLs
    all_results = []
    all_sources = []
    
    for result_key in ["wikihow_results", "ifixit_results", "medium_results"]:
        if result_key in state and state[result_key]:
            result_data = state[result_key]
            if result_data.get("success"):
                all_results.append(result_data)
                # Extract URLs from the source_urls field
                source_urls = result_data.get("source_urls", [])
                all_sources.extend(source_urls)
    
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
    
    Sources:
    1. [Source URL 1]
    2. [Source URL 2]
    [Continue with numbered sources as needed]
    
    IMPORTANT: 
    - Replace "[specific problem]" with the actual problem from the query
    - Make steps specific and actionable
    - List only essential tools and materials
    - Include all source URLs that provided useful information
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
        
        # Debug: Print available sources
        print(f"DEBUG: Available sources: {all_sources}")
        
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=aggregation_prompt.format(
            query=query,
            problem_statement=problem_statement,
            results_summary=results_summary
        ))])
        instructions = response.content
        
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
        if all_sources:
            sources_section = "\n\nSources:\n"
            for i, source in enumerate(all_sources, 1):
                sources_section += f"{i}. {source}\n"
            instructions += sources_section
    
    # Return only the clean instructions
    return {"final_response": instructions}


# =============================================================================
# GRAPH CONSTRUCTION - FIX: Use conditional routing to handle parallel execution properly
# =============================================================================

def create_multiagent_graph():
    """
    Creates and returns the LangGraph workflow with parallel execution
    """
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("problem_identification", problem_identification_node)
    workflow.add_node("wikihow", wikihow_node)
    workflow.add_node("ifixit", ifixit_node)
    workflow.add_node("medium", medium_node)
    workflow.add_node("aggregator", aggregator_agent)
    
    # Set entry point
    workflow.set_entry_point("problem_identification")
    
    # Sequential to parallel: problem_identification -> all 3 agents
    workflow.add_edge("problem_identification", "wikihow")
    workflow.add_edge("problem_identification", "ifixit") 
    workflow.add_edge("problem_identification", "medium")
    
    # Parallel to aggregator: all agents -> aggregator
    workflow.add_edge("wikihow", "aggregator")
    workflow.add_edge("ifixit", "aggregator")
    workflow.add_edge("medium", "aggregator")
    
    # Aggregator routes to end
    workflow.add_edge("aggregator", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

def run_multiagent_system(query: str):
    """
    Example of how to run the multiagent system
    """
    # Create the graph
    app = create_multiagent_graph()
    
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "problem_statement": "",
        "wikihow_results": {},
        "ifixit_results": {},
        "medium_results": {},
        "final_response": ""
    }
    
    # Run the workflow
    result = app.invoke(initial_state)
    
    return result


if __name__ == "__main__":
    import time
    
    # Test with a simple query
    test_query = "How to fix a leaky faucet"
    
    try:
        # Start timing
        start_time = time.time()
        
        # Run the multi-agent system
        result = run_multiagent_system(test_query)
        
        # End timing
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Show only the final response
        if result.get("final_response"):
            print(result["final_response"])
        else:
            print("No response generated")
        
        # Show timing
        print(f"\n⏱️ Total time: {elapsed_time:.2f} seconds")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'elapsed_time' in locals():
            print(f"⏱️ Time before error: {elapsed_time:.2f} seconds")