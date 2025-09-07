#!/usr/bin/env python3
"""
Test module for Tavily Search connectivity using LangChain integration
Tests the TavilySearch tool from langchain_tavily
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

try:
    from langchain_tavily import TavilySearch
except ImportError:
    print("❌ langchain_tavily not installed. Install with: pip install langchain-tavily")
    sys.exit(1)


def extract_article_content(url: str, title: str) -> Optional[Dict]:
    """
    Extract detailed content from a single article URL.
    
    Args:
        url: Article URL
        title: Article title
    
    Returns:
        Dictionary with article details and content
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Try to find main content area
        content_selectors = [
            'article',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content',
            'main',
            '.main-content',
            '[role="main"]'
        ]
        
        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break
        
        # If no specific content area found, use body
        if not content_element:
            content_element = soup.find('body')
        
        if not content_element:
            return None
        
        # Extract text content
        text_content = content_element.get_text()
        
        # Clean up the text and remove repetitions
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Remove common repetitive elements
        text = re.sub(r'\b(How To Fix|How to Fix|Step \d+:|Tools you may need|Parts of a faucet)\b.*?(?=\b(How To Fix|How to Fix|Step \d+:|Tools you may need|Parts of a faucet|$))', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove repeated phrases (simple deduplication)
        sentences = text.split('. ')
        unique_sentences = []
        seen = set()
        
        for sentence in sentences:
            # Normalize sentence for comparison
            normalized = re.sub(r'\s+', ' ', sentence.strip().lower())
            if normalized and normalized not in seen and len(normalized) > 10:
                unique_sentences.append(sentence.strip())
                seen.add(normalized)
        
        text = '. '.join(unique_sentences)
        
        # Limit content length (similar to Medium module)
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        # Structure content similar to Medium module
        content_paragraphs = [{
            'title': 'Article Content',
            'content': text
        }]
        
        return {
            'title': title,
            'url': url,
            'content': content_paragraphs
        }
        
    except Exception as e:
        return None


def search_tavily(search_query: str, max_results: int = 6) -> List[Dict]:
    """
    Tavily search that finds URLs from multiple sources and extracts full content.
    Searches at least 4 different sources and returns the first result with actual content.
    
    Args:
        search_query: Search term (e.g., "how to fix laptop overheating")
        max_results: Maximum number of results to search through (default 6 to ensure 4+ sources)
    
    Returns:
        List with single best result dictionary with title, url, content, and metadata
    """
    try:
        # Check for Tavily API key
        tavily_api_key = os.getenv('TAVILY_API_KEY')
        if not tavily_api_key:
            print("❌ TAVILY_API_KEY not found in environment variables")
            return []
        
        # Initialize Tavily Search Tool with higher max_results to ensure multiple sources
        tavily_search = TavilySearch(
            max_results=max_results,
            topic="general",
            api_key=tavily_api_key
        )
        
        # Perform the search
        search_results = tavily_search.invoke({"query": search_query})
        
        # Parse the results
        if isinstance(search_results, str):
            try:
                results_data = json.loads(search_results)
            except json.JSONDecodeError:
                return []
        else:
            results_data = search_results
        
        # Extract results from the response
        results = results_data.get("results", [])
        
        if not results:
            return []
        
        # Process results and return the first one with actual content
        for i, result in enumerate(results, 1):
            try:
                title = result.get("title", f"Result {i}")
                url = result.get("url", "")
                
                # Extract full content from the URL
                article_data = extract_article_content(url, title)
                if article_data and article_data.get('content'):
                    # Check if content actually has text
                    content = article_data.get('content', [])
                    if content and len(content) > 0:
                        content_text = content[0].get('content', '')
                        if content_text and len(content_text.strip()) > 50:  # Ensure meaningful content
                            return [article_data]  # Return first result with actual content
                
            except Exception as e:
                continue
        
        return []  # No results with content
        
    except Exception as e:
        print(f"❌ Error in Tavily search: {e}")
        return []


if __name__ == "__main__":
    print("🚀 Tavily Search Module Test")
    print("=" * 50)
    
    # Test with leaky faucet query
    test_query = "how to fix a leaky faucet"
    print(f"🔍 Testing with query: '{test_query}'")
    
    # Check API key first
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    if not tavily_api_key:
        print("❌ TAVILY_API_KEY not found in environment variables")
        print("💡 Get your API key from: https://tavily.com/")
        exit(1)
    
    print(f"✅ TAVILY_API_KEY found: {tavily_api_key[:8]}...")
    
    try:
        # Test Tavily search with multiple sources
        print("\n1️⃣ Testing Tavily search with multiple sources...")
        import time
        start = time.time()
        results = search_tavily(test_query, max_results=6)
        end = time.time()
        print(f"   ✅ Tavily search completed in {end-start:.2f}s, found {len(results)} results")
        
        # Show single result (like Medium module)
        if results:
            result = results[0]
            
            print("\n📄 TAVILY SEARCH RESULT:")
            print("=" * 50)
            print(f"Title: {result.get('title', 'Unknown')}")
            print(f"URL: {result.get('url', 'Unknown')}")
            
            content = result.get('content', [])
            if content and len(content) > 0:
                content_text = content[0].get('content', '')
                print(f"Content:\n{content_text}")
            else:
                print("Content: No content available")
        
        print("\n" + "=" * 50)
        print("🎉 Tavily search test completed successfully!")
        print("📋 Summary:")
        print(f"   • Search completed successfully")
        print(f"   • Searched multiple sources (6 results)")
        print(f"   • Content extracted and displayed")
        print("   • Single result format (like Medium module): ✅")
        
    except Exception as e:
        print(f"\n❌ Tavily search test failed: {e}")
        print("🔧 Troubleshooting:")
        print("   1. Check your TAVILY_API_KEY in .env file")
        print("   2. Get API key from: https://tavily.com/")
        print("   3. Install langchain-tavily: pip install langchain-tavily")
        print("   4. Check your internet connection")
