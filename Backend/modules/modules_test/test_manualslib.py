#!/usr/bin/env python3
"""
Test module for Manualslib connectivity
Tests the search_manualslib function from tools.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup

def search_manualslib(query: str) -> str:
    """
    Search Manualslib.com for product manuals.
    Note: Manuals are often PDFs/images, so vision/OCR may be needed to parse content.
    
    Args:
        query: Search term (e.g., "Samsung washing machine manual", "IKEA Malm assembly manual")
    """
    try:
        # Manualslib search endpoint
        url = "https://www.manualslib.com/serinfo.php"
        params = {"term": query}
        headers = {"User-Agent": "RepairBot/1.0"}
        
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        
        # Parse top few results
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select(".search-result a")[:5]:
            title = item.get_text(strip=True)
            link = "https://www.manualslib.com" + item.get("href")
            results.append(f"{title} - {link}")
        
        if not results:
            return f"No Manualslib results found for '{query}'."
        
        return f"Manualslib results for '{query}':\n\n" + "\n".join(results)
    
    except Exception as e:
        return f"Error searching Manualslib: {str(e)}"

def test_manualslib_connectivity():
    """Test Manualslib search functionality"""
    print("🧪 Testing Manualslib Connectivity...")
    print("=" * 50)
    
    # Test queries
    test_queries = [
        "Samsung washing machine manual",
        "iPhone user manual",
        "MacBook Pro manual",
        "Sony TV manual",
        "LG refrigerator manual"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test {i}: {query}")
        print("-" * 40)
        
        try:
            # Test the actual search function
            results = search_manualslib(query)
            
            if results:
                print(f"✅ Search successful!")
                print(f"📊 Results length: {len(results)} characters")
                
                # Parse results to extract URLs
                lines = results.split('\n')
                urls = []
                for line in lines:
                    if ' - http' in line:
                        url = line.split(' - ')[-1]
                        if url.startswith('http'):
                            urls.append(url)
                
                print(f"📚 Manuals found: {len(urls)}")
                for j, url in enumerate(urls[:3], 1):  # Show first 3 URLs
                    print(f"   {j}. {url}")
                
                if len(urls) > 3:
                    print(f"   ... and {len(urls) - 3} more")
                
                # Show sample content
                content_preview = results[:300] + "..." if len(results) > 300 else results
                print(f"📝 Content preview: {content_preview}")
                
            else:
                print("⚠️  No results returned")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
    
    print("\n" + "=" * 50)
    print("🎯 Manualslib connectivity test completed!")

if __name__ == "__main__":
    test_manualslib_connectivity()
