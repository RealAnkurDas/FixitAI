#!/usr/bin/env python3
"""
Test module for LLM connectivity
Tests the ChatOllama connection and basic functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

# Get OLLAMA_BASE_URL from environment, default to localhost:11434
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

def test_llm_connectivity():
    """Test LLM connectivity and basic functionality"""
    print("🧪 Testing LLM Connectivity...")
    print("=" * 50)
    print(f"🔗 Ollama URL: {OLLAMA_BASE_URL}")
    
    try:
        # Create LLM instance
        print("\n1️⃣ Creating LLM instance...")
        llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url=OLLAMA_BASE_URL,
            temperature=0.3
        )
        print("   ✅ LLM instance created successfully")
        
        # Test basic connectivity
        print("\n2️⃣ Testing basic connectivity...")
        test_prompt = "What is 2+2? Answer with just the number."
        print(f"   📝 Test prompt: {test_prompt}")
        
        response = llm.invoke([HumanMessage(content=test_prompt)])
        print(f"   ✅ Response received: {response.content}")
        
        # Test classification prompt (similar to orchestrator agent)
        print("\n3️⃣ Testing classification prompt...")
        classification_prompt = """Analyze this query and determine what type of content would be most helpful.

Query: How to fix a leaky faucet

Choose from these exact values:
- wikihow: For how-to guides, step-by-step tutorials, learning new skills
- ifixit: For device repair guides, troubleshooting, teardowns
- websearch: For general information, current solutions, research
- reddit: For real-world user experiences, community solutions
- stackexchange: For technical troubleshooting, detailed technical solutions
- official_support: For manufacturer support, warranty information, official procedures
- manufacturer_manual: For technical manuals, PDF guides, specifications
- online_retailer: For finding replacement parts, pricing, availability
- manualslib: For product manuals, technical documentation, assembly instructions

Return ONLY the exact value (e.g., "wikihow", "ifixit", etc.) with no additional text or formatting."""
        
        print("   📝 Classification prompt sent...")
        classification_response = llm.invoke([HumanMessage(content=classification_prompt)])
        print(f"   ✅ Classification response: {classification_response.content}")
        
        # Test aggregation prompt (similar to aggregator agent)
        print("\n4️⃣ Testing aggregation prompt...")
        aggregation_prompt = """Synthesize the following information into one coherent instruction set.

Original Query: How to fix a leaky faucet
Query Type: wikihow

Available Information:
Source 1: Step-by-step guide for fixing a leaky faucet including tools needed and safety precautions.

Create a comprehensive, specific repair guide that includes:
1. Clear step-by-step instructions tailored to the specific problem
2. Specific difficulty rating (1-10) based on the complexity
3. Relevant safety tips specific to this repair
4. Realistic time estimate based on the task
5. Specific tools needed for this repair
6. Specific materials or parts needed

Make the guide specific to the query - don't use generic language."""
        
        print("   📝 Aggregation prompt sent...")
        aggregation_response = llm.invoke([HumanMessage(content=aggregation_prompt)])
        print(f"   ✅ Aggregation response preview: {aggregation_response.content[:200]}...")
        
        print("\n" + "=" * 50)
        print("🎯 LLM connectivity test completed successfully!")
        print("✅ All LLM functionality is working properly")
        
    except Exception as e:
        print(f"\n❌ LLM test failed: {str(e)}")
        print(f"🔍 Error type: {type(e).__name__}")
        print("\n💡 Troubleshooting tips:")
        print("   • Make sure Ollama is running")
        print("   • Check if the model 'qwen2.5vl:7b' is installed")
        print("   • Verify the OLLAMA_BASE_URL in your .env file")
        print("   • Try running: ollama list")

if __name__ == "__main__":
    test_llm_connectivity()
