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
    Search the iFixit API for repair guides by keyword.

    Args:
        query: Search terms, e.g., "iPhone 12 screen replacement"
    Returns:
        String summary of top guides with guideid for fetching details.
    """
    try:
        resp = requests.get(f"{IFIXIT_API_BASE}/guides", params={"query": query})
        resp.raise_for_status()
        guides = resp.json().get("guides", [])
        if not guides:
            return f"No guides found for '{query}'."

        top_results = []
        for g in guides[:5]:
            top_results.append(
                f"GuideID: {g.get('guideid')}\n"
                f"Title: {g.get('title')}\n"
                f"Device: {g.get('device')}\n"
                f"Difficulty: {g.get('difficulty', 'Unknown')}\n"
                f"Summary: {g.get('summary', '').strip()}"
            )
        return "Top iFixit Guides:\n\n" + "\n\n".join(top_results)
    except Exception as e:
        return f"Error searching iFixit: {str(e)}"


@tool
def get_ifixit_guide_steps(guideid: int) -> str:
    """
    Fetch full guide details (steps, tools, difficulty) from iFixit.

    Args:
        guideid: ID of the guide (from search_ifixit_guides)
    Returns:
        Formatted string containing tools, parts, and numbered steps.
    """
    try:
        resp = requests.get(f"{IFIXIT_API_BASE}/guides/{guideid}")
        resp.raise_for_status()
        guide = resp.json()

        title = guide.get("title", "Unknown Guide")
        difficulty = guide.get("difficulty", "Unknown")
        time_required = guide.get("time_required", {}).get("text", "Not specified")

        tools = [t.get("text") for t in guide.get("tools", [])]
        parts = [p.get("text") for p in guide.get("parts", [])]

        steps = []
        for idx, step in enumerate(guide.get("steps", []), 1):
            step_text = step.get("lines", [{}])[0].get("text", "").strip()
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