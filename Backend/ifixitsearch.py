import requests
import json

class iFixitAPI:
    def __init__(self):
        self.base_url = "https://www.ifixit.com/api/2.0"
        self.headers = {
            'User-Agent': 'YourAppName/1.0'  # Replace with your app name
        }
    
    def search_guides(self, query, limit=10):
        """
        Search for repair guides by keyword
        
        Args:
            query (str): Search term (e.g., "iPhone screen", "MacBook battery")
            limit (int): Number of results to return (default 10)
        
        Returns:
            dict: Search results from iFixit API
        """
        url = f"{self.base_url}/search/{query}"
        params = {
            'limit': limit
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error searching guides: {e}")
            return None
    
    def get_guide_details(self, guide_id):
        """
        Get detailed information about a specific guide
        
        Args:
            guide_id (int): The ID of the guide
        
        Returns:
            dict: Guide details including steps, tools, parts needed
        """
        url = f"{self.base_url}/guides/{guide_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting guide details: {e}")
            return None
    
    def search_by_device(self, device_name):
        """
        Search for guides specific to a device
        
        Args:
            device_name (str): Device name (e.g., "iPhone 12", "Samsung Galaxy S21")
        
        Returns:
            dict: Search results for the device
        """
        url = f"{self.base_url}/categories/{device_name}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error searching by device: {e}")
            return None

# Example usage
def main():
    api = iFixitAPI()
    
    # Search for iPhone screen repair guides
    print("Custom search running...")
    results = api.search_guides("Framework Laptop 12 cpu upgrade, mainboard replacement", limit=5)
    
    if results:
        print(f"Found {len(results.get('results', []))} results:")
        for guide in results.get('results', []):
            print(f"- {guide.get('title', 'Unknown title')}")
            print(f"  ID: {guide.get('guideid')}")
            print(f"  Difficulty: {guide.get('difficulty', 'Unknown')}")
            print(f"  URL: {guide.get('url', '')}")
            print()
    
    # Get detailed information about a specific guide
    if results and results.get('results'):
        first_guide_id = results['results'][0].get('guideid')
        if first_guide_id:
            print(f"\nGetting details for guide ID: {first_guide_id}")
            guide_details = api.get_guide_details(first_guide_id)
            
            if guide_details:
                print(f"Title: {guide_details.get('title')}")
                print(f"Introduction: {guide_details.get('introduction', '')[:200]}...")
                print(f"Number of steps: {len(guide_details.get('steps', []))}")
                print(f"Tools needed: {len(guide_details.get('tools', []))}")
                print(f"Parts needed: {len(guide_details.get('parts', []))}")

# Advanced search with filtering
def advanced_search_example():
    api = iFixitAPI()
    
    # Search and filter results
    search_term = "MacBook battery replacement"
    results = api.search_guides(search_term, limit=20)
    
    if results:
        guides = results.get('results', [])
        
        # Filter by difficulty level
        easy_guides = [g for g in guides if g.get('difficulty', '').lower() in ['easy', 'moderate']]
        
        print(f"Found {len(easy_guides)} easy/moderate difficulty guides:")
        for guide in easy_guides:
            print(f"- {guide.get('title')}")
            print(f"  Difficulty: {guide.get('difficulty')}")
            print(f"  Time required: {guide.get('time_required', 'Unknown')}")
            print()

# Search for specific issues
def search_common_fixes():
    api = iFixitAPI()
    
    common_issues = [
        "cracked screen",
        "battery replacement", 
        "charging port repair",
        "water damage",
        "speaker not working"
    ]
    
    for issue in common_issues:
        print(f"\n=== {issue.upper()} ===")
        results = api.search_guides(issue, limit=3)
        
        if results:
            for guide in results.get('results', []):
                print(f"• {guide.get('title')}")
                print(f"  Device: {guide.get('category', 'Unknown')}")
                print(f"  Difficulty: {guide.get('difficulty', 'Unknown')}")

if __name__ == "__main__":
    main()
    print("\n" + "="*50)
    advanced_search_example()
    print("\n" + "="*50)
    search_common_fixes()