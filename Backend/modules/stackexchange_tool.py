#!/usr/bin/env python3
"""
Test module for Stack Exchange Search connectivity
Tests Stack Exchange search functionality to find relevant questions and answers
"""

import requests
import html
from typing import Dict, List, Any, Optional
from datetime import datetime

class StackExchangeAPI:
    """Stack Exchange API wrapper for searching questions and answers."""
    
    def __init__(self):
        self.base_url = "https://api.stackexchange.com/2.3"
        self.default_site = "stackoverflow"
    
    def search_questions(self, query: str, site: str = None, limit: int = 10) -> List[Dict]:
        """Search for questions on Stack Exchange sites."""
        site = site or self.default_site
        
        params = {
            'order': 'desc',
            'sort': 'relevance',
            'intitle': query,
            'site': site,
            'pagesize': limit,
            'filter': 'withbody'  # Include question body
        }
        
        response = requests.get(f"{self.base_url}/search/advanced", params=params)
        response.raise_for_status()
        
        data = response.json()
        return data.get('items', [])
    
    def get_question_answers(self, question_id: int, site: str = None) -> List[Dict]:
        """Get all answers for a specific question."""
        site = site or self.default_site
        
        params = {
            'order': 'desc',
            'sort': 'votes',
            'site': site,
            'filter': 'withbody',
            'pagesize': 100  # Get up to 100 answers
        }
        
        response = requests.get(f"{self.base_url}/questions/{question_id}/answers", params=params)
        response.raise_for_status()
        
        data = response.json()
        return data.get('items', [])
    
    def get_question_details(self, question_id: int, site: str = None) -> Optional[Dict]:
        """Get detailed information about a specific question."""
        site = site or self.default_site
        
        params = {
            'site': site,
            'filter': 'withbody'
        }
        
        response = requests.get(f"{self.base_url}/questions/{question_id}", params=params)
        response.raise_for_status()
        
        data = response.json()
        items = data.get('items', [])
        return items[0] if items else None
    
    def clean_html(self, text: str) -> str:
        """Remove HTML tags and decode HTML entities."""
        if not text:
            return ""
        
        # Remove HTML tags (basic cleanup)
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text
    
    def format_timestamp(self, timestamp: int) -> str:
        """Convert Unix timestamp to readable date."""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def search_stack_exchange(query: str, site: str = "stackoverflow", limit: int = 5) -> str:
    """
    Search Stack Exchange for questions and their answers.
    
    Args:
        query: Search term (e.g., "python list comprehension", "javascript async await")
        site: Stack Exchange site (stackoverflow, superuser, serverfault, etc.)
        limit: Number of questions to return (default: 5)
    """
    try:
        api = StackExchangeAPI()
        
        # Search for questions
        questions = api.search_questions(query, site, limit)
        
        if not questions:
            return f"No questions found for '{query}' on {site}."
        
        detailed_results = []
        
        for i, question in enumerate(questions):
            question_id = question.get('question_id')
            title = question.get('title', 'Unknown Title')
            
            result_text = f"#{i+1} - Question ID: {question_id}\n"
            result_text += f"Title: {title}\n"
            result_text += f"Site: {site}\n"
            result_text += f"Score: {question.get('score', 0)}\n"
            result_text += f"Views: {question.get('view_count', 0)}\n"
            result_text += f"Asked: {api.format_timestamp(question.get('creation_date', 0))}\n"
            
            # Add tags
            tags = question.get('tags', [])
            if tags:
                result_text += f"Tags: {', '.join(tags)}\n"
            
            # Add question body preview
            body = api.clean_html(question.get('body', ''))
            if body:
                body_preview = body[:200] + "..." if len(body) > 200 else body
                result_text += f"Question: {body_preview}\n"
            
            # Check if question is answered
            answer_count = question.get('answer_count', 0)
            is_answered = question.get('is_answered', False)
            result_text += f"Answers: {answer_count} ({'Accepted' if is_answered else 'None accepted'})\n"
            
            detailed_results.append(result_text)
        
        return f"Found {len(questions)} questions for '{query}' on {site}:\n\n" + "\n\n".join(detailed_results)
        
    except Exception as e:
        return f"Error searching Stack Exchange: {str(e)}"


def get_stack_exchange_answers(question_id: int, site: str = "stackoverflow") -> str:
    """
    Get the complete question details and all answers for a Stack Exchange question.
    
    Args:
        question_id: The Stack Exchange question ID
        site: Stack Exchange site (default: stackoverflow)
    """
    try:
        api = StackExchangeAPI()
        
        # Get question details
        question = api.get_question_details(question_id, site)
        if not question:
            return f"Could not retrieve question {question_id} from {site}"
        
        # Get all answers
        answers = api.get_question_answers(question_id, site)
        
        # Format the result
        result = f"Question: {question.get('title', 'Unknown Title')}\n"
        result += f"Site: {site}\n"
        result += f"Question ID: {question_id}\n"
        result += f"Score: {question.get('score', 0)}\n"
        result += f"Views: {question.get('view_count', 0)}\n"
        result += f"Asked: {api.format_timestamp(question.get('creation_date', 0))}\n"
        
        # Add tags
        tags = question.get('tags', [])
        if tags:
            result += f"Tags: {', '.join(tags)}\n"
        
        # Add question body
        question_body = api.clean_html(question.get('body', ''))
        result += f"\nQuestion Body:\n{question_body}\n"
        
        # Add answers
        if answers:
            result += f"\n--- ANSWERS ({len(answers)} total) ---\n"
            
            for i, answer in enumerate(answers):
                result += f"\nAnswer #{i+1}:\n"
                result += f"Score: {answer.get('score', 0)}\n"
                result += f"Accepted: {'Yes' if answer.get('is_accepted', False) else 'No'}\n"
                result += f"Posted: {api.format_timestamp(answer.get('creation_date', 0))}\n"
                
                # Add answer body
                answer_body = api.clean_html(answer.get('body', ''))
                result += f"Answer:\n{answer_body}\n"
                
                # Add separator between answers
                if i < len(answers) - 1:
                    result += "\n" + "-" * 50 + "\n"
        else:
            result += "\nNo answers found for this question."
        
        return result
        
    except Exception as e:
        return f"Error fetching question {question_id}: {str(e)}"

# Additional utility function for common sites

def search_stack_exchange_all_sites(query: str, limit: int = 3) -> str:
    """
    Search across multiple popular Stack Exchange sites.
    
    Args:
        query: Search term
        limit: Number of questions per site
    """
    popular_sites = [
        "stackoverflow",
        "superuser", 
        "serverfault",
        "askubuntu",
        "unix"
    ]
    
    all_results = []
    
    for site in popular_sites:
        try:
            result = search_stack_exchange(query, site, limit)
            if "No questions found" not in result:
                all_results.append(f"=== {site.upper()} ===\n{result}")
        except:
            continue
    
    if not all_results:
        return f"No questions found for '{query}' across Stack Exchange sites."
    
    return "\n\n".join(all_results)

def test_search_stack_exchange():
    """Test the basic search functionality."""
    print("=" * 60)
    print("TEST 1: Basic Search")
    print("=" * 60)
    
    # Test search
    query = "python list comprehension"
    print(f"Searching for: '{query}'\n")
    
    result = search_stack_exchange(query, limit=3)
    print(result)
    print("\n")

def test_get_answers():
    """Test getting detailed answers for a specific question."""
    print("=" * 60)
    print("TEST 2: Get Question with All Answers")
    print("=" * 60)
    
    # Use a well-known Stack Overflow question ID
    # This is a popular question about Python list comprehensions
    question_id = 394809  # "How to get the last element of a list in Python?"
    
    print(f"Getting all answers for question ID: {question_id}\n")
    
    result = get_stack_exchange_answers(question_id)
    print(result)
    print("\n")

def test_different_sites():
    """Test searching on different Stack Exchange sites."""
    print("=" * 60)
    print("TEST 3: Different Sites")
    print("=" * 60)
    
    # Test on different sites
    queries_and_sites = [
        ("linux terminal commands", "unix"),
        ("windows registry", "superuser"),
        ("nginx configuration", "serverfault")
    ]
    
    for query, site in queries_and_sites:
        print(f"Searching '{query}' on {site}:")
        result = search_stack_exchange(query, site=site, limit=2)
        print(result[:500] + "..." if len(result) > 500 else result)
        print("\n" + "-" * 40 + "\n")

def test_multi_site_search():
    """Test searching across multiple sites."""
    print("=" * 60)
    print("TEST 4: Multi-Site Search")
    print("=" * 60)
    
    query = "docker container"
    print(f"Searching '{query}' across multiple sites:\n")
    
    result = search_stack_exchange_all_sites(query, limit=2)
    print(result[:1000] + "..." if len(result) > 1000 else result)
    print("\n")

def interactive_test():
    """Interactive test allowing user input."""
    print("=" * 60)
    print("INTERACTIVE TEST")
    print("=" * 60)
    
    while True:
        print("\nChoose an option:")
        print("1. Search questions")
        print("2. Get question with answers")
        print("3. Multi-site search")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            query = input("Enter search query: ").strip()
            site = input("Enter site (or press Enter for stackoverflow): ").strip() or "stackoverflow"
            limit = input("Enter number of results (or press Enter for 5): ").strip()
            limit = int(limit) if limit.isdigit() else 5
            
            print(f"\nSearching for '{query}' on {site}...")
            result = search_stack_exchange(query, site, limit)
            print(result)
            
        elif choice == "2":
            question_id = input("Enter question ID: ").strip()
            site = input("Enter site (or press Enter for stackoverflow): ").strip() or "stackoverflow"
            
            if question_id.isdigit():
                print(f"\nGetting answers for question {question_id}...")
                result = get_stack_exchange_answers(int(question_id), site)
                print(result)
            else:
                print("Invalid question ID!")
                
        elif choice == "3":
            query = input("Enter search query: ").strip()
            limit = input("Enter results per site (or press Enter for 3): ").strip()
            limit = int(limit) if limit.isdigit() else 3
            
            print(f"\nSearching '{query}' across multiple sites...")
            result = search_stack_exchange_all_sites(query, limit)
            print(result)
            
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice!")

def main():
    """Run all tests."""
    print("Stack Exchange Searcher Test Suite")
    print("=" * 60)
    
    # Import the functions (assuming they're in the same file or imported)
    # If running separately, you'll need to import from your module
    
    try:
        # Run automated tests
        test_search_stack_exchange()
        test_get_answers()
        test_different_sites()
        test_multi_site_search()
        
        # Ask if user wants interactive test
        print("=" * 60)
        run_interactive = input("Run interactive test? (y/n): ").strip().lower()
        if run_interactive == 'y':
            interactive_test()
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        print("Make sure you have internet connection and requests library installed.")
        print("Install with: pip install requests")

if __name__ == "__main__":
    main()

# Example usage scenarios:
"""
# Basic search
result = search_stack_exchange("python async await", limit=3)
print(result)

# Get specific question with all answers
answers = get_stack_exchange_answers(11227809)  # Popular async/await question
print(answers)

# Search on different site
result = search_stack_exchange("linux permissions", site="unix", limit=3)
print(result)

# Multi-site search
result = search_stack_exchange_all_sites("docker deployment", limit=2)
print(result)
"""
