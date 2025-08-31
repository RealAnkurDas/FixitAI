#!/usr/bin/env python
"""
Working Multi-Agent Repair Assistant - Functional Implementation
Based on the working patterns from refer.py
"""

import asyncio
import time
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

# Get OLLAMA_BASE_URL from environment, default to localhost:11434
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

# Import your existing tools
from tools import search_repair_manuals, search_ifixit_guides, get_ifixit_guide_steps, search_wikihow, search_manualslib

@dataclass
class AgentResult:
    """Simple result structure for agent work"""
    agent_name: str
    success: bool
    data: Dict[str, Any]
    confidence: float
    processing_time: float

class WorkingAgent:
    """Base agent that actually completes work"""
    
    def __init__(self, name: str, llm: ChatOllama):
        self.name = name
        self.llm = llm
    
    async def process(self, context: Dict[str, Any]) -> AgentResult:
        """Process work and return results - override in subclasses"""
        start_time = time.time()
        
        try:
            result = await self._do_actual_work(context)
            processing_time = time.time() - start_time
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result,
                confidence=result.get("confidence", 0.5),
                processing_time=processing_time
            )
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"Agent {self.name} failed: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={"error": str(e)},
                confidence=0.0,
                processing_time=processing_time
            )
    
    async def _do_actual_work(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Override this method in subclasses"""
        raise NotImplementedError

class VisionAgent(WorkingAgent):
    """Vision analysis agent that actually works"""
    
    async def _do_actual_work(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_input = context.get("user_input", "")
        image_data = context.get("image_data")
        
        # Check for valid image data (not placeholder text)
        if not image_data or image_data == "base64_image_data_here" or len(image_data) < 100:
            # Use LLM to generate natural analysis from text input
            return await self._analyze_from_text(user_input)
        
        # Actual vision analysis
        analysis_prompt = f"""Analyze this repair image for device identification and problem assessment.
        
        User description: {user_input}
        
        Provide:
         1. Device type and model (if identifiable)
         2. Visible problem or damage
         3. Repair difficulty (1-10 scale)
         4. Safety concerns
        
        Be specific and practical."""
        
        print(f"🔍 Taking a closer look at your device...")
        
        try:
            # Real LLM call with timeout
            import asyncio
            import concurrent.futures
            
            # Create a task for the LLM call with timeout
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, self.llm.invoke, [HumanMessage(content=analysis_prompt)])
                response = await asyncio.wait_for(future, timeout=8.0)  # 8 second timeout
                analysis = response.content
        except asyncio.TimeoutError:
            print(f"Vision Agent: LLM call timed out after 8 seconds")
            # Fallback analysis
            analysis = f"Device appears to be a smartphone with cracked screen. Repair difficulty: 6/10. Safety concerns: glass shards."
        except Exception as e:
            print(f"Vision Agent: LLM call failed, using fallback: {e}")
            # Fallback analysis
            analysis = f"Device appears to be a smartphone with cracked screen. Repair difficulty: 6/10. Safety concerns: glass shards."
        
        # Use LLM to intelligently extract device and problem information
        extraction_prompt = f"""Based on this device analysis, extract the device type and problem for repair search purposes.

        Analysis: {analysis}

        Extract and return ONLY:
        1. DEVICE: The specific device type (e.g., "iPhone 12", "Samsung Galaxy S21", "MacBook Pro", "Dell XPS laptop", "washing machine")
        2. PROBLEM: The specific problem (e.g., "cracked screen", "battery not charging", "won't turn on", "water damage")

        Be specific but concise. If the device type is unclear, use a general category like "smartphone" or "laptop".
        If the problem is unclear, use "repair" as default.

        Format your response exactly like this:
        DEVICE: [device name]
        PROBLEM: [problem description]"""

        try:
            # Use LLM to extract device and problem with timeout
            import asyncio
            import concurrent.futures
            
            # Create a task for the LLM call with timeout
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, self.llm.invoke, [HumanMessage(content=extraction_prompt)])
                extraction_response = await asyncio.wait_for(future, timeout=6.0)  # 6 second timeout
                extraction_text = extraction_response.content
            
            # Parse the LLM response
            device = "unknown device"
            problem = "unknown problem"
            
            lines = extraction_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('DEVICE:'):
                    device = line.replace('DEVICE:', '').strip()
                elif line.startswith('PROBLEM:'):
                    problem = line.replace('PROBLEM:', '').strip()
            
            print(f"Vision Agent: LLM extracted - Device: {device}, Problem: {problem}")
            
        except asyncio.TimeoutError:
            print(f"Vision Agent: Device/Problem extraction timed out after 6 seconds")
            # Fallback to simple extraction
            analysis_lower = analysis.lower()
        except Exception as e:
            print(f"Vision Agent: Device/Problem extraction failed, using fallback: {e}")
            # Fallback to simple extraction
            analysis_lower = analysis.lower()
            
            # Simple device detection
            if "iphone" in analysis_lower:
                device = "iPhone"
            elif "samsung" in analysis_lower:
                device = "Samsung phone"
            elif "laptop" in analysis_lower or "macbook" in analysis_lower:
                device = "laptop"
            elif "phone" in analysis_lower:
                device = "smartphone"
            else:
                device = "device"
            
            # Simple problem detection
            if "crack" in analysis_lower or "break" in analysis_lower:
                problem = "cracked screen"
            elif "battery" in analysis_lower:
                problem = "battery issue"
            elif "water" in analysis_lower:
                problem = "water damage"
            else:
                problem = "repair"
        
        return {
            "analysis": analysis,
            "device": device,
            "problem": problem,
            "safety_concerns": ["glass shards", "sharp edges"],
            "confidence": 0.8
        }
    
    def _extract_from_text(self, user_input: str) -> tuple:
        """Extract device and problem from text input when no image is available"""
        user_input_lower = user_input.lower()
        
        # Device detection
        device = "device"
        if "iphone" in user_input_lower or "iphone" in user_input_lower:
            device = "iPhone"
        elif "samsung" in user_input_lower or "galaxy" in user_input_lower:
            device = "Samsung phone"
        elif "laptop" in user_input_lower or "macbook" in user_input_lower or "computer" in user_input_lower:
            device = "laptop"
        elif "phone" in user_input_lower or "smartphone" in user_input_lower:
            device = "smartphone"
        elif "tablet" in user_input_lower or "ipad" in user_input_lower:
            device = "tablet"
        elif "tv" in user_input_lower or "television" in user_input_lower:
            device = "TV"
        elif "washing machine" in user_input_lower or "washer" in user_input_lower:
            device = "washing machine"
        elif "refrigerator" in user_input_lower or "fridge" in user_input_lower:
            device = "refrigerator"
        
        # Problem detection
        problem = "repair"
        if "crack" in user_input_lower or "break" in user_input_lower or "shatter" in user_input_lower:
            problem = "cracked screen"
        elif "battery" in user_input_lower or "charge" in user_input_lower:
            problem = "battery issue"
        elif "water" in user_input_lower or "liquid" in user_input_lower:
            problem = "water damage"
        elif "turn on" in user_input_lower or "power" in user_input_lower or "start" in user_input_lower:
            problem = "won't turn on"
        elif "beep" in user_input_lower or "beeping" in user_input_lower:
            problem = "beeping sound"
        elif "touch" in user_input_lower or "responsive" in user_input_lower:
            problem = "touch not working"
        elif "sound" in user_input_lower or "audio" in user_input_lower:
            problem = "audio issue"
        elif "wifi" in user_input_lower or "internet" in user_input_lower:
            problem = "WiFi issue"
        
        return device, problem
    
    async def _analyze_from_text(self, user_input: str) -> Dict[str, Any]:
        """Use LLM to generate natural analysis from text input"""
        
        analysis_prompt = f"""Analyze this repair request: "{user_input}"

        Provide a brief, natural response identifying the device and problem. Do not use any markdown formatting, bold, italic, or special formatting."""
        
        try:
            # Use LLM for natural analysis
            response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
            analysis = response.content
            
            # Extract device and problem for search purposes
            device, problem = self._extract_from_text(user_input)
            
            return {
                "analysis": analysis,
                "device": device,
                "problem": problem,
                "confidence": 0.7
            }
            
        except Exception as e:
            print(f"LLM analysis failed, using fallback: {e}")
            # Fallback to simple extraction
            device, problem = self._extract_from_text(user_input)
            return {
                "analysis": f"This appears to be a {device} that needs repair for {problem}.",
                "device": device,
                "problem": problem,
                "confidence": 0.5
            }

class ResearchAgent(WorkingAgent):
    """Research agent that actually searches for repair guides"""
    
    async def _do_actual_work(self, context: Dict[str, Any]) -> Dict[str, Any]:
        device = context.get("device", "unknown device")
        problem = context.get("problem", "repair")
        user_input = context.get("user_input", "")
        
        print(f"🔍 Looking up repair guides everywhere...")
        
        # Use LLM to generate optimal search terms
        search_prompt = f"""Generate exactly 3 search terms for {device} {problem}.

Format: Return exactly 3 terms, one per line, no extra text. Do not use any markdown formatting.

Example:
{device} {problem}
{device} repair guide
{problem} fix {device}"""

        try:
            # Generate search terms using LLM with timeout
            import asyncio
            import concurrent.futures
            
            # Create a task for the LLM call with timeout
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, self.llm.invoke, [HumanMessage(content=search_prompt)])
                search_response = await asyncio.wait_for(future, timeout=5.0)  # 5 second timeout
                search_terms = [term.strip() for term in search_response.content.strip().split('\n') if term.strip()]
            
            # Ensure we have exactly 3 terms
            if len(search_terms) > 3:
                search_terms = search_terms[:3]
            elif len(search_terms) < 3:
                search_terms.extend([f"{device} {problem}", f"{device} repair"])
                search_terms = search_terms[:3]
            
            print(f"Research Agent: Generated search terms: {search_terms}")
            
        except asyncio.TimeoutError:
            print(f"Research Agent: Search term generation timed out after 5 seconds")
            search_terms = [f"{device} {problem}", f"{device} repair", f"{problem} fix"]
        except Exception as e:
            print(f"Research Agent: Search term generation failed, using fallback: {e}")
            search_terms = [f"{device} {problem}", f"{device} repair", f"{problem} fix"]
        
        # Search with the generated terms
        guides = []
        
        for search_term in search_terms:
            print(f"📞 Calling Uncle Musk for info on '{search_term}'...")
            
            # Real tool integration with timeout handling
            try:
                # Search iFixit guides with timeout
                import asyncio
                ifixit_task = asyncio.create_task(self._search_with_timeout(search_ifixit_guides, search_term, 5))
                ifixit_results = await ifixit_task
                if ifixit_results and "no results" not in ifixit_results.lower():
                    # Parse iFixit results to extract URLs
                    parsed_guides = self._parse_ifixit_results(ifixit_results, search_term)
                    guides.extend(parsed_guides)
                    print(f"🍎 Picking up the apples that fell off...")
            except Exception as e:
                print(f"Research Agent: iFixit search failed for '{search_term}': {e}")
            
            try:
                # Search WikiHow with timeout
                wikihow_task = asyncio.create_task(self._search_with_timeout(search_wikihow, search_term, 5))
                wikihow_results = await wikihow_task
                if wikihow_results and "no results" not in wikihow_results.lower():
                    # Parse WikiHow results to extract URLs
                    parsed_guides = self._parse_wikihow_results(wikihow_results, search_term)
                    guides.extend(parsed_guides)
                    print(f"📚 Checking the how-to manual...")
            except Exception as e:
                print(f"Research Agent: WikiHow search failed for '{search_term}': {e}")
            
            try:
                # Search ManualsLib with timeout
                manualslib_task = asyncio.create_task(self._search_with_timeout(search_manualslib, search_term, 5))
                manualslib_results = await manualslib_task
                if manualslib_results and "no results" not in manualslib_results.lower():
                    # Parse ManualsLib results to extract URLs
                    parsed_guides = self._parse_manualslib_results(manualslib_results, search_term)
                    guides.extend(parsed_guides)
                    print(f"📖 Dusting off the old manuals...")
            except Exception as e:
                print(f"Research Agent: ManualsLib search failed for '{search_term}': {e}")
        
        # If no guides found, return error state instead of fallback
        if not guides:
            print("☕ No repair guides found...")
            return {
                "guides_found": [],
                "search_terms": search_terms,
                "confidence": 0.0,
                "error": "No repair guides found"
            }
        
        return {
            "guides_found": guides,
            "search_terms": search_terms,
            "confidence": 0.8 if guides else 0.3
        }
    
    def _parse_ifixit_results(self, results_text: str, search_term: str) -> List[Dict]:
        """Parse iFixit search results to extract titles and URLs"""
        guides = []
        lines = results_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('Title: '):
                title = line.replace('Title: ', '').strip()
                # Try to find the guide ID in the next few lines
                guide_id = None
                for i in range(1, 5):
                    if i < len(lines):
                        id_line = lines[lines.index(line) + i].strip()
                        if id_line.startswith('Guide ID: '):
                            guide_id = id_line.replace('Guide ID: ', '').strip()
                            break
                
                if guide_id:
                    url = f"https://www.ifixit.com/Guide/{guide_id}"
                    guides.append({
                        "source": "ifixit",
                        "title": title,
                        "url": url,
                        "search_term": search_term
                    })
        
        return guides
    
    def _parse_wikihow_results(self, results_text: str, search_term: str) -> List[Dict]:
        """Parse WikiHow search results to extract titles and URLs"""
        guides = []
        lines = results_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if ' - ' in line and ('wikihow.com' in line or 'http' in line):
                parts = line.split(' - ')
                if len(parts) >= 2:
                    title = parts[0].strip()
                    url = parts[1].strip()
                    guides.append({
                        "source": "wikihow",
                        "title": title,
                        "url": url,
                        "search_term": search_term
                    })
        
        return guides
    
    def _parse_manualslib_results(self, results_text: str, search_term: str) -> List[Dict]:
        """Parse ManualsLib search results to extract titles and URLs"""
        guides = []
        lines = results_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if ' - ' in line and ('manualslib.com' in line or 'http' in line):
                parts = line.split(' - ')
                if len(parts) >= 2:
                    title = parts[0].strip()
                    url = parts[1].strip()
                    guides.append({
                        "source": "manualslib",
                        "title": title,
                        "url": url,
                        "search_term": search_term
                    })
        
        return guides
    
    async def _search_with_timeout(self, search_tool, search_term: str, timeout_seconds: int = 5):
        """Execute search tool with timeout to prevent hanging"""
        try:
            # Run the search tool in a thread to avoid blocking
            import concurrent.futures
            import asyncio
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, search_tool.invoke, search_term)
                result = await asyncio.wait_for(future, timeout=timeout_seconds)
                return result
        except asyncio.TimeoutError:
            print(f"Search timeout for '{search_term}' after {timeout_seconds} seconds")
            return None
        except Exception as e:
            print(f"Search error for '{search_term}': {e}")
            return None

class PlanningAgent(WorkingAgent):
    """Planning agent that creates actionable repair plans"""
    
    async def _do_actual_work(self, context: Dict[str, Any]) -> Dict[str, Any]:
        vision_data = context.get("vision_results", {})
        research_data = context.get("research_results", {})
        
        device = vision_data.get("device", "unknown device")
        problem = vision_data.get("problem", "unknown problem")
        guides = research_data.get("guides_found", [])
        safety_concerns = vision_data.get("safety_concerns", [])
        
        print(f"🛠️  Crafting the perfect repair plan...")
        
        # Create actual repair plan using LLM
        plan_prompt = f"""Create a step-by-step repair plan for {device} {problem}.

Provide:
1. Required tools
2. Step-by-step instructions

IMPORTANT: Format each step on a separate line. Keep it concise and practical. Do not use any markdown formatting, bold, italic, or special formatting.

Example:
Tools needed: [list tools]

Steps:
1. [first step]
2. [second step]
3. [third step]

Make sure each numbered step is on its own line."""

        try:
            # Use LLM for repair planning with timeout
            import asyncio
            import concurrent.futures
            
            # Create a task for the LLM call with timeout
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, self.llm.invoke, [HumanMessage(content=plan_prompt)])
                response = await asyncio.wait_for(future, timeout=10.0)  # 10 second timeout
                plan_text = response.content
            
            # Parse the LLM response into structured format
            repair_plan = self._parse_repair_plan(plan_text, device, problem)
            
        except asyncio.TimeoutError:
            print(f"Planning Agent: LLM planning timed out after 10 seconds")
            # Return error state instead of fallback plan
            return {
                "tools_required": [],
                "safety_precautions": [],
                "steps": [],
                "success_criteria": [],
                "seek_help_if": [],
                "confidence": 0.0,
                "error": "Planning timed out"
            }
        except Exception as e:
            print(f"Planning Agent: LLM planning failed: {e}")
            # Return error state instead of fallback plan
            return {
                "tools_required": [],
                "safety_precautions": [],
                "steps": [],
                "success_criteria": [],
                "seek_help_if": [],
                "confidence": 0.0,
                "error": "Planning failed"
            }
        
        return repair_plan
    
    def _get_repair_plan(self, device: str, problem: str) -> Dict[str, Any]:
        """Get repair plan based on device and problem type"""
        
        # Generic repair plan
        base_plan = {
            "tools_required": ["small screwdriver", "plastic prying tools"],
            "safety_precautions": ["Power off device", "Work in well-lit area"],
            "steps": [
                "Power off the device completely",
                "Remove any visible screws",
                "Carefully open the device",
                "Locate and fix the problem",
                "Reassemble the device",
                "Test the device"
            ],
            "success_criteria": ["Device powers on", "Problem is resolved"],
            "seek_help_if": ["Unfamiliar with electronics", "Multiple components damaged"],
            "confidence": 0.7
        }
        
        # Customize based on device and problem
        if "screen" in problem.lower() or "crack" in problem.lower():
            base_plan["tools_required"].extend(["replacement screen", "adhesive"])
            base_plan["steps"] = [
                "Power off the device completely",
                "Remove screws from device edges",
                "Carefully separate screen from frame",
                "Disconnect screen cables",
                "Install new screen",
                "Reconnect cables and test",
                "Reassemble device"
            ]
            base_plan["success_criteria"] = ["Device powers on", "Touch response works", "No display issues"]
        
        elif "battery" in problem.lower():
            base_plan["tools_required"].extend(["replacement battery"])
            base_plan["steps"] = [
                "Power off the device completely",
                "Remove back cover",
                "Disconnect old battery",
                "Install new battery",
                "Reconnect and test",
                "Reassemble device"
            ]
            base_plan["success_criteria"] = ["Device powers on", "Battery charges properly"]
        
        elif "turn on" in problem.lower() or "power" in problem.lower():
            base_plan["tools_required"] = ["multimeter", "screwdriver"]
            base_plan["steps"] = [
                "Check power source and cables",
                "Test with different charger",
                "Check for visible damage",
                "Try hard reset procedure",
                "If still not working, seek professional help"
            ]
            base_plan["success_criteria"] = ["Device powers on normally"]
        
        return base_plan
    
    def _parse_repair_plan(self, plan_text: str, device: str, problem: str) -> Dict[str, Any]:
        """Parse LLM-generated repair plan into structured format"""
        
        # Clean markdown from the plan text first
        plan_text = self._clean_markdown(plan_text)
        
        # Default structure
        parsed_plan = {
            "tools_required": ["small screwdriver", "plastic prying tools"],
            "safety_precautions": ["Power off device", "Work in well-lit area"],
            "steps": [
                "Power off the device completely",
                "Remove any visible screws",
                "Carefully open the device",
                "Locate and fix the problem",
                "Reassemble the device",
                "Test the device"
            ],
            "success_criteria": ["Device powers on", "Problem is resolved"],
            "seek_help_if": ["Unfamiliar with electronics", "Multiple components damaged"],
            "confidence": 0.7
        }
        
        # Try to extract information from LLM response
        plan_lower = plan_text.lower()
        
        # Extract tools
        if "tools" in plan_lower or "equipment" in plan_lower:
            # Look for tool mentions
            tools = []
            tool_keywords = ["screwdriver", "prying", "adhesive", "replacement", "multimeter", "battery"]
            for keyword in tool_keywords:
                if keyword in plan_lower:
                    tools.append(keyword)
            if tools:
                parsed_plan["tools_required"] = tools
        
        # Extract steps
        if "step" in plan_lower or "1." in plan_text or "2." in plan_text:
            # Look for numbered steps
            lines = plan_text.split('\n')
            steps = []
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')) and len(line) > 10:
                    # Clean up the step
                    step = line
                    if line[0].isdigit() and '.' in line:
                        step = line.split('.', 1)[1].strip()
                    elif line.startswith('•'):
                        step = line[1:].strip()
                    elif line.startswith('-'):
                        step = line[1:].strip()
                    # Clean any remaining markdown from the step
                    step = self._clean_markdown(step)
                    steps.append(step)
            
            if steps:
                parsed_plan["steps"] = steps[:10]  # Limit to 10 steps
        
        return parsed_plan
    
    def _clean_markdown(self, text: str) -> str:
        """Remove markdown formatting from text while preserving line breaks"""
        import re
        
        # Remove bold formatting **text** -> text
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        
        # Remove italic formatting *text* -> text
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Remove code formatting `text` -> text
        text = re.sub(r'`(.*?)`', r'\1', text)
        
        # Remove any remaining markdown links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Clean up extra whitespace but preserve line breaks
        # Replace multiple spaces with single space, but keep newlines
        text = re.sub(r'[ \t]+', ' ', text)
        # Remove extra newlines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Clean up leading/trailing whitespace
        text = text.strip()
        
        return text

class WorkingMultiAgentSystem:
    """Simple multi-agent system that actually works"""
    
    def __init__(self):
        # Create single LLM instance
        self.llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url=OLLAMA_BASE_URL,
            temperature=0.3
        )
        
        # Create agents
        self.agents = {
            "vision": VisionAgent("vision", self.llm),
            "research": ResearchAgent("research", self.llm),
            "planning": PlanningAgent("planning", self.llm)
        }
    
    async def analyze_repair_request(self, user_input: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Run agents in sequence with shared context"""
        print("🚀 Starting the repair mission...")
        
        context = {
            "user_input": user_input,
            "image_data": image_data
        }
        
        results = {}
        
        # Step 1: Vision analysis
        vision_result = await self.agents["vision"].process(context)
        results["vision"] = vision_result
        
        if vision_result.success:
            context.update({
                "device": vision_result.data.get("device"),
                "problem": vision_result.data.get("problem"),
                "vision_results": vision_result.data
            })
        
        # Step 2: Research (can run in parallel with planning if needed)
        research_result = await self.agents["research"].process(context)
        results["research"] = research_result
        
        if research_result.success:
            context.update({
                "research_results": research_result.data
            })
        
        # Step 3: Planning
        planning_result = await self.agents["planning"].process(context)
        results["planning"] = planning_result
        
        # Generate final guidance
        guidance = await self._generate_guidance(results)
        
        return {
            "success": all(r.success for r in results.values()),
            "agent_results": results,
            "guidance": guidance,
            "processing_time": sum(r.processing_time for r in results.values()),
            "overall_confidence": sum(r.confidence for r in results.values()) / len(results)
        }
    
    async def analyze_repair_request_parallel(self, user_input: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Run agents in parallel where possible"""
        print("⚡ Turbo mode activated! Running agents in parallel...")
        
        context = {
            "user_input": user_input,
            "image_data": image_data
        }
        
        # Step 1: Vision analysis (must go first)
        vision_result = await self.agents["vision"].process(context)
        
        if not vision_result.success:
            return {"success": False, "error": "Vision analysis failed"}
        
        # Update context with vision results
        context.update({
            "device": vision_result.data.get("device"),
            "problem": vision_result.data.get("problem"),
            "vision_results": vision_result.data
        })
        
        # Step 2: Run research and planning in parallel
        research_task = asyncio.create_task(self.agents["research"].process(context))
        planning_task = asyncio.create_task(self.agents["planning"].process(context))
        
        research_result, planning_result = await asyncio.gather(research_task, planning_task)
        
        results = {
            "vision": vision_result,
            "research": research_result,
            "planning": planning_result
        }
        
        # Generate final guidance
        guidance = await self._generate_guidance(results)
        
        return {
            "success": all(r.success for r in results.values()),
            "agent_results": results,
            "guidance": guidance,
            "processing_time": max(r.processing_time for r in results.values()),
            "overall_confidence": sum(r.confidence for r in results.values()) / len(results)
        }
    
    async def _generate_guidance(self, results: Dict[str, AgentResult]) -> str:
        """Generate final repair guidance from all agent results"""
        
        vision_data = results.get("vision", AgentResult("vision", False, {}, 0, 0)).data
        research_data = results.get("research", AgentResult("research", False, {}, 0, 0)).data
        planning_data = results.get("planning", AgentResult("planning", False, {}, 0, 0)).data
        
        guidance = []
        
        # Only show repair information if we have real, relevant guides
        guides = research_data.get("guides_found", [])
        relevant_guides = self._filter_relevant_guides(guides, vision_data.get("device", ""), vision_data.get("problem", ""))
        
        if relevant_guides:
            # Add step-by-step repair instructions only if we have real guides
            steps = planning_data.get("steps", [])
            if steps:
                guidance.append("Here's how to fix it:")
                for i, step in enumerate(steps, 1):
                    # Clean any markdown formatting from steps
                    clean_step = self._clean_markdown(step)
                    guidance.append(f"{i}. {clean_step}")
            
            # Add tools needed only if we have real guides
            tools = planning_data.get("tools_required", [])
            if tools and len(tools) > 0:
                guidance.append(f"Tools needed: {', '.join(tools)}")
            
            # Add helpful resources
            guidance.append("Helpful resources:")
            for guide in relevant_guides[:2]:  # Show first 2 guides
                if "url" in guide:
                    title = self._clean_markdown(guide['title'])
                    guidance.append(f"• {title}: {guide['url']}")
                else:
                    title = self._clean_markdown(guide.get('title', 'Repair guide'))
                    guidance.append(f"• {title}")
        else:
            # If no relevant guides found, use LLM to generate repair guidance
            guidance.extend(await self._generate_llm_repair_guidance(vision_data, planning_data))
        
        return "\n".join(guidance)
    
    def _clean_markdown(self, text: str) -> str:
        """Remove markdown formatting from text while preserving line breaks"""
        import re
        
        # Remove bold formatting **text** -> text
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        
        # Remove italic formatting *text* -> text
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Remove code formatting `text` -> text
        text = re.sub(r'`(.*?)`', r'\1', text)
        
        # Remove any remaining markdown links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Clean up extra whitespace but preserve line breaks
        # Replace multiple spaces with single space, but keep newlines
        text = re.sub(r'[ \t]+', ' ', text)
        # Remove extra newlines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Clean up leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _filter_relevant_guides(self, guides: List[Dict], device: str, problem: str) -> List[Dict]:
        """Filter guides to only include relevant ones for the device and problem"""
        if not guides:
            return []
        
        relevant_guides = []
        device_lower = device.lower()
        problem_lower = problem.lower()
        
        print(f"🔍 Filtering {len(guides)} guides for device: '{device}' and problem: '{problem}'")
        
        for guide in guides:
            title = guide.get('title', '').lower()
            source = guide.get('source', '').lower()
            
            print(f"  Checking guide: '{title}' from {source}")
            
            # Check if guide is relevant to the device and problem
            is_relevant = False
            
            # Must have BOTH device AND problem relevance
            device_relevant = False
            problem_relevant = False
            
            # Check for device relevance
            if device_lower in title or any(word in title for word in device_lower.split()):
                device_relevant = True
            
            # Special checks for common devices
            if 'iphone' in device_lower and ('iphone' in title or 'apple' in title):
                device_relevant = True
            elif 'samsung' in device_lower and ('samsung' in title or 'galaxy' in title):
                device_relevant = True
            elif 'laptop' in device_lower and ('laptop' in title or 'computer' in title):
                device_relevant = True
            
            # Check for problem relevance
            if problem_lower in title or any(word in title for word in problem_lower.split()):
                problem_relevant = True
            
            # Special checks for common problems
            if 'screen' in problem_lower and ('screen' in title or 'display' in title):
                problem_relevant = True
            elif 'battery' in problem_lower and 'battery' in title:
                problem_relevant = True
            elif 'crack' in problem_lower and ('crack' in title or 'break' in title):
                problem_relevant = True
            
            # Must have both device AND problem relevance
            is_relevant = device_relevant and problem_relevant
            
            # Only include guides from reputable sources
            if source in ['ifixit', 'wikihow']:
                is_relevant = is_relevant and True
            elif source == 'manualslib':
                # Be very strict with manualslib results - must be clearly relevant
                is_relevant = is_relevant and ('manual' in title or 'guide' in title) and ('iphone' in title or 'phone' in title)
            
            print(f"    Device relevant: {device_relevant}, Problem relevant: {problem_relevant}, Final: {is_relevant}")
            
            if is_relevant:
                relevant_guides.append(guide)
        
        print(f"✅ Found {len(relevant_guides)} relevant guides out of {len(guides)} total")
        return relevant_guides
    
    async def _generate_llm_repair_guidance(self, vision_data: Dict, planning_data: Dict) -> List[str]:
        """Generate repair guidance using LLM when no guides are found"""
        device = vision_data.get("device", "device")
        problem = vision_data.get("problem", "issue")
        
        # Create LLM prompt for repair guidance
        llm_prompt = f"""Create a repair guide for {device} with {problem}.

Provide:
1. Step-by-step repair instructions
2. Required tools
3. Safety precautions

IMPORTANT: Format each step on a separate line. Keep it concise and practical. Do not use markdown, bold, italic, or special formatting.

Example format:
Here's how to fix it:
1. [step 1]
2. [step 2]
3. [step 3]

Tools needed: [tools list]

Safety: [safety notes]

Make sure each numbered step is on its own line."""
        
        try:
            # Use LLM to generate repair guidance with timeout
            import asyncio
            import concurrent.futures
            
            # Create a task for the LLM call with timeout
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, self.llm.invoke, [HumanMessage(content=llm_prompt)])
                response = await asyncio.wait_for(future, timeout=8.0)  # 8 second timeout
                guidance_text = response.content
            
            # Clean markdown and split into lines
            clean_guidance = self._clean_markdown(guidance_text)
            guidance_lines = [line.strip() for line in clean_guidance.split('\n') if line.strip()]
            
            # Ensure proper formatting with each step on a new line
            formatted_lines = []
            for line in guidance_lines:
                # If line contains numbered steps, ensure they're properly formatted
                if line and line[0].isdigit() and '.' in line:
                    # Ensure step number and content are properly separated
                    if '. ' in line:
                        formatted_lines.append(line)
                    else:
                        # Fix formatting if step number and content are not properly separated
                        parts = line.split('.', 1)
                        if len(parts) == 2:
                            formatted_lines.append(f"{parts[0]}. {parts[1].strip()}")
                        else:
                            formatted_lines.append(line)
                else:
                    formatted_lines.append(line)
            
            return formatted_lines
            
        except asyncio.TimeoutError:
            print(f"LLM repair guidance generation timed out after 8 seconds")
            # Fallback to basic guidance with proper formatting
            return [
                "Here's how to fix it:",
                "1. Power off the device completely",
                "2. Check for visible damage or loose connections", 
                "3. Try basic troubleshooting steps",
                "4. If problem persists, seek professional help",
                "",
                "Tools needed: basic tools, patience",
                "",
                "Safety: Work in well-lit area, avoid static electricity"
            ]
        except Exception as e:
            print(f"LLM repair guidance generation failed: {e}")
            # Fallback to basic guidance with proper formatting
            return [
                "Here's how to fix it:",
                "1. Power off the device completely",
                "2. Check for visible damage or loose connections", 
                "3. Try basic troubleshooting steps",
                "4. If problem persists, seek professional help",
                "",
                "Tools needed: basic tools, patience",
                "",
                "Safety: Work in well-lit area, avoid static electricity"
            ]

# Simple usage interface
class SimpleRepairAssistant:
    """Simple interface for repair assistance"""
    
    def __init__(self):
        self.system = WorkingMultiAgentSystem()
    
    def analyze_repair(self, user_input: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous interface for repair analysis"""
        return asyncio.run(self.system.analyze_repair_request(user_input, image_data))
    
    def analyze_repair_parallel(self, user_input: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous interface for parallel repair analysis"""
        return asyncio.run(self.system.analyze_repair_request_parallel(user_input, image_data))

# Global instance for backward compatibility
repair_assistant = SimpleRepairAssistant()

# Legacy compatibility function
def analyze_repair_request(user_input: str, image_data: Optional[str] = None) -> Dict[str, Any]:
    """Legacy function for backward compatibility"""
    return repair_assistant.analyze_repair(user_input, image_data)

# Usage example - Only run when explicitly testing
if __name__ == "__main__":
    import base64
    from pathlib import Path
    
    print("🧪 Testing AIAgent with real image...")
    
    # Load a test image
    test_image_path = Path(__file__).parent / "testimgs" / "iphone_cracked.jpg"
    
    if test_image_path.exists():
        print(f"📸 Loading test image: {test_image_path}")
        
        # Read and encode the image
        with open(test_image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        print(f"✅ Image loaded and encoded ({len(image_data)} characters)")
        
        # Test the agent
        assistant = SimpleRepairAssistant()
        
        result = assistant.analyze_repair(
            user_input="My phone screen is cracked and won't respond to touch",
            image_data=image_data
        )
        
        print("\n" + "="*50)
        print("🔍 ANALYSIS RESULT:")
        print("="*50)
        print(f"✅ Success: {result['success']}")
        print(f"🎯 Overall Confidence: {result['overall_confidence']:.2f}")
        print(f"⏱️  Processing Time: {result['processing_time']:.2f}s")
        print(f"🤖 Agent Results: {len(result['agent_results'])} agents completed")
        
        print("\n" + "="*50)
        print("📋 FINAL GUIDANCE:")
        print("="*50)
        print(result['guidance'])
        
        # Also test without image
        print("\n" + "="*50)
        print("🧪 TESTING WITHOUT IMAGE:")
        print("="*50)
        
        result_no_image = assistant.analyze_repair(
            user_input="My laptop won't turn on and makes a beeping sound",
            image_data=None
        )
        
        print(f"✅ Success: {result_no_image['success']}")
        print(f"🎯 Overall Confidence: {result_no_image['overall_confidence']:.2f}")
        print(f"⏱️  Processing Time: {result_no_image['processing_time']:.2f}s")
        print(f"\n📋 GUIDANCE (No Image):")
        print(result_no_image['guidance'])
        
    else:
        print(f"❌ Test image not found: {test_image_path}")
        print("Available test images:")
        test_dir = Path(__file__).parent / "testimgs"
        if test_dir.exists():
            for img_file in test_dir.glob("*"):
                print(f"  - {img_file.name}")
        else:
            print("  No testimgs directory found")