#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tools module for MyFixit dataset interface and utility functions
"""

import json
import re
import math
import itertools
import requests
from typing import List, Dict, Optional, Any
from pathlib import Path
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from bs4 import BeautifulSoup

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

class iFixitAPI:
    """Enhanced iFixit API interface"""
    
    def __init__(self):
        self.base_url = "https://www.ifixit.com/api/2.0"
        self.headers = {
            'User-Agent': 'RepairBot/1.0'
        }
    
    def search_guides(self, query: str) -> List[Dict]:
        """Search for repair guides with unlimited results"""
        all_guides = []
        offset = 0
        limit = 50  # API limit per request
        
        while True:
            try:
                url = f"{self.base_url}/search/{query}"
                params = {
                    'limit': limit,
                    'offset': offset
                }
                
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, dict):
                    guides = data.get('results', data.get('guides', []))
                elif isinstance(data, list):
                    guides = data
                else:
                    break
                
                if not guides:
                    break
                
                all_guides.extend(guides)
                
                # If we got fewer results than the limit, we've reached the end
                if len(guides) < limit:
                    break
                    
                offset += limit
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching guides: {e}")
                break
        
        return all_guides
    
    def get_guide_details(self, guide_id: int) -> Optional[Dict]:
        """Get detailed information about a specific guide"""
        try:
            url = f"{self.base_url}/guides/{guide_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting guide details for {guide_id}: {e}")
            return None
    
    def extract_tools_and_steps(self, guide_details: Dict) -> Dict[str, Any]:
        """Extract tools and steps from guide details"""
        if not isinstance(guide_details, dict):
            return {"tools": [], "steps": [], "error": "Invalid guide format"}
        
        # Extract tools
        tools = []
        tools_raw = guide_details.get("tools", [])
        for tool in tools_raw:
            if isinstance(tool, dict):
                tool_name = tool.get("text", tool.get("title", tool.get("name", "")))
                if tool_name:
                    tools.append(tool_name)
            else:
                tools.append(str(tool))
        
        # Extract parts (also useful for repairs)
        parts = []
        parts_raw = guide_details.get("parts", [])
        for part in parts_raw:
            if isinstance(part, dict):
                part_name = part.get("text", part.get("title", part.get("name", "")))
                if part_name:
                    parts.append(part_name)
            else:
                parts.append(str(part))
        
        # Extract steps
        steps = []
        for idx, step in enumerate(guide_details.get("steps", []), 1):
            if isinstance(step, dict):
                # Try different possible step text locations
                step_text = ""
                
                # Check for lines array (common format)
                lines = step.get("lines", [])
                if isinstance(lines, list) and lines:
                    first_line = lines[0]
                    if isinstance(first_line, dict):
                        step_text = first_line.get("text", "").strip()
                    else:
                        step_text = str(first_line).strip()
                
                # Fallback to direct text field
                if not step_text:
                    step_text = step.get("text", step.get("title", "")).strip()
                
                if step_text:
                    steps.append(f"{idx}. {step_text}")
            else:
                steps.append(f"{idx}. {str(step)}")
        
        return {
            "tools": tools,
            "parts": parts,
            "steps": steps,
            "difficulty": guide_details.get("difficulty", "Unknown"),
            "time_required": self._extract_time_required(guide_details.get("time_required"))
        }
    
    def _extract_time_required(self, time_data) -> str:
        """Extract time required from various formats"""
        if isinstance(time_data, dict):
            return time_data.get("text", "Not specified")
        elif isinstance(time_data, list) and time_data:
            first_item = time_data[0]
            if isinstance(first_item, dict):
                return first_item.get("text", "Not specified")
            else:
                return str(first_item)
        elif time_data:
            return str(time_data)
        return "Not specified"

@tool
def search_ifixit_guides(query: str) -> str:
    """
    Search iFixit API for repair guides with complete details including tools and steps.
    Returns unlimited results with full guide information.
    
    Args:
        query: Search term (e.g., "iPhone screen repair", "MacBook battery")
    """
    try:
        api = iFixitAPI()
        
        # Search for guides
        guides = api.search_guides(query)
        
        if not guides:
            return f"No guides found for '{query}'."
        
        # Get detailed information for each guide
        detailed_results = []
        
        for i, guide in enumerate(guides):
            guide_id = guide.get('guideid') or guide.get('id')
            if not guide_id:
                continue
                
            # Get basic info
            title = guide.get('title', 'Unknown Title')
            device = guide.get('device', guide.get('category', 'Unknown Device'))
            difficulty = guide.get('difficulty', 'Unknown')
            
            # Get detailed guide information
            guide_details = api.get_guide_details(guide_id)
            
            result_text = f"#{i+1} - Guide ID: {guide_id}\n"
            result_text += f"Title: {title}\n"
            result_text += f"Device: {device}\n"
            result_text += f"Difficulty: {difficulty}\n"
            
            if guide_details:
                details = api.extract_tools_and_steps(guide_details)
                
                # Add time required
                time_req = details.get('time_required', 'Not specified')
                if time_req != 'Not specified':
                    result_text += f"Time Required: {time_req}\n"
                
                # Add tools
                tools = details.get('tools', [])
                if tools:
                    result_text += f"Tools Needed: {', '.join(tools[:5])}" # Limit to first 5 tools
                    if len(tools) > 5:
                        result_text += f" (+{len(tools)-5} more)"
                    result_text += "\n"
                
                # Add parts if any
                parts = details.get('parts', [])
                if parts:
                    result_text += f"Parts Needed: {', '.join(parts[:3])}" # Limit to first 3 parts
                    if len(parts) > 3:
                        result_text += f" (+{len(parts)-3} more)"
                    result_text += "\n"
                
                # Add steps preview
                steps = details.get('steps', [])
                if steps:
                    result_text += f"Steps ({len(steps)} total):\n"
                    # Show first 3 steps as preview
                    for step in steps[:3]:
                        # Truncate long steps
                        step_text = step[:100] + "..." if len(step) > 100 else step
                        result_text += f"  {step_text}\n"
                    if len(steps) > 3:
                        result_text += f"  ... and {len(steps)-3} more steps\n"
            else:
                result_text += "Could not retrieve detailed guide information.\n"
            
            # Add summary if available
            summary = guide.get('summary', '')
            if summary:
                summary_preview = summary[:150] + "..." if len(summary) > 150 else summary
                result_text += f"Summary: {summary_preview}\n"
            
            detailed_results.append(result_text)
        
        return f"Found {len(guides)} iFixit guides for '{query}':\n\n" + "\n\n".join(detailed_results)
        
    except Exception as e:
        return f"Error searching iFixit: {str(e)}"

@tool
def get_ifixit_guide_steps(guideid: int) -> str:
    """
    Fetch complete guide details (steps, tools, difficulty) from iFixit.
    This function is maintained for backward compatibility.
    """
    try:
        api = iFixitAPI()
        guide_details = api.get_guide_details(guideid)
        
        if not guide_details:
            return f"Could not retrieve guide {guideid}"
        
        title = guide_details.get("title", "Unknown Guide")
        details = api.extract_tools_and_steps(guide_details)
        
        result = f"Repair Guide: {title}\n"
        result += f"Difficulty: {details['difficulty']}\n"
        result += f"Time Required: {details['time_required']}\n"
        
        if details['tools']:
            result += f"Tools: {', '.join(details['tools'])}\n"
        else:
            result += "Tools: None listed\n"
        
        if details['parts']:
            result += f"Parts: {', '.join(details['parts'])}\n"
        else:
            result += "Parts: None listed\n"
        
        result += f"\nSteps ({len(details['steps'])} total):\n"
        result += "\n".join(details['steps'])
        
        return result
        
    except Exception as e:
        return f"Error fetching guide {guideid}: {str(e)}"
    
@tool
def search_wikihow(query: str) -> str:
    """
    Search WikiHow for repair or upcycling guides.
    
    Args:
        query: Search term (e.g., "fix wooden chair", "upcycle old table")
    """
    try:
        search_tool = DuckDuckGoSearchRun()
        results = search_tool.run(f"site:wikihow.com {query}")
        return f"WikiHow results for '{query}':\n\n{results}"
    except Exception as e:
        return f"Error searching WikiHow: {str(e)}"
    
@tool
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