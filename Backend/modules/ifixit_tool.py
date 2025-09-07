#!/usr/bin/env python3
"""
Test module for iFixit using LangChain document loader
Tests the IFixitLoader from langchain_community.document_loaders
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from typing import List, Dict, Optional
from langchain_community.document_loaders import IFixitLoader

def remove_markdown_formatting(text: str) -> str:
    """
    Remove all markdown formatting from text to ensure plain text output.
    """
    if not text:
        return text
    
    import re
    
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown bold/italic
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)_', r'\1', text)
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

def select_best_guide_with_llm(search_query: str, guides: List[Dict]) -> int:
    """
    Use LLM to select the most relevant iFixit guide from the list.
    
    Args:
        search_query: The original search query
        guides: List of guide dictionaries with 'title' and 'url'
    
    Returns:
        Index of the selected guide (0-based)
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
        for i, guide in enumerate(guides, 1):
            title_mapping[i] = f"{guide['title']} - {guide.get('device', 'Unknown Device')}"
        
        # Create the mapping text for the prompt
        mapping_text = "\n".join([f"{num}: {title}" for num, title in title_mapping.items()])
        
        prompt = f"""You are an expert at selecting the most relevant iFixit repair guide for a given search query.

        Search Query: "{search_query}"

        Available iFixit Guides:
        {mapping_text}

        Instructions:
        - Analyze which iFixit guide title is most relevant to the search query
        - Consider which guide would best help someone accomplish the repair task described in the search query
        - Prefer comprehensive guides, step-by-step tutorials, and detailed repair instructions
        - Consider the device match if mentioned
        - Return ONLY the number (1, 2, 3, etc.) of the most relevant guide
        - Do not include any explanation or additional text
        - Just return the single number

        Most relevant guide number:"""
        
        llm_response = llm.invoke(prompt)
        
        # Extract the number from the response
        response_text = llm_response.content.strip()
        
        # Try to extract the first number from the response
        import re
        numbers = re.findall(r'\d+', response_text)
        if numbers:
            selected_num = int(numbers[0])
            # Convert to 0-based index and validate
            if 1 <= selected_num <= len(guides):
                return selected_num - 1  # Convert to 0-based index
        
        # Fallback: return first guide if no valid selection
        return 0
        
    except Exception as e:
        # Fallback: return first guide if LLM fails
        return 0

def search_ifixit_advanced(search_query: str, max_guides: int = 10) -> List[Dict]:
    """
    Advanced iFixit search using LangChain IFixitLoader.
    
    Args:
        search_query: Search term (e.g., "iPhone screen replacement")
        max_guides: Maximum number of guides to process
    
    Returns:
        List of guide dictionaries with title, url, and content
    """
    try:
        print(f"🔍 iFixit search for: '{search_query}'")
        print("=" * 60)
        
        # Use IFixitLoader to search for suggestions
        print("📡 Loading iFixit suggestions...")
        documents = IFixitLoader.load_suggestions(search_query)
        
        if not documents:
            print("❌ No iFixit guides found")
            return []
        
        print(f"✅ Found {len(documents)} iFixit guides")
        
        # Process documents into guide format
        guides = []
        for i, doc in enumerate(documents):
            title = doc.metadata.get('title', f'Guide {i+1}')
            url = doc.metadata.get('source', '')
            
            # Extract device from URL if possible
            device = "Unknown Device"
            if '/Device/' in url:
                device = url.split('/Device/')[-1].replace('_', ' ').title()
            elif '/Teardown/' in url:
                device = url.split('/Teardown/')[-1].split('/')[0].replace('+', ' ').title()
            
            guides.append({
                'title': title,
                'url': url,
                'device': device,
                'content': doc.page_content
            })
            
            print(f"📝 Guide {i+1}: {title}")
            print(f"   Device: {device}")
            print(f"   URL: {url}")
            print("-" * 40)
        
        # Limit to max_guides
        guides = guides[:max_guides]
        
        # Use LLM to select the most relevant guide
        if len(guides) > 1:
            print(f"\n🤖 Using LLM to select most relevant guide from {len(guides)} options...")
            selected_index = select_best_guide_with_llm(search_query, guides)
            selected_guide = guides[selected_index]
            
            print(f"✅ LLM selected guide {selected_index + 1}: {selected_guide['title']}")
            print(f"   Device: {selected_guide['device']}")
            
            # Process the selected guide content
            try:
                guide_data = process_guide_content(selected_guide)
                if guide_data:
                    return [guide_data]  # Return the single selected guide
            except Exception as e:
                print(f"Error processing selected guide: {e}")
        elif len(guides) == 1:
            # Only one guide found, process it directly
            print(f"\n📋 Only one guide found, processing directly...")
            guide_data = process_guide_content(guides[0])
            if guide_data:
                return [guide_data]
        
        return []
        
    except Exception as e:
        print(f"Error in iFixit search: {e}")
        return []

def process_guide_content(guide: Dict) -> Optional[Dict]:
    """
    Process guide content using LLM to create a comprehensive summary.
    
    Args:
        guide: Guide dictionary with title, url, device, and content
    
    Returns:
        Dictionary with processed guide content
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
        
        content = guide['content']
        
        # Print total content statistics
        total_chars = len(content)
        total_words = len(content.split())
        print(f"📊 Total content: {total_chars} characters, {total_words} words")
        
        # Single LLM call to process the entire content
        prompt = f"""You are an expert repair guide summarizer. Your task is to create a comprehensive repair guide summary from the iFixit content below.

        iFixit Repair Guide Content:
        {content}

        Instructions:
        - Write ONLY ONE SINGLE PARAGRAPH
        - NO titles, headers, or section breaks
        - NO bullet points, numbered lists, or any formatting
        - Write EXACTLY 500 words or fewer - this is a strict limit
        - Include all important repair steps, tools, and safety considerations
        - Use your own words to make it clear and readable
        - DO NOT add any information that is not mentioned in the source content
        - DO NOT use external knowledge
        - Write in plain text only - no special characters or formatting
        - Count your words carefully to stay within the 500-word limit

        Output format: Just write one single paragraph of normal text with maximum 500 words."""
        
        print("🤖 Processing content with single LLM call...")
        llm_response = llm.invoke(prompt)
        
        # Post-process to remove any markdown that might have slipped through
        cleaned_content = remove_markdown_formatting(llm_response.content)
        
        # Ensure word count is within 500 words
        word_count = len(cleaned_content.split())
        if word_count > 500:
            # Truncate to 500 words if exceeded
            words = cleaned_content.split()[:500]
            cleaned_content = ' '.join(words)
            print(f"⚠️  Summary exceeded 500 words ({word_count}), truncated to 500 words")
        else:
            print(f"✅ Final summary: {word_count} words (within 500 limit)")
        
        return {
            'title': guide['title'],
            'device': guide['device'],
            'url': guide['url'],
            'content': [{
                'title': 'LLM Processed Summary',
                'content': cleaned_content
            }]
        }
        
    except Exception as e:
        print(f"Error processing guide content: {e}")
        # Fallback to raw content if LLM fails
        return {
            'title': guide['title'],
            'device': guide['device'],
            'url': guide['url'],
            'content': [{
                'title': 'Raw Guide Content',
                'content': content[:2000]  # Limit to 2000 characters
            }]
        }

def split_content_into_chunks(content: str) -> List[str]:
    """Split content into manageable chunks for processing."""
    # Split by double newlines or section markers
    chunks = []
    
    # Try to split by sections (##, ###, etc.)
    import re
    sections = re.split(r'\n#{2,}\s+', content)
    
    for section in sections:
        if section.strip() and len(section.strip()) > 50:
            chunks.append(section.strip())
    
    # If no sections found, split by paragraphs
    if not chunks:
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip() and len(para.strip()) > 50:
                chunks.append(para.strip())
    
    return chunks

async def process_content_chunks_async(content_chunks: List[List[str]]) -> List[str]:
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
    
    async def process_chunk(chunk: List[str]) -> str:
        """Process a single chunk of content."""
        try:
            content_text = "\n\n".join([f"Section {i+1}: {section}" for i, section in enumerate(chunk)])
            
            # Print chunk statistics
            chunk_chars = len(content_text)
            chunk_words = len(content_text.split())
            print(f"   📊 Chunk stats: {chunk_chars} characters, {chunk_words} words")
            
            prompt = f"""You are a helpful summarizer. Your task is to create a concise summary of the repair information provided in the source text below.

            Source text to summarize:
            {content_text}

            Instructions:
            - Write ONLY ONE SINGLE PARAGRAPH
            - NO titles, headers, or section breaks
            - NO bullet points, numbered lists, or any formatting
            - Just write one continuous paragraph of approximately 150 words
            - Include the key repair steps, tools, and important details mentioned in the source
            - Use your own words to make it clear and readable
            - DO NOT add any information that is not mentioned in the source text
            - Write in plain text only - no special characters or formatting

            Output format: Just write one single paragraph of normal text."""
            
            # Since ChatOllama doesn't support async directly, we'll run it in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: llm.invoke(prompt))
            
            # Post-process to remove any markdown that might have slipped through
            cleaned_content = remove_markdown_formatting(response.content)
            
            # Print output statistics
            output_chars = len(cleaned_content)
            output_words = len(cleaned_content.split())
            print(f"   ✅ Chunk output: {output_chars} characters, {output_words} words")
            
            return cleaned_content
            
        except Exception as e:
            return f"Error processing chunk: {str(e)}"
    
    # Process all chunks concurrently
    tasks = [process_chunk(chunk) for chunk in content_chunks]
    chunk_summaries = await asyncio.gather(*tasks)
    
    return chunk_summaries

def combine_chunk_summaries(chunk_summaries: List[str]) -> str:
    """Combine multiple chunk summaries into one comprehensive summary using LLM with iterative shortening."""
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
        
        # Initial combination prompt
        initial_prompt = f"""You are an expert repair guide summarizer. Your task is to create ONE comprehensive repair guide by combining information from multiple chunk summaries.

        Chunk Summaries:
        {combined_text}

        Instructions:
        - Write ONLY ONE SINGLE PARAGRAPH
        - NO titles, headers, or section breaks
        - NO bullet points, numbered lists, or any formatting
        - Write EXACTLY 500 words or fewer - this is a strict limit
        - Combine all the chunk information into one coherent repair guide
        - Eliminate redundancy and contradictions
        - Include all important repair steps, tools, and safety considerations from the sources
        - Use your own words to make it clear and readable
        - DO NOT add any information that is not mentioned in the source chunks
        - DO NOT use external knowledge
        - Write in plain text only - no special characters or formatting
        - Count your words carefully to stay within the 500-word limit

        Output format: Just write one single paragraph of normal text with maximum 500 words."""
        
        # Get initial response
        llm_response = llm.invoke(initial_prompt)
        current_content = remove_markdown_formatting(llm_response.content)
        
        # Iterative shortening loop
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        while len(current_content.split()) > 500 and iteration < max_iterations:
            iteration += 1
            word_count = len(current_content.split())
            print(f"🔄 Iteration {iteration}: Content is {word_count} words, shortening...")
            
            # Create shortening prompt
            shorten_prompt = f"""You are an expert at making repair guides more concise. Your task is to shorten the following repair guide while keeping all essential information.

        Current Repair Guide ({word_count} words):
        {current_content}

        Instructions:
        - Write ONLY ONE SINGLE PARAGRAPH
        - NO titles, headers, or section breaks
        - NO bullet points, numbered lists, or any formatting
        - Make it significantly shorter while keeping all important repair steps, tools, and safety information
        - Remove redundant information and combine similar points
        - Keep the most critical repair instructions
        - Use your own words to make it clear and readable
        - Write in plain text only - no special characters or formatting
        - Target approximately {max(300, word_count - 100)} words

        Output format: Just write one single paragraph of normal text."""
            
            # Get shortened response
            shorten_response = llm.invoke(shorten_prompt)
            current_content = remove_markdown_formatting(shorten_response.content)
            
            new_word_count = len(current_content.split())
            print(f"   ✅ Shortened to {new_word_count} words")
        
        # Final word count check
        final_word_count = len(current_content.split())
        if final_word_count > 500:
            # Final truncation if still over limit
            words = current_content.split()[:500]
            current_content = ' '.join(words)
            print(f"⚠️  Final truncation: {final_word_count} words → 500 words")
        else:
            print(f"✅ Final content: {final_word_count} words (within 500 limit)")
        
        return current_content
        
    except Exception as e:
        # Fallback: combine summaries manually
        fallback_content = f"Combined repair information from {len(chunk_summaries)} sections:\n\n"
        for i, summary in enumerate(chunk_summaries, 1):
            fallback_content += f"--- Section {i} ---\n{summary}\n\n"
        
        # Ensure fallback content is also within 500 words
        word_count = len(fallback_content.split())
        if word_count > 500:
            words = fallback_content.split()[:500]
            fallback_content = ' '.join(words)
            print(f"⚠️  Fallback summary exceeded 500 words ({word_count}), truncated to 500 words")
        
        return fallback_content

def search_ifixit(query: str) -> str:
    """
    Legacy function for backward compatibility.
    Now calls the advanced search function.
    """
    try:
        guides = search_ifixit_advanced(query, max_guides=10)
        if guides:
            return f"Found {len(guides)} iFixit guides for '{query}':\n\n" + str(guides)
        else:
            return f"No iFixit guides found for '{query}'"
    except Exception as e:
        return f"Error searching iFixit: {str(e)}"

def test_ifixit_connectivity():
    """Test iFixit search functionality"""
    
    # Test queries - specific device models for better results
    test_queries = [
        "iPhone 12 screen replacement",
        "MacBook Pro 13 inch battery replacement",
        "Samsung Galaxy S21 screen repair"
    ]
        
    # Test the exact format
    print("\n🧪 Testing iFixit Search Output Format...")
    print("=" * 50)
    
    # Test all queries from test_queries
    for test_query in test_queries:
        print(f"\n🔍 Testing: {test_query}")
        print(f"📊 Max guides: 10")
        
        try:
            import time
            start = time.time()
            guides = search_ifixit_advanced(test_query, 10)
            end = time.time()
            elapsed = end - start
            
            if guides:
                print(f"\n✅ Success! Generated iFixit guide in {elapsed:.2f} seconds")
                print("\n📋 iFixit Guide Content:")
                print("=" * 60)
                
                # Since we return only one selected guide, just show its content
                guide = guides[0]  # Get the first (and only) guide
                print(guide['content'][0]['content'])
                print("=" * 60)
                
                print(f"\n📊 Content Info:")
                print(f"  - Length: {len(guide['content'][0]['content'])} characters")
                print(f"  - Processing time: {elapsed:.2f} seconds")
                print(f"  - Device: {guide['device']}")
                print(f"  - Source: {guide['url']}")
                                
            else:
                print("❌ No iFixit guides found for the test query")
                    
        except Exception as e:
            print(f"❌ Error in format test: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
        
        print("-" * 50)
    
    print("=" * 50)

if __name__ == "__main__":
    test_ifixit_connectivity()
