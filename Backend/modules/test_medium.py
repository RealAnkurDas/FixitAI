#!/usr/bin/env python3
"""
Test module for Medium Search connectivity
Tests Medium search functionality similar to WikiHow but for Medium articles
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
from urllib.parse import urljoin, urlparse, quote
from googleapiclient.discovery import build
from dotenv import load_dotenv

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
    Use LLM to select the most relevant Medium article from the list.
    
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
            title_mapping[i] = f"{article['title']} - {article.get('author', 'Unknown Author')}"
        
        # Create the mapping text for the prompt
        mapping_text = "\n".join([f"{num}: {title}" for num, title in title_mapping.items()])
        
        prompt = f"""You are an expert at selecting the most relevant Medium article for a given search query.

        Search Query: "{search_query}"

        Available Medium Articles:
        {mapping_text}

        Instructions:
        - Analyze which Medium article title is most relevant to the search query
        - Consider which article would best help someone accomplish the task described in the search query
        - Prefer comprehensive guides, tutorials, and detailed explanations
        - Consider the author's expertise if mentioned
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

def search_medium_advanced(search_query: str, max_articles: int = 10) -> List[Dict]:
    """
    Advanced Medium search using Google PSE to find Medium articles.
    
    Args:
        search_query: Search term (e.g., "how to make a website")
        max_articles: Maximum number of articles to process
    
    Returns:
        List of article dictionaries with title, url, author, and content
    """
    try:
        # Step 1: Use Google PSE to find Medium articles
        load_dotenv()
        api_key = os.getenv("GOOGLE_PSE_API_KEY")
        cx = os.getenv("GOOGLE_PSE_CX")
        
        if not api_key or not cx:
            #print("❌ Google PSE API key or CX not set in environment variables")
            #print("   Please set GOOGLE_PSE_API_KEY and GOOGLE_PSE_CX in your .env file")
            return []
        
        # Use the search query directly since PSE is configured for Medium only
        google_query = search_query
        
        #print(f"🔍 Google PSE search for: '{google_query}'")
        #print("=" * 60)
        
        # Build the search service
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Execute the search
        search_results = service.cse().list(
            q=google_query, 
            cx=cx, 
            num=min(max_articles, 10)  # Google PSE max is 10 per request
        ).execute()
        
        article_links = []
        
        # Process the search results
        for i, item in enumerate(search_results.get('items', []), 1):
            url = item.get('link', '')
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            
            #print(f"📝 Result {i}:")
            #print(f"   Title: {title}")
            #print(f"   URL: {url}")
            #print(f"   Snippet: {snippet[:100]}...")
            
            # All results are from Medium since PSE is configured for Medium only
            #print(f"✅ Medium article found!")
            
            # Extract author from URL
            author_match = re.search(r'/@([^/]+)/', url)
            author = author_match.group(1) if author_match else "Unknown Author"
            
            # Clean up title (remove any Medium suffix)
            clean_title = title.split(' - Medium')[0]  # Remove " - Medium" suffix if present
            clean_title = clean_title.split(' | by ')[0]  # Remove " | by Author" if present
            
            #print(f"👤 Author: {author}")
            #print(f"📰 Clean Title: {clean_title}")
            
            # Add to article list (all results are valid Medium articles)
            article_links.append({
                'url': url,
                'title': clean_title,
                'author': author,
                'snippet': snippet
            })
            #print(f"✅ Added to article list!")
            
            #print("-" * 40)
        
        # No need to remove duplicates as Google PSE doesn't return duplicates
        unique_links = article_links[:max_articles]
        
        # Step 3: Use LLM to select the most relevant article
        if unique_links:
            #print(f"Found {len(unique_links)} Medium articles, using LLM to select most relevant...")
            
            # Create title mapping for display
            for i, article in enumerate(unique_links, 1):
                #print(f"  {i}. {article['title']}")
                #print(f"     Author: {article['author']}")
                #print(f"     URL: {article['url']}")
                pass
            
            # Let LLM choose the best article
            selected_index = select_best_article_with_llm(search_query, unique_links)
            selected_article = unique_links[selected_index]
            
            #print(f"\n🤖 LLM selected article {selected_index + 1}: {selected_article['title']}")
            #print(f"    By: {selected_article['author']}")
            
            # Step 4: Extract content from the selected article only
            try:
                article_data = extract_medium_article(selected_article['url'], selected_article['title'], selected_article['author'])
                if article_data:
                    return [article_data]  # Return the single selected article
            except Exception as e:
                pass
                #print(f"Error extracting selected article: {e}")
        
        return []
        
    except Exception as e:
        #print(f"Error in Medium search: {e}")
        return []

def extract_medium_article(url: str, title: str, author: str) -> Optional[Dict]:
    """
    Extract detailed content from a single Medium article.
    
    Args:
        url: Article URL
        title: Article title
        author: Article author
    
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
        
        # Extract content using Medium-specific strategies
        content_paragraphs = extract_medium_content(soup)
        
        if not content_paragraphs:
            return None
        
        return {
            'title': title,
            'author': author,
            'url': url,
            'content': content_paragraphs
        }
        
    except Exception as e:
        #print(f"Error extracting Medium article {url}: {e}")
        return None

def extract_medium_content(soup: BeautifulSoup) -> List[Dict]:
    """Extract main content from a Medium article."""
    try:
        content_paragraphs = []
        
        # Remove unwanted elements
        for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
            unwanted.decompose()
        
        # Medium-specific content extraction
        # Medium typically uses article tags or specific content containers
        article_selectors = [
            'article',
            '[data-testid="storyContent"]',
            '.postArticle-content',
            '.section-content',
            'main',
            '[role="main"]'
        ]
        
        article_content = None
        for selector in article_selectors:
            article_content = soup.select_one(selector)
            if article_content:
                break
        
        if not article_content:
            # Fallback: look for the largest content container
            article_content = soup.find('body')
        
        if article_content:
            # Extract paragraphs from Medium article
            # Medium uses various paragraph classes and structures
            paragraph_selectors = [
                'p',
                '[data-selectable-paragraph]',
                '.graf--p',
                '.paragraph'
            ]
            
            all_paragraphs = []
            for selector in paragraph_selectors:
                all_paragraphs.extend(article_content.find_all(selector))
            
            # If no specific Medium paragraphs found, fall back to all p tags
            if not all_paragraphs:
                all_paragraphs = article_content.find_all('p')
            
            for para in all_paragraphs:
                text = para.get_text(strip=True)
                
                # Filter out short, navigation, or junk content
                if (len(text) > 50 and 
                    not any(skip_word in text.lower() for skip_word in 
                           ['follow', 'clap', 'subscribe', 'sign up', 'more from', 'written by']) and
                    len(text.split()) > 10):  # At least 10 words
                    
                    content_paragraphs.append({
                        'title': f"Section {len(content_paragraphs)+1}",
                        'content': text
                    })
                    
                    # Limit to reasonable amount of content
                    if len(content_paragraphs) >= 25:
                        break
        
        # Process content in chunks similar to WikiHow
        if content_paragraphs:
            try:
                # Process content in chunks of 10 and use async LLM calls
                chunk_size = 10
                content_chunks = [content_paragraphs[i:i + chunk_size] for i in range(0, len(content_paragraphs), chunk_size)]
                
                # Use async to process chunks in parallel
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                chunk_summaries = loop.run_until_complete(process_content_chunks_async(content_chunks))
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
                # Fallback to raw content if LLM fails
                return content_paragraphs[:15]  # Limit to 15 sections
        
        return []
        
    except Exception as e:
        return []

async def process_content_chunks_async(content_chunks: List[List[Dict]]) -> List[str]:
    """Process content chunks asynchronously to get summaries."""
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
        """Process a single chunk of content."""
        try:
            content_text = "\n\n".join([f"Section {i+1}: {section['content']}" for i, section in enumerate(chunk)])
            
            prompt = f"""You are a helpful summarizer. Your task is to create a concise summary of the information provided in the source text below.

            Source text to summarize:
            {content_text}

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
    tasks = [process_chunk(chunk) for chunk in content_chunks]
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

def search_medium(query: str) -> str:
    """
    Legacy function for backward compatibility.
    Now calls the advanced search function.
    """
    try:
        articles = search_medium_advanced(query, max_articles=10)
        if articles:
            return f"Found {len(articles)} Medium articles for '{query}':\n\n" + json.dumps(articles, indent=2)
        else:
            return f"No Medium articles found for '{query}'"
    except Exception as e:
        return f"Error searching Medium: {str(e)}"

def test_medium_connectivity():
    """Test Medium search functionality"""
    
    # Test queries
    test_queries = [
        "How to make a website",
        "How to fix a leaky faucet",
        "How to repair iPhone screen"
    ]
    
    # Test the exact format
    #print("\n🧪 Testing Medium Search Output Format...")
    #print("=" * 50)
    
    # Test all queries from test_queries
    for test_query in test_queries:
        #print(f"\n🔍 Testing: {test_query}")
        #print(f"📊 Max articles: 5")
        
        try:
            import time
            start = time.time()
            articles = search_medium_advanced(test_query, 20)
            end = time.time()
            elapsed = end - start
           
            if articles:
                #print(f"\n✅ Success! Generated Medium guide in {elapsed:.2f} seconds")
                #print("\n📋 Medium Guide Content:")
                #print("=" * 60)
                
                # Since we return only one selected article, just show its content
                article = articles[0]  # Get the first (and only) article
                #print(article['content'][0]['content'])
                #print("=" * 60)
                
                #print(f"\n📊 Content Info:")
                #print(f"  - Length: {len(article['content'][0]['content'])} characters")
                #print(f"  - Processing time: {elapsed:.2f} seconds")
                #print(f"  - Author: {article['author']}")
                #print(f"  - Source: {article['url']}")
                
            else:
                pass
                #print("❌ No Medium articles found for the test query")
                
        except Exception as e:
            pass
            #print(f"❌ Error in format test: {str(e)}")
            #print(f"🔍 Error type: {type(e).__name__}")
        
        pass
        #print("-" * 50)
    
    pass
    #print("=" * 50)

if __name__ == "__main__":
    test_medium_connectivity()
