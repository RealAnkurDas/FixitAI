#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tools module for MyFixit dataset interface and utility functions
"""

import json
import itertools
import requests
from typing import List, Dict, Optional, Any
from pathlib import Path
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

class MyFixitDataset:
    """Interface for querying MyFixit dataset"""

    def __init__(self, dataset_path: str = "MyFixit-Dataset/jsons"):
        self.dataset_path = Path(dataset_path)
        self.available_files = []
        self._scan_dataset()

    def _scan_dataset(self):
        """Scan available JSON files in dataset directory"""
        if self.dataset_path.exists():
            self.available_files = list(self.dataset_path.glob("*.json"))
        else:
            print(f"Warning: Dataset path {self.dataset_path} not found")

    def load_json_file(self, filename: str) -> List[Dict]:
        """Load a specific JSON file from dataset"""
        file_path = self.dataset_path / filename
        if not file_path.exists():
            available = [f.name for f in self.available_files]
            raise FileNotFoundError(f"File {filename} not found. Available files: {available}")

        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.startswith('['):
                    data = json.loads(content)
                else:
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file {filename}: {e}")
            return []
        return data

    def query_manuals(self, filename: str, device: Optional[str] = None, part: Optional[str] = None) -> List[Dict]:
        """Query manuals based on device and part"""
        data = self.load_json_file(filename)
        filtered_manuals = []
        for manual in data:
            if device and device.lower() not in [a.lower() for a in manual.get('Ancestors', [])]:
                continue
            if part and part.lower() not in manual.get('Title', '').lower():
                continue
            filtered_manuals.append(manual)
        return filtered_manuals

    def search_by_keywords(self, filename: str, keywords: List[str]) -> List[Dict]:
        """Search manuals by keywords"""
        data = self.load_json_file(filename)
        results = []
        for manual in data:
            title = manual.get('Title', '').lower()
            if any(keyword.lower() in title for keyword in keywords):
                results.append(manual)
        return results

    def get_manual_summary(self, manual: Dict) -> Dict[str, Any]:
        """Get a summary of a manual"""
        return {
            'title': manual.get('Title', 'Unknown'),
            'device': manual.get('Ancestors', []),
            'num_steps': len(manual.get('Steps', [])),
            'tools_required': len(manual.get('Toolbox', [])),
            'difficulty': manual.get('Difficulty', 'Unknown')
        }

@tool
def search_repair_manuals(device: Optional[str] = None, part: Optional[str] = None, keywords: Optional[str] = None) -> str:
    """
    Search for repair manuals.
    Priority:
    1. Local MyFixit dataset
    2. iFixit.com search
    3. General web search
    """
    dataset = MyFixitDataset()
    if not dataset.available_files:
        return "No dataset files found locally."

    filename = dataset.available_files[0].name
    keyword_list = [k.strip() for k in keywords.split(',')] if keywords else None

    # 1️⃣ Local dataset search
    if keyword_list:
        results = dataset.search_by_keywords(filename, keyword_list)
    else:
        results = dataset.query_manuals(filename, device=device, part=part)

    if results:
        summaries = [dataset.get_manual_summary(m) for m in results[:3]]
        return f"Found {len(results)} manuals locally. Top results:\n\n" + "\n\n".join(
            [f"Title: {s['title']}\nDevice: {', '.join(s['device'])}" for s in summaries]
        )

    # Build search terms for fallback searches
    search_terms = []
    if device:
        search_terms.append(device)
    if part:
        search_terms.append(part)
    if keyword_list:
        search_terms.extend(keyword_list)

    if not search_terms:
        return "No search terms provided for online search."

    # 2️⃣ Search iFixit directly first
    query = "site:ifixit.com " + " ".join(search_terms)
    search_tool = DuckDuckGoSearchRun()
    ifixit_results = search_tool.run(query)
    if ifixit_results and "ifixit" in ifixit_results.lower():
        return f"No local results found. Here are some iFixit repair guides for '{' '.join(search_terms)}':\n\n{ifixit_results}"

    # 3️⃣ Fallback to general search
    general_query = "repair manual " + " ".join(search_terms)
    web_results = search_tool.run(general_query)
    return f"No local or iFixit results found. Here are some general online search results for '{general_query}':\n\n{web_results}"


@tool
def get_repair_steps(manual_title: str) -> str:
    """
    Get repair steps for a manual.

    Args:
        manual_title: The title of the manual.
    """
    dataset = MyFixitDataset()
    if not dataset.available_files:
        return "No dataset files found."

    filename = dataset.available_files[0].name
    data = dataset.load_json_file(filename)

    manual = next((m for m in data if manual_title.lower() in m.get('Title', '').lower()), None)

    if not manual:
        return f"Manual '{manual_title}' not found."

    steps = manual.get('Steps', [])
    tools = manual.get('Toolbox', [])

    result = f"Repair Guide: {manual.get('Title', 'Unknown')}\n"
    result += f"Tools: {', '.join(tools)}\n\nSteps:\n"
    result += "\n".join([f"{i + 1}. {s.get('Text', '')}" for i, s in enumerate(steps)])

    return result
IFIXIT_API_BASE = "https://www.ifixit.com/api/2.0"

@tool
def search_ifixit_guides(query: str) -> str:
    """
    Search the iFixit API for repair guides by keyword, filtering to relevant devices/problems.
    Args:
        query: Search terms, e.g., "iPhone 12 screen replacement"
    Returns:
        String summary of top relevant guides with guideid for fetching details.
    """
    try:
        import requests
        
        # Define the iFixit API base URL
        IFIXIT_API_BASE = "https://www.ifixit.com/api/2.0"
        
        # Clean and prepare search terms
        query = query.strip()
        if not query:
            return "Empty search query provided."
        
        # Split query into keywords for better matching
        keywords = [k.strip().lower() for k in query.split() if k.strip() and len(k.strip()) > 2]
        
        # Make API request with proper parameters
        params = {
            "query": query,
            "limit": 50  # Get more results to filter from
        }
        
        print(f"Searching iFixit for: '{query}'")  # Debug output
        resp = requests.get(f"{IFIXIT_API_BASE}/guides", params=params, timeout=10)
        resp.raise_for_status()
        
        data = resp.json()
        print(f"API returned: {type(data)}")  # Debug output
        
        # Handle different API response formats
        if isinstance(data, list):
            guides = data
        elif isinstance(data, dict):
            guides = data.get("guides", data.get("results", []))
        else:
            return f"Unexpected API response format for '{query}'. Response type: {type(data)}"
        
        if not guides:
            return f"No guides found for '{query}'. API returned empty results."
        
        print(f"Found {len(guides)} total guides")  # Debug output
        
        # Enhanced filtering with more flexible matching
        filtered = []
        for g in guides:
            if not isinstance(g, dict):
                continue
            
            title = g.get("title", "").lower()
            device = g.get("device", "").lower()
            summary = g.get("summary", "").lower()
            category = g.get("category", "").lower()
            
            # Check if any keyword matches in title, device, summary, or category
            match_found = False
            for kw in keywords:
                if (kw in title or kw in device or kw in summary or kw in category):
                    match_found = True
                    break
            
            # Also check for partial matches and common variations
            if not match_found:
                search_text = f"{title} {device} {summary} {category}"
                # Handle common device name variations
                device_variants = {
                    'iphone': ['iphone', 'apple phone'],
                    'samsung': ['samsung', 'galaxy'],
                    'pixel': ['pixel', 'google pixel'],
                    'macbook': ['macbook', 'mac book', 'apple laptop'],
                    'ipad': ['ipad', 'apple tablet']
                }
                
                for kw in keywords:
                    if kw in device_variants:
                        for variant in device_variants[kw]:
                            if variant in search_text:
                                match_found = True
                                break
                    if match_found:
                        break
            
            if match_found:
                filtered.append(g)
        
        if not filtered:
            # If no filtered results, show what we got for debugging
            sample_titles = [g.get("title", "No title") for g in guides[:3]]
            return f"No relevant guides found for '{query}'. Sample of available guides: {sample_titles}"
        
        print(f"Filtered to {len(filtered)} relevant guides")  # Debug output
        
        # Enhanced relevance scoring
        def relevance_score(guide):
            score = 0
            title = guide.get("title", "").lower()
            device = guide.get("device", "").lower()
            summary = guide.get("summary", "").lower()
            
            for kw in keywords:
                # Higher score for exact matches in title and device
                if kw in title:
                    score += 5
                if kw in device:
                    score += 4
                if kw in summary:
                    score += 2
                
                # Bonus for multiple keyword matches
                keyword_count = sum(1 for k in keywords if k in title or k in device)
                score += keyword_count * 2
            
            return -score  # Negative for descending sort
        
        filtered.sort(key=relevance_score)
        
        # Build enhanced output
        top_results = []
        for i, g in enumerate(filtered[:7]):  # Show top 7 results
            difficulty = g.get("difficulty", "Unknown")
            time_required = g.get("time_required", "")
            tools_required = g.get("tools", [])
            
            result = (
                f"#{i+1} - GuideID: {g.get('guideid')}\n"
                f"Title: {g.get('title')}\n"
                f"Device: {g.get('device')}\n"
                f"Difficulty: {difficulty}"
            )
            
            if time_required:
                result += f"\nTime Required: {time_required}"
            
            if tools_required and isinstance(tools_required, list):
                tools_str = ", ".join(tools_required[:3])  # Show first 3 tools
                if tools_str:
                    result += f"\nTools Needed: {tools_str}"
            
            summary = g.get('summary', '').strip()
            if summary:
                result += f"\nSummary: {summary[:150]}{'...' if len(summary) > 150 else ''}"
            
            top_results.append(result)
        
        return f"Found {len(filtered)} relevant iFixit guides for '{query}':\n\n" + "\n\n".join(top_results)
        
    except requests.exceptions.RequestException as e:
        return f"Network error searching iFixit: {str(e)}"
    except requests.exceptions.Timeout:
        return "Request to iFixit API timed out. Please try again."
    except Exception as e:
        return f"Error searching iFixit: {str(e)}"



@tool
def get_ifixit_guide_steps(guideid: int) -> str:
    """
    Fetch full guide details (steps, tools, difficulty) from iFixit.
    """
    try:
        resp = requests.get(f"{IFIXIT_API_BASE}/guides/{guideid}")
        resp.raise_for_status()
        guide = resp.json()

        # ✅ Ensure it's a dict before using .get()
        if not isinstance(guide, dict):
            return f"Unexpected API format for guide {guideid}: {guide}"

        title = guide.get("title", "Unknown Guide")
        difficulty = guide.get("difficulty", "Unknown")

        # Safe time_required handling
        time_required_raw = guide.get("time_required", "Not specified")
        if isinstance(time_required_raw, dict):
            time_required = time_required_raw.get("text", "Not specified")
        elif isinstance(time_required_raw, list) and time_required_raw:
            first_item = time_required_raw[0]
            if isinstance(first_item, dict):
                time_required = first_item.get("text", "Not specified")
            else:
                time_required = str(first_item)
        else:
            time_required = str(time_required_raw)

        # Safe tools & parts
        tools_raw = guide.get("tools", [])
        tools = [t.get("text") if isinstance(t, dict) else str(t) for t in tools_raw]

        parts_raw = guide.get("parts", [])
        parts = [p.get("text") if isinstance(p, dict) else str(p) for p in parts_raw]

        # Safe steps
        steps = []
        for idx, step in enumerate(guide.get("steps", []), 1):
            if isinstance(step, dict):
                lines = step.get("lines", [])
                if isinstance(lines, list) and lines:
                    first_line = lines[0]
                    if isinstance(first_line, dict):
                        step_text = first_line.get("text", "").strip()
                    else:
                        step_text = str(first_line).strip()
                else:
                    step_text = ""
                if step_text:
                    steps.append(f"{idx}. {step_text}")

        result = f"Repair Guide: {title}\n"
        result += f"Difficulty: {difficulty}\n"
        result += f"Time Required: {time_required}\n"
        result += f"Tools: {', '.join(tools) if tools else 'None listed'}\n"
        result += f"Parts: {', '.join(parts) if parts else 'None listed'}\n\n"
        result += "Steps:\n" + "\n".join(steps)

        return result
    except Exception as e:
        return f"Error fetching guide {guideid}: {str(e)}"
