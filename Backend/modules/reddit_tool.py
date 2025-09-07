#!/usr/bin/env python3
"""
Test module for Reddit Search connectivity
Tests Reddit search functionality to find relevant Reddit posts
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

def select_best_post_with_llm(search_query: str, unique_links: List[Dict]) -> int:
    """
    Use LLM to select the most relevant Reddit post from the list.
    
    Args:
        search_query: The original search query
        unique_links: List of post dictionaries with 'title' and 'url'
    
    Returns:
        Index of the selected post (0-based)
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
        for i, post in enumerate(unique_links, 1):
            title_mapping[i] = f"{post['title']} - r/{post.get('subreddit', 'Unknown')} by u/{post.get('author', 'Unknown')}"
        
        # Create the mapping text for the prompt
        mapping_text = "\n".join([f"{num}: {title}" for num, title in title_mapping.items()])
        
        prompt = f"""You are an expert at selecting the most relevant Reddit post for a given search query.

        Search Query: "{search_query}"

        Available Reddit Posts:
        {mapping_text}

        Instructions:
        - Analyze which Reddit post title is most relevant to the search query
        - Consider which post would best help someone accomplish the task described in the search query
        - Prefer detailed discussions, comprehensive guides, and helpful explanations
        - Consider the subreddit context and author if mentioned
        - Return ONLY the number (1, 2, 3, etc.) of the most relevant post
        - Do not include any explanation or additional text
        - Just return the single number

        Most relevant post number:"""
        
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
        
        # Fallback: return first post if no valid selection
        return 0
        
    except Exception as e:
        # Fallback: return first post if LLM fails
        return 0

def search_reddit_advanced(search_query: str, max_posts: int = 10) -> List[Dict]:
    """
    Advanced Reddit search using Google PSE to find Reddit posts.
    
    Args:
        search_query: Search term (e.g., "how to make a website")
        max_posts: Maximum number of posts to process
    
    Returns:
        List of post dictionaries with title, url, author, subreddit, and content
    """
    try:
        # Step 1: Use Google PSE to find Reddit posts
        load_dotenv()
        # Use Reddit-specific API key and CX
        api_key = os.getenv("GOOGLE_PSE_API_KEY_REDDIT", "AIzaSyDnoSyRVvIBXWfaGzBI-eyboIP9NpSlBeE")
        cx = os.getenv("GOOGLE_PSE_CX_REDDIT", "963dbddd12d434e90")
        
        if not api_key or not cx:
            print("❌ Google PSE API key or CX not set for Reddit search")
            print("   Please set GOOGLE_PSE_API_KEY_REDDIT and GOOGLE_PSE_CX_REDDIT in your .env file")
            return []
        
        # Use the search query with site:reddit.com to find Reddit posts
        google_query = f"{search_query} site:reddit.com"
        
        print(f"🔍 Google PSE search for: '{google_query}'")
        print("=" * 60)
        
        # Build the search service
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Execute the search
        search_results = service.cse().list(
            q=google_query, 
            cx=cx, 
            num=min(max_posts, 10)  # Google PSE max is 10 per request
        ).execute()
        
        post_links = []
        
        # Process the search results
        for i, item in enumerate(search_results.get('items', []), 1):
            url = item.get('link', '')
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            
            print(f"📝 Result {i}:")
            print(f"   Title: {title}")
            print(f"   URL: {url}")
            print(f"   Snippet: {snippet[:100]}...")
            
            # Check if this is a Reddit post URL
            if 'reddit.com' in url and '/comments/' in url:
                print(f"✅ Reddit post found!")
                
                # Extract subreddit and author from URL and title
                subreddit_match = re.search(r'/r/([^/]+)/', url)
                subreddit = subreddit_match.group(1) if subreddit_match else "Unknown"
                
                # Try to extract author from title or set as unknown
                author_match = re.search(r'by.*?u/([^\s\]]+)', title)
                if not author_match:
                    author_match = re.search(r'u/([^\s\]]+)', title)
                author = author_match.group(1) if author_match else "Unknown"
                
                # Clean up title (remove Reddit suffix and author info)
                clean_title = title.split(' : r/')[0]  # Remove subreddit info
                clean_title = clean_title.split(' - Reddit')[0]  # Remove " - Reddit" suffix if present
                clean_title = re.sub(r'\s*by\s*u/[^\s\]]+', '', clean_title)  # Remove author info
                clean_title = clean_title.strip()
                
                print(f"📍 Subreddit: r/{subreddit}")
                print(f"👤 Author: u/{author}")
                print(f"📰 Clean Title: {clean_title}")
                
                # Add to post list
                post_links.append({
                    'url': url,
                    'title': clean_title,
                    'author': author,
                    'subreddit': subreddit,
                    'snippet': snippet
                })
                print(f"✅ Added to post list!")
            else:
                print(f"❌ Not a Reddit post, skipping...")
            
            print("-" * 40)
        
        # Remove duplicates based on URL
        unique_links = []
        seen_urls = set()
        for post in post_links:
            if post['url'] not in seen_urls:
                unique_links.append(post)
                seen_urls.add(post['url'])
        
        unique_links = unique_links[:max_posts]
        
        # Step 3: Use LLM to select the most relevant post
        if unique_links:
            print(f"Found {len(unique_links)} Reddit posts, using LLM to select most relevant...")
            
            # Create title mapping for display
            for i, post in enumerate(unique_links, 1):
                print(f"  {i}. {post['title']}")
                print(f"     Subreddit: r/{post['subreddit']}")
                print(f"     Author: u/{post['author']}")
                print(f"     URL: {post['url']}")
            
            # Let LLM choose the best post
            selected_index = select_best_post_with_llm(search_query, unique_links)
            selected_post = unique_links[selected_index]
            
            print(f"\n🤖 LLM selected post {selected_index + 1}: {selected_post['title']}")
            print(f"    From: r/{selected_post['subreddit']}")
            print(f"    By: u/{selected_post['author']}")
            
            # Step 4: Extract content from the selected post only
            try:
                post_data = extract_reddit_post(selected_post['url'], selected_post['title'], selected_post['author'], selected_post['subreddit'])
                if post_data:
                    return [post_data]  # Return the single selected post
            except Exception as e:
                print(f"Error extracting selected post: {e}")
        
        return []
        
    except Exception as e:
        print(f"Error in Reddit search: {e}")
        return []

def extract_reddit_post(url: str, title: str, author: str, subreddit: str) -> Optional[Dict]:
    """
    Extract detailed content from a single Reddit post.
    
    Args:
        url: Post URL
        title: Post title
        author: Post author
        subreddit: Subreddit name
    
    Returns:
        Dictionary with post details and content
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract content using Reddit-specific strategies
        content_paragraphs = extract_reddit_content(soup)
        
        if not content_paragraphs:
            return None
        
        return {
            'title': title,
            'author': author,
            'subreddit': subreddit,
            'url': url,
            'content': content_paragraphs
        }
        
    except Exception as e:
        print(f"Error extracting Reddit post {url}: {e}")
        return None

def extract_reddit_content(soup: BeautifulSoup) -> List[Dict]:
    """Extract main content from a Reddit post including original post and top comments."""
    try:
        content_paragraphs = []
        
        # Remove unwanted elements
        for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
            unwanted.decompose()
        
        # Reddit-specific content extraction
        # Look for the main post content first
        post_selectors = [
            '[data-test-id="post-content"]',
            '[data-click-id="text"]',
            '.usertext-body',
            '[data-testid="post-content"]',
            'div[slot="text-body"]'
        ]
        
        main_post_content = None
        for selector in post_selectors:
            main_post_content = soup.select_one(selector)
            if main_post_content:
                break
        
        # Extract main post content
        if main_post_content:
            post_text = main_post_content.get_text(strip=True)
            if post_text and len(post_text) > 50:
                content_paragraphs.append({
                    'title': 'Original Post',
                    'content': post_text
                })
        
        # Extract comments - look for comment content
        comment_selectors = [
            '[data-testid="comment"]',
            '.Comment',
            'div[data-click-id="text"]',
            '.usertext-body'
        ]
        
        all_comments = []
        for selector in comment_selectors:
            comments = soup.select(selector)
            for comment in comments:
                comment_text = comment.get_text(strip=True)
                
                # Filter for substantial comments (avoid short replies, navigation text, etc.)
                if (len(comment_text) > 100 and 
                    not any(skip_word in comment_text.lower() for skip_word in 
                           ['permalink', 'reply', 'share', 'report', 'save', 'give award']) and
                    len(comment_text.split()) > 20):  # At least 20 words
                    
                    all_comments.append(comment_text)
                    
                    # Limit number of comments to process
                    if len(all_comments) >= 10:
                        break
            
            if all_comments:
                break  # If we found comments with one selector, don't try others
        
        # Add top comments to content
        for i, comment in enumerate(all_comments[:5], 1):  # Top 5 comments
            content_paragraphs.append({
                'title': f'Comment {i}',
                'content': comment
            })
        
        # If we didn't find specific Reddit content, try general paragraph extraction
        if not content_paragraphs:
            paragraphs = soup.find_all('p')
            for para in paragraphs:
                text = para.get_text(strip=True)
                if (len(text) > 50 and 
                    len(text.split()) > 10 and
                    not any(skip_word in text.lower() for skip_word in 
                           ['reddit', 'upvote', 'downvote', 'permalink'])):
                    
                    content_paragraphs.append({
                        'title': f"Section {len(content_paragraphs)+1}",
                        'content': text
                    })
                    
                    if len(content_paragraphs) >= 15:
                        break
        
        # Process content in chunks if we have content
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
                return content_paragraphs[:10]  # Limit to 10 sections
        
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
            
            prompt = f"""You are a helpful summarizer. Your task is to create a concise summary of the Reddit discussion provided in the source text below.

            Source text to summarize:
            {content_text}

            Instructions:
            - Write ONLY ONE SINGLE PARAGRAPH
            - NO titles, headers, or section breaks
            - NO bullet points, numbered lists, or any formatting
            - Just write one continuous paragraph of approximately 150 words
            - Include the key points, advice, and insights mentioned in the discussion
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
        
        prompt = f"""You are an expert summarizer. Your task is to create ONE comprehensive summary by combining information from multiple Reddit discussion summaries.

        Reddit Discussion Summaries:
        {combined_text}

        Instructions:
        - Write ONLY ONE SINGLE PARAGRAPH
        - NO titles, headers, or section breaks
        - NO bullet points, numbered lists, or any formatting
        - Just write one continuous paragraph of approximately 500 words
        - Combine all the discussion information into one coherent paragraph
        - Eliminate redundancy and contradictions
        - Include all important advice, insights, and recommendations from the sources
        - Use your own words to make it clear and readable
        - DO NOT add any information that is not mentioned in the source summaries
        - DO NOT use external knowledge
        - Write in plain text only - no special characters or formatting

        Output format: Just write one single paragraph of normal text."""
        
        llm_response = llm.invoke(prompt)
        
        # Post-process to remove any markdown that might have slipped through
        cleaned_content = remove_markdown_formatting(llm_response.content)
        
        return cleaned_content
        
    except Exception as e:
        # Fallback: combine summaries manually
        fallback_content = f"Combined information from {len(chunk_summaries)} discussion chunks:\n\n"
        for i, summary in enumerate(chunk_summaries, 1):
            fallback_content += f"--- Chunk {i} ---\n{summary}\n\n"
        return fallback_content

def search_reddit(query: str) -> str:
    """
    Legacy function for backward compatibility.
    Now calls the advanced search function.
    """
    try:
        posts = search_reddit_advanced(query, max_posts=10)
        if posts:
            return f"Found {len(posts)} Reddit posts for '{query}':\n\n" + json.dumps(posts, indent=2)
        else:
            return f"No Reddit posts found for '{query}'"
    except Exception as e:
        return f"Error searching Reddit: {str(e)}"

def test_reddit_connectivity():
    """Test Reddit search functionality"""
    
    # Test queries
    test_queries = [
        "How to make a website",
        "How to fix a leaky faucet", 
        "How to repair iPhone screen"
    ]
    
    # Test the exact format
    print("\n🧪 Testing Reddit Search Output Format...")
    print("=" * 50)
    
    # Test all queries from test_queries
    for test_query in test_queries:
        print(f"\n🔍 Testing: {test_query}")
        print(f"📊 Max posts: 5")
        
        try:
            import time
            start = time.time()
            posts = search_reddit_advanced(test_query, 20)
            end = time.time()
            elapsed = end - start
           
            if posts:
                print(f"\n✅ Success! Generated Reddit guide in {elapsed:.2f} seconds")
                print("\n📋 Reddit Guide Content:")
                print("=" * 60)
                
                # Since we return only one selected post, just show its content
                post = posts[0]  # Get the first (and only) post
                print(post['content'][0]['content'])
                print("=" * 60)
                
                print(f"\n📊 Content Info:")
                print(f"  - Length: {len(post['content'][0]['content'])} characters")
                print(f"  - Processing time: {elapsed:.2f} seconds")
                print(f"  - Author: u/{post['author']}")
                print(f"  - Subreddit: r/{post['subreddit']}")
                print(f"  - Source: {post['url']}")
                
            else:
                print("❌ No Reddit posts found for the test query")
                
        except Exception as e:
            print(f"❌ Error in format test: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
        
        print("-" * 50)
    
    print("=" * 50)

if __name__ == "__main__":
    test_reddit_connectivity()
