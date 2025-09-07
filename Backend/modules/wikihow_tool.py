#!/usr/bin/env python3
"""
Test module for WikiHow connectivity
Tests the search_wikihow function from tools.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup
import json
import re
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

def remove_markdown_formatting(text: str) -> str:
    """
    Remove all markdown formatting from text to ensure plain text output.
    """
    if not text:
        return text
    
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown bold/italic
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # Remove markdown code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Remove markdown links
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove markdown lists
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown horizontal rules
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    
    # Remove markdown tables
    text = re.sub(r'\|.*?\|', '', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    
    return text.strip()

def select_best_article_with_llm(search_query: str, unique_links: List[Dict]) -> int:
    """
    Use LLM to select the most relevant article from the list.
    
    Args:
        search_query: The original search query
        unique_links: List of article dictionaries with 'title' and 'url'
    
    Returns:
        Index of the selected article (0-based)
    """
    try:
        from langchain_ollama import ChatOllama
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        llm = ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model="qwen2.5vl:7b",
            temperature=0.1
        )
        
        # Create title mapping
        title_mapping = {}
        for i, article in enumerate(unique_links, 1):
            title_mapping[i] = article['title']
        
        # Create the mapping text for the prompt
        mapping_text = "\n".join([f"{num}: {title}" for num, title in title_mapping.items()])
        
        prompt = f"""You are an expert at selecting the most relevant WikiHow article for a given search query.

        Search Query: "{search_query}"

        Available Articles:
        {mapping_text}

        Instructions:
        - Analyze which article title is most relevant to the search query
        - Consider which article would best help someone accomplish the task described in the search query
        - Return ONLY the number (1, 2, 3, etc.) of the most relevant article
        - Do not include any explanation or additional text
        - Just return the single number

        Most relevant article number:"""
        
        llm_response = llm.invoke(prompt)
        
        # Extract the number from the response
        response_text = llm_response.content.strip()
        
        # Try to extract the first number from the response
        import re
        numbers = re.findall(r'\d+', response_text)
        if numbers:
            selected_num = int(numbers[0])
            # Convert to 0-based index and validate
            if 1 <= selected_num <= len(unique_links):
                return selected_num - 1  # Convert to 0-based index
        
        # Fallback: return first article if no valid selection
        return 0
        
    except Exception as e:
        # Fallback: return first article if LLM fails
        return 0

def search_wikihow_advanced(search_query: str, max_articles: int = 5) -> List[Dict]:
    """
    Advanced WikiHow search that extracts full article content and steps.
    
    Args:
        search_query: Search term (e.g., "how to make a website")
        max_articles: Maximum number of articles to process
    
    Returns:
        List of article dictionaries with title, date, views, link, and content
    """
    try:
        # Step 1: Search WikiHow
        search_url = f"https://www.wikihow.com/wikiHowTo?search={search_query.replace(' ', '+')}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Step 2: Parse search results and extract article links
        soup = BeautifulSoup(response.text, 'html.parser')
        article_links = []
        
        # Look for article links in search results
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and href.startswith('https://www.wikihow.com/') and not href.startswith('https://www.wikihow.com/Category:'):
                # This is a direct article URL
                title = link.get_text(strip=True)
                if title and len(title) > 10:  # Filter out short/nonsense titles
                    article_links.append({
                        'url': href,
                        'title': title
                    })
            elif href and href.startswith('/wiki/') and not href.startswith('/wiki/Category:'):
                # This is a relative article URL
                full_url = urljoin('https://www.wikihow.com', href)
                title = link.get_text(strip=True)
                if title and len(title) > 10:  # Filter out short/nonsense titles
                    article_links.append({
                        'url': full_url,
                        'title': title
                    })
        
        # Remove duplicates and limit results
        unique_links = []
        seen_urls = set()
        for article in article_links:
            if article['url'] not in seen_urls and len(unique_links) < max_articles:
                unique_links.append(article)
                seen_urls.add(article['url'])
        
        # Step 3: Use LLM to select the most relevant article
        if unique_links:
            print("Wikihow")
            print(f"Found {len(unique_links)} articles, using LLM to select most relevant...")
            
            # Create title mapping for display
            for i, article in enumerate(unique_links, 1):
                print(f"  {i}. {article['title']}")
            
            # Let LLM choose the best article
            selected_index = select_best_article_with_llm(search_query, unique_links)
            selected_article = unique_links[selected_index]
            
            print(f"\n🤖 LLM selected article {selected_index + 1}: {selected_article['title']}")
            
            # Step 4: Extract content from the selected article only
            try:
                article_data = extract_wikihow_article(selected_article['url'], selected_article['title'])
                if article_data:
                    return [article_data]  # Return the single selected article
            except Exception as e:
                print(f"Error extracting selected article: {e}")
        
        return []
        
    except Exception as e:
        return []

def extract_wikihow_article(url: str, title: str) -> Optional[Dict]:
    """
    Extract detailed content from a single WikiHow article.
    
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
        
        # Extract metadata
        date_updated = extract_date(soup)
        views = extract_views(soup)
        
        # Extract step-by-step content
        steps_content = extract_steps(soup)
        
        if not steps_content:
            return None
        
        return {
            'title': title,
            'date': date_updated,
            'views': views,
            'link': url,
            'content': steps_content
        }
        
    except Exception as e:
        return None

def extract_date(soup: BeautifulSoup) -> str:
    """Extract the last updated date from the article."""
    try:
        # Look for date in various locations
        date_selectors = [
            '.last_updated',
            '.date',
            '.timestamp',
            '[class*="date"]',
            '[class*="time"]'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                if date_text and any(word in date_text.lower() for word in ['updated', 'modified', 'published']):
                    return date_text
        
        # Fallback: look for any text that looks like a date
        for elem in soup.find_all(text=True):
            text = elem.strip()
            if re.search(r'(updated|modified|published).*\d+', text.lower()):
                return text
        
        return "Date not available"
        
    except Exception:
        return "Date not available"

def extract_views(soup: BeautifulSoup) -> str:
    """Extract view count from the article."""
    try:
        # Look for view count in various locations
        view_selectors = [
            '.views',
            '.view-count',
            '[class*="view"]',
            '[class*="count"]'
        ]
        
        for selector in view_selectors:
            view_elem = soup.select_one(selector)
            if view_elem:
                view_text = view_elem.get_text(strip=True)
                if re.search(r'\d+', view_text):
                    return view_text
        
        return "Views not available"
        
    except Exception:
        return "Views not available"

def extract_steps(soup: BeautifulSoup) -> List[Dict]:
    """Extract step-by-step content from the article."""
    try:
        steps = []
        
        # Method 1: Look for WikiHow step elements with specific classes
        # Only target elements with the specific classes we identified
        step_elements = soup.find_all('div', class_='step')
        
        if step_elements:
            for step_elem in step_elements:
                # Only process if this element has the specific classes we want
                if not step_elem.get('class') or 'step' not in step_elem.get('class', []):
                    continue
                
                # Extract step title from .whb class (step titles)
                title_elem = step_elem.find('b', class_='whb')
                if not title_elem:
                    continue  # Skip if no whb class found
                
                step_title = title_elem.get_text(strip=True)
                if not step_title:
                    continue  # Skip if no title text
                
                # Extract step content (everything except the title)
                step_content = ""
                for content_elem in step_elem.find_all(['p', 'ul', 'li']):
                    if content_elem != title_elem:
                        content_text = content_elem.get_text(strip=True)
                        if content_text and len(content_text) > 10:
                            step_content += content_text + " "
                
                step_content = step_content.strip()
                
                # Only add if we have meaningful content and the element has the right classes
                if step_content and len(step_content) > 20:
                    steps.append({
                        'title': step_title,
                        'content': step_content
                    })
        
        # Method 2: Look for section content with specific classes if no steps found
        if not steps:
            # Only look for elements with the specific classes we identified
            section_elements = soup.find_all('div', class_='section_text')
            for elem in section_elements:
                # Verify it has the right class
                if not elem.get('class') or 'section_text' not in elem.get('class', []):
                    continue
                    
                text = elem.get_text(strip=True)
                if text and len(text) > 50:  # Only meaningful content
                    steps.append({
                        'title': f"Content Section {len(steps)+1}",
                        'content': text
                    })
        
        # Method 3: Look for headline containers if still no content
        if not steps:
            headline_elements = soup.find_all('div', class_='headline_container')
            for elem in headline_elements:
                # Verify it has the right class
                if not elem.get('class') or 'headline_container' not in elem.get('class', []):
                    continue
                    
                text = elem.get_text(strip=True)
                if text and len(text) > 30:  # Only meaningful content
                    steps.append({
                        'title': f"Headline Section {len(steps)+1}",
                        'content': text
                    })
        
        # for step in steps:
        #     print(step)
        
        # Process steps in chunks of 10 and use async LLM calls
        try:
            # Process steps in chunks of 10
            chunk_size = 10
            step_chunks = [steps[i:i + chunk_size] for i in range(0, len(steps), chunk_size)]
            
            # Use async to process chunks in parallel
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            chunk_summaries = loop.run_until_complete(process_step_chunks_async(step_chunks))
            loop.close()
            
            # Combine all chunk summaries into one
            combined_summary = combine_chunk_summaries(chunk_summaries)
            
            # Final safety check to remove any remaining markdown
            final_cleaned_summary = remove_markdown_formatting(combined_summary)
            
            # Return the combined summary
            return [{
                'title': 'LLM Processed Summary',
                'content': final_cleaned_summary
            }]
            
        except Exception as e:
            # Fallback to raw steps if LLM fails
            return steps[:20]  # Limit to 20 steps
        
    except Exception as e:
        return []

def create_ultimate_guide_with_llm(articles_data: List[Dict], search_query: str) -> str:
    """Use LLM to merge all individual guide summaries into one ultimate guide."""
    try:
        from langchain_ollama import ChatOllama
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        llm = ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model="qwen2.5vl:7b",
            temperature=0.1
        )
        
        # Prepare the combined summaries for the LLM
        combined_summaries = []
        for i, article in enumerate(articles_data, 1):
            combined_summaries.append(f"Guide {i}: {article['title']}\n{article['content']}\n")
        
        all_summaries_text = "\n".join(combined_summaries)
        
        prompt = f"""You are an expert guide creator. Your task is to create ONE comprehensive, ultimate guide by combining information from multiple WikiHow guides on the same topic.

        Search Query: {search_query}
        Number of guides to combine: {len(articles_data)}

        Individual Guide Summaries:
        {all_summaries_text}

        Instructions:
        - Write ONLY ONE SINGLE PARAGRAPH
        - NO titles, headers, or section breaks
        - NO bullet points, numbered lists, or any formatting
        - Just write one continuous paragraph of approximately 800-1000 words
        - Create one comprehensive guide that combines the best information from all sources
        - Eliminate redundancy and contradictions
        - Include all important details, tools, and options from the sources
        - Present the information in a logical, coherent manner
        - Use your own words to make it clear and readable
        - DO NOT add any information that is not mentioned in the source guides
        - DO NOT use external knowledge
        - This should be the definitive guide that someone would follow to complete the task
        - Write in plain text only - no special characters or formatting

        Output format: Just write one single paragraph of normal text."""
        
        llm_response = llm.invoke(prompt)
        # print(f"\n🤖 Ultimate Guide Created:\n{llm_response.content[:300]}...")
        
        # Post-process to remove any markdown that might have slipped through
        cleaned_content = remove_markdown_formatting(llm_response.content)
        
        return cleaned_content
        
    except Exception as e:
        # Fallback: combine summaries manually
        fallback_content = f"Combined information from {len(articles_data)} guides on '{search_query}':\n\n"
        for i, article in enumerate(articles_data, 1):
            fallback_content += f"--- Guide {i}: {article['title']} ---\n{article['content']}\n\n"
        return fallback_content

async def process_step_chunks_async(step_chunks: List[List[Dict]]) -> List[str]:
    """Process step chunks asynchronously to get summaries."""
    from langchain_ollama import ChatOllama
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    llm = ChatOllama(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model="qwen2.5vl:7b",
        temperature=0.1
    )
    
    async def process_chunk(chunk: List[Dict]) -> str:
        """Process a single chunk of steps."""
        try:
            steps_text = "\n\n".join([f"Step {i+1}: {step['title']}\n{step['content']}" for i, step in enumerate(chunk)])
            
            prompt = f"""You are a helpful summarizer. Your task is to create a concise summary of the information provided in the source text below.

            Source text to summarize:
            {steps_text}

            Instructions:
            - Write ONLY ONE SINGLE PARAGRAPH
            - NO titles, headers, or section breaks
            - NO bullet points, numbered lists, or any formatting
            - Just write one continuous paragraph of approximately 150 words
            - Include the key details, tools, and options mentioned in the source
            - Use your own words to make it clear and readable
            - DO NOT add any information that is not mentioned in the source text
            - Write in plain text only - no special characters or formatting

            Output format: Just write one single paragraph of normal text."""
            
            # Since ChatOllama doesn't support async directly, we'll run it in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: llm.invoke(prompt))
            
            # Post-process to remove any markdown that might have slipped through
            cleaned_content = remove_markdown_formatting(response.content)
            
            return cleaned_content
            
        except Exception as e:
            return f"Error processing chunk: {str(e)}"
    
    # Process all chunks concurrently
    tasks = [process_chunk(chunk) for chunk in step_chunks]
    chunk_summaries = await asyncio.gather(*tasks)
    
    return chunk_summaries

def combine_chunk_summaries(chunk_summaries: List[str]) -> str:
    """Combine multiple chunk summaries into one comprehensive summary using LLM."""
    try:
        from langchain_ollama import ChatOllama
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        llm = ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model="qwen2.5vl:7b",
            temperature=0.1
        )
        
        # Combine all chunk summaries
        combined_text = "\n\n".join([f"Chunk {i+1}: {summary}" for i, summary in enumerate(chunk_summaries)])
        
        prompt = f"""You are an expert summarizer. Your task is to create ONE comprehensive summary by combining information from multiple chunk summaries.

        Chunk Summaries:
        {combined_text}

        Instructions:
        - Write ONLY ONE SINGLE PARAGRAPH
        - NO titles, headers, or section breaks
        - NO bullet points, numbered lists, or any formatting
        - Just write one continuous paragraph of approximately 500 words
        - Combine all the chunk information into one coherent paragraph
        - Eliminate redundancy and contradictions
        - Include all important details, tools, and options from the sources
        - Use your own words to make it clear and readable
        - DO NOT add any information that is not mentioned in the source chunks
        - DO NOT use external knowledge
        - Write in plain text only - no special characters or formatting

        Output format: Just write one single paragraph of normal text."""
        
        llm_response = llm.invoke(prompt)
        
        # Post-process to remove any markdown that might have slipped through
        cleaned_content = remove_markdown_formatting(llm_response.content)
        
        return cleaned_content
        
    except Exception as e:
        # Fallback: combine summaries manually
        fallback_content = f"Combined information from {len(chunk_summaries)} chunks:\n\n"
        for i, summary in enumerate(chunk_summaries, 1):
            fallback_content += f"--- Chunk {i} ---\n{summary}\n\n"
        return fallback_content

def search_wikihow(query: str) -> str:
    """
    Legacy function for backward compatibility.
    Now calls the advanced search function.
    """
    try:
        articles = search_wikihow_advanced(query, max_articles=3)
        if articles:
            return f"Found {len(articles)} WikiHow articles for '{query}':\n\n" + json.dumps(articles, indent=2)
        else:
            return f"No WikiHow articles found for '{query}'"
    except Exception as e:
        return f"Error searching WikiHow: {str(e)}"

def test_wikihow_connectivity():
    """Test WikiHow search functionality"""
    
    # Test queries
    test_queries = [
        "How to make a website",
        "How to fix a leaky faucet",
        "How to repair iPhone screen"
    ]
    
    # Test the exact format you showed
    print("\n🧪 Testing Exact Output Format...")
    print("=" * 50)
    
    # Test all queries from test_queries
    for test_query in test_queries:
        print(f"\n🔍 Testing: {test_query}")
        print(f"📊 Max articles: 3")
        
        try:
            import time
            start = time.time()
            articles = search_wikihow_advanced(test_query, 3)
            end = time.time()
            elapsed = end - start
           
            if articles:
                print(f"\n✅ Success! Generated ultimate guide in {elapsed:.2f} seconds")
                print("\n📋 WikiHow Guide Content:")
                print("=" * 60)
                
                # Since we return only one ultimate guide, just show its content
                article = articles[0]  # Get the first (and only) article
                print(article['content'][0]['content'])
                print("=" * 60)
                
                print(f"\n📊 Content Info:")
                print(f"  - Length: {len(article['content'])} characters")
                print(f"  - Processing time: {elapsed:.2f} seconds")
                
            else:
                print("❌ No articles found for the test query")
                
        except Exception as e:
            print(f"❌ Error in format test: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
        
        print("-" * 50)
    
    print("=" * 50)

def test_markdown_removal():
    """Test the markdown removal function to ensure it works correctly."""
    print("\n🧪 Testing Markdown Removal Function...")
    print("=" * 50)
    
    # Test cases with various markdown formats
    test_cases = [
        {
            "input": "# Header 1\n## Header 2\n**Bold text** and *italic text*",
            "expected": "Header 1\nHeader 2\nBold text and italic text"
        },
        {
            "input": "- Bullet point 1\n- Bullet point 2\n1. Numbered item\n2. Another item",
            "expected": "Bullet point 1\nBullet point 2\nNumbered item\nAnother item"
        },
        {
            "input": "```code block``` and `inline code`",
            "expected": "code block and inline code"
        },
        {
            "input": "[Link text](http://example.com) and > blockquote",
            "expected": "Link text and blockquote"
        },
        {
            "input": "| Table | Header |\n|-------|--------|\n| Cell  | Data   |",
            "expected": "Table Header\nCell Data"
        }
    ]
    
    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        result = remove_markdown_formatting(test_case["input"])
        expected = test_case["expected"]
        
        if result == expected:
            print(f"✅ Test {i} PASSED")
        else:
            print(f"❌ Test {i} FAILED")
            print(f"   Input: {test_case['input']}")
            print(f"   Expected: {expected}")
            print(f"   Got: {result}")
            all_passed = False
    
    if all_passed:
        print("\n🎉 All markdown removal tests passed!")
    else:
        print("\n⚠️  Some markdown removal tests failed!")
    
    print("=" * 50)

if __name__ == "__main__":
    test_wikihow_connectivity()
