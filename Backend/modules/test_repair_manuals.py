#!/usr/bin/env python3
"""
Test module for repair manuals search functionality
Tests the search_repair_manuals function from orig_tools.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.tools import DuckDuckGoSearchRun

def search_repair_manuals(device: str = None, part: str = None, keywords: str = None) -> str:
    """
    Search for repair manuals.
    Priority:
    1. iFixit.com search
    2. General web search
    """
    # Build search terms
    search_terms = []
    if device:
        search_terms.append(device)
    if part:
        search_terms.append(part)
    if keywords:
        keyword_list = [k.strip() for k in keywords.split(',')]
        search_terms.extend(keyword_list)

    if not search_terms:
        return "No search terms provided for online search."

    # 1️⃣ Search iFixit directly first
    query = "site:ifixit.com " + " ".join(search_terms)
    search_tool = DuckDuckGoSearchRun()
    ifixit_results = search_tool.run(query)
    if ifixit_results and "ifixit" in ifixit_results.lower():
        return f"Here are some iFixit repair guides for '{' '.join(search_terms)}':\n\n{ifixit_results}"

    # 2️⃣ Fallback to general search
    general_query = "repair manual " + " ".join(search_terms)
    web_results = search_tool.run(general_query)
    return f"No iFixit results found. Here are some general online search results for '{general_query}':\n\n{web_results}"

def test_repair_manuals_connectivity():
    """Test repair manuals search functionality"""
    print("🧪 Testing Repair Manuals Search...")
    print("=" * 50)
    
    # Test queries with different combinations
    test_queries = [
        # Device only
        {"device": "iPhone 13", "part": None, "keywords": None},
        # Part only
        {"device": None, "part": "screen replacement", "keywords": None},
        # Keywords only
        {"device": None, "part": None, "keywords": "repair, troubleshooting"},
        # Device + Part
        {"device": "Samsung washing machine", "part": "drain pump", "keywords": None},
        # Device + Keywords
        {"device": "MacBook Pro", "part": None, "keywords": "battery, replacement"},
        # All three
        {"device": "PS4 controller", "part": "analog stick", "keywords": "repair, drift fix"},
    ]
    
    for i, query_params in enumerate(test_queries, 1):
        print(f"\n🔍 Test {i}:")
        print(f"   Device: {query_params['device'] or 'None'}")
        print(f"   Part: {query_params['part'] or 'None'}")
        print(f"   Keywords: {query_params['keywords'] or 'None'}")
        print("-" * 40)
        
        try:
            # Test the actual search function
            results = search_repair_manuals(
                device=query_params['device'],
                part=query_params['part'],
                keywords=query_params['keywords']
            )
            
            if results:
                print(f"✅ Search successful!")
                print(f"📊 Results length: {len(results)} characters")
                
                # Check if iFixit results were found
                if "ifixit" in results.lower():
                    print("🔧 iFixit results found!")
                else:
                    print("🌐 General web search results")
                
                # Show sample content
                content_preview = results[:300] + "..." if len(results) > 300 else results
                print(f"📝 Content preview: {content_preview}")
                
            else:
                print("⚠️  No results returned")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
    
    print("\n" + "=" * 50)
    print("🎯 Repair manuals search test completed!")

if __name__ == "__main__":
    test_repair_manuals_connectivity()
