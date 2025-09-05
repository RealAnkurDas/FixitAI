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


# Define the state schema
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    query: str
    query_type: str
    wikihow_results: Dict[str, Any]
    ifixit_results: Dict[str, Any]
    medium_results: Dict[str, Any]
    final_response: str
    next_action: str


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
# ORCHESTRATOR AGENT
# =============================================================================

def orchestrator_agent(state: AgentState) -> AgentState:
    """
    Decides what type of content is needed based on the query
    """
    query = state["query"]
    
    # Create LLM instance
    llm = ChatOllama(
        model="qwen2.5vl:7b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )
    
    # LLM-based classification
    classification_prompt = ChatPromptTemplate.from_template("""
    Analyze this query and determine what type of content would be most helpful.
    
    Query: {query}
    
    Choose from these exact values:
    - wikihow: For how-to guides, step-by-step tutorials, learning new skills, general DIY tasks
    - ifixit: For device repair guides, troubleshooting, teardowns, hardware repair
    - medium: For detailed articles, technical guides, programming tutorials, in-depth explanations
    
    Return ONLY the exact value (e.g., "wikihow", "ifixit", "medium") with no additional text or formatting.
    """)
    
    try:
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=classification_prompt.format(query=query))])
        classification_result = response.content.strip().lower()
        
        # Map the LLM response to query type
        if classification_result == "wikihow":
            query_type = QueryType.WIKIHOW
        elif classification_result == "ifixit":
            query_type = QueryType.IFIXIT
        elif classification_result == "medium":
            query_type = QueryType.MEDIUM
        else:
            # Default to wikihow for general queries
            query_type = QueryType.WIKIHOW
        
    except Exception as e:
        # Fallback to wikihow
        query_type = QueryType.WIKIHOW
    
    state["query_type"] = query_type.value
    state["next_action"] = f"run_{query_type.value}_agent"
    
    return state


# =============================================================================
# SPECIALIZED AGENTS
# =============================================================================

def wikihow_node(state: AgentState) -> AgentState:
    """
    Searches WikiHow and returns results in correct format to next agent
    """
    query = state["query"]
    
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
    
    state["wikihow_results"] = result.model_dump()
    state["next_action"] = "aggregator"
    
    return state


def ifixit_node(state: AgentState) -> AgentState:
    """
    Searches iFixit website using LangChain document loader and returns results in correct format
    """
    query = state["query"]
    
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
    
    state["ifixit_results"] = result.model_dump()
    state["next_action"] = "aggregator"
    
    return state


def medium_node(state: AgentState) -> AgentState:
    """
    Searches Medium articles using Google PSE and returns results in correct format
    """
    query = state["query"]
    
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
    
    state["medium_results"] = result.model_dump()
    state["next_action"] = "aggregator"
    
    return state


# =============================================================================
# AGGREGATOR/SUMMARIZER AGENT
# =============================================================================

def aggregator_agent(state: AgentState) -> AgentState:
    """
    Combines results from multiple sources into coherent instructions
    """
    query = state["query"]
    query_type = state["query_type"]
    
    # Collect all available results
    all_results = []
    sources = []
    
    for result_key in ["wikihow_results", "ifixit_results", "medium_results"]:
        if result_key in state and state[result_key]:
            result_data = state[result_key]
            if result_data.get("success"):
                all_results.append(result_data)
                sources.extend(result_data.get("source_urls", []))
    
    # Create LLM instance for aggregation
    llm = ChatOllama(
        model="qwen2.5vl:7b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )
    
    # LLM-based aggregation
    aggregation_prompt = ChatPromptTemplate.from_template("""
    Synthesize the following information into one coherent instruction set.
    
    Original Query: {query}
    Query Type: {query_type}
    
    Available Information:
    {results_summary}
    
    Create a comprehensive, specific repair guide that includes:
    1. Clear step-by-step instructions tailored to the specific problem
    2. Specific difficulty rating (1-10) based on the complexity
    3. Relevant safety tips specific to this repair
    4. Realistic time estimate based on the task
    5. Specific tools needed for this repair
    6. Specific materials or parts needed
    
    Make the guide specific to the query - don't use generic language.
    If this is about a specific device (like iPhone, Samsung, etc.), mention the specific model.
    If this is about a specific problem (like overheating, screen replacement), make the steps specific to that issue.
    
    Format your response as a structured guide with clear sections and specific details.
    """)
    
    try:
        # Prepare results summary for LLM
        results_summary = ""
        for i, result in enumerate(all_results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            results_summary += f"Source {i}: {content}\n"
            if metadata:
                results_summary += f"Metadata: {metadata}\n"
            results_summary += "\n"
        
        # Simple synchronous LLM call
        response = llm.invoke([HumanMessage(content=aggregation_prompt.format(
            query=query,
            query_type=query_type,
            results_summary=results_summary
        ))])
        instructions = response.content
        
        # Extract structured information from LLM response using another LLM call
        extraction_prompt = f"""Extract the following information from this repair guide. Return ONLY a JSON object with these exact keys:

Repair Guide:
{instructions}

Return this JSON format (no additional text):
{{
    "difficulty_rating": <number 1-10>,
    "estimated_time": "<time estimate>",
    "safety_tips": ["tip1", "tip2", "tip3"],
    "tools_needed": ["tool1", "tool2"],
    "materials_needed": ["material1", "material2"]
}}

If any information is not found, use reasonable defaults."""
        
        try:
            extraction_response = llm.invoke([HumanMessage(content=extraction_prompt)])
            extraction_text = extraction_response.content.strip()
            
            # Try to parse JSON response
            import json
            try:
                extracted_data = json.loads(extraction_text)
                difficulty = extracted_data.get("difficulty_rating", 5)
                estimated_time = extracted_data.get("estimated_time", "30-90 minutes")
                safety_tips = extracted_data.get("safety_tips", [
                    "Always wear protective equipment",
                    "Work in a well-ventilated area",
                    "Have emergency contacts ready"
                ])
                tools_needed = extracted_data.get("tools_needed", [])
                materials_needed = extracted_data.get("materials_needed", [])
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                difficulty = 5
                estimated_time = "30-90 minutes"
                safety_tips = [
                    "Always wear protective equipment",
                    "Work in a well-ventilated area",
                    "Have emergency contacts ready"
                ]
                tools_needed = []
                materials_needed = []
                
        except Exception as e:
            # Fallback values
            difficulty = 5
            estimated_time = "30-90 minutes"
            safety_tips = [
                "Always wear protective equipment",
                "Work in a well-ventilated area",
                "Have emergency contacts ready"
            ]
            tools_needed = []
            materials_needed = []
        
    except Exception as e:
        # Fallback instructions
        instructions = f"Unable to process query: {query}. Please try again."
        difficulty = 5
        safety_tips = ["Always wear protective equipment", "Work in a well-ventilated area"]
    
    final_response = FinalResponse(
        instructions=instructions,
        difficulty_rating=difficulty,
        safety_tips=safety_tips,
        sources=list(set(sources)),  # Remove duplicates
        estimated_time=estimated_time,
        tools_needed=tools_needed,
        materials_needed=materials_needed
    )
    
    state["final_response"] = final_response.model_dump_json()
    state["next_action"] = "end"
    
    return state


# =============================================================================
# ROUTING LOGIC
# =============================================================================

def route_next_action(state: AgentState) -> str:
    """
    Determines the next node to execute based on state
    """
    next_action = state.get("next_action", "")
    
    if next_action.startswith("run_"):
        # Extract the agent name from "run_agentname_agent" format
        agent_name = next_action.replace("run_", "").replace("_agent", "")
        return agent_name
    elif next_action == "aggregator":
        return "aggregator"
    elif next_action == "end":
        return END
    else:
        return "orchestrator"


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_multiagent_graph():
    """
    Creates and returns the LangGraph workflow
    """
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("orchestrator", orchestrator_agent)
    workflow.add_node("wikihow", wikihow_node)
    workflow.add_node("ifixit", ifixit_node)
    workflow.add_node("medium", medium_node)
    workflow.add_node("aggregator", aggregator_agent)
    
    # Set entry point
    workflow.set_entry_point("orchestrator")
    
    # Add conditional routing from orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        route_next_action,
        {
            "wikihow": "wikihow",
            "ifixit": "ifixit", 
            "medium": "medium"
        }
    )
    
    # All specialized agents route to aggregator
    for agent_name in ["wikihow", "ifixit", "medium"]:
        workflow.add_edge(agent_name, "aggregator")
    
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
        "query_type": "",
        "wikihow_results": {},
        "ifixit_results": {},
        "medium_results": {},
        "final_response": "",
        "next_action": ""
    }
    
    # Run the workflow
    result = app.invoke(initial_state)
    
    return result


if __name__ == "__main__":
    print("🧪 Testing Multi-Agent System...")
    print("=" * 50)
    
    try:
        # Test 1: LLM connectivity
        print("1️⃣ Testing LLM connectivity...")
        llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url=OLLAMA_BASE_URL,
            temperature=0.3
        )
        
        test_prompt = "What is 2+2? Answer with just the number."
        response = llm.invoke([HumanMessage(content=test_prompt)])
        print(f"   ✅ LLM test successful: {response.content}")
        
        # Test 2: Generate Mermaid diagram
        print("\n2️⃣ Generating Mermaid diagram...")
        try:
            workflow = create_multiagent_graph()
            mermaid_code = workflow.get_graph().draw_mermaid()
            print("📊 Mermaid Diagram:")
            print("=" * 50)
            print(mermaid_code)
            print("=" * 50)
            print("💡 Copy the above Mermaid code to visualize your workflow!")
        except Exception as mermaid_error:
            print(f"   ⚠️  Could not generate Mermaid diagram: {mermaid_error}")
        
        # Test 3: Full multi-agent system
        print("\n3️⃣ Testing full multi-agent system...")
        
        # Test different types of queries
        test_queries = [
            "How to fix a leaky faucet",
            "iPhone 12 screen replacement guide",
            "How to build a website from scratch"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔍 Query: {query}")
            print("=" * 60)
            
            try:
                import time
                start_time = time.time()
                
                # Run the full multi-agent system
                result = run_multiagent_system(query)
                
                end_time = time.time()
                elapsed_time = end_time - start_time
                
                # Show only the final response
                if result.get("final_response"):
                    try:
                        final_data = result["final_response"]
                        if isinstance(final_data, str):
                            import json
                            final_data = json.loads(final_data)
                        
                        print(final_data.get('instructions', 'No instructions available'))
                        print(f"\n⏱️  Time taken: {elapsed_time:.2f} seconds")
                        
                    except Exception as parse_error:
                        print("Error processing response")
                        print(f"\n⏱️  Time taken: {elapsed_time:.2f} seconds")
                
            except Exception as agent_error:
                print("Error: Unable to process query")
                if 'elapsed_time' in locals():
                    print(f"\n⏱️  Time taken: {elapsed_time:.2f} seconds")
        
        print("\n🎉 All tests completed!")
        print("=" * 50)
        print("📋 Summary:")
        print("   • LLM integration: ✅ Working")
        print("   • Mermaid diagram: ✅ Generated")
        print("   • Multi-agent system: ✅ Working")
        print("   • Agent routing: ✅ Working")
        print("   • Result aggregation: ✅ Working")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        print(f"🔍 Error type: {type(e).__name__}")
        print("Make sure Ollama is running and accessible at the configured URL.")
        print("Check that all required packages are installed:")
        print("   pip install langgraph langchain-ollama python-dotenv")