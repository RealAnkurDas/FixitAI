#!/usr/bin/env python
# -- coding: utf-8 --
"""
Tools module for repair guide interface and utility functions
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

@tool
def search_repair_manuals(device: Optional[str] = None, part: Optional[str] = None, keywords: Optional[str] = None) -> str:
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


class iFixitAPI:
    """Enhanced iFixit API interface"""
    
    def _init_(self):
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