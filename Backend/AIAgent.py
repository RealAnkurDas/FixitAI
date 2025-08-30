#!/usr/bin/env python
# -- coding: utf-8 --
"""
True Agentic Multi-Agent Repair Assistant with LangGraph
Switches between multi-agent problem solving and conversational guidance
"""

import os
import re
import json
import asyncio
from typing import List, Dict, Optional, Any, Literal
from pathlib import Path
from enum import Enum
import time

# Core LangChain imports
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool

# LangGraph for multi-agent coordination
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

# Image processing
import base64
from PIL import Image

# Import tools
from tools import search_repair_manuals, search_ifixit_guides, get_ifixit_guide_steps, search_wikihow, search_manualslib

# Import environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
class Config:
    MODEL_NAME = "qwen2.5vl:7b" #"gemma3:latest"
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") # create a .env file in project root folder and set OLLAMA_BASE_URL = "your_ollama_base_url"
    TEMPERATURE_PLANNING = 0.7  # Higher for creative problem solving
    TEMPERATURE_INSTRUCTION = 0.2  # Lower for precise instructions

class SystemMode(Enum):
    """Current system operating mode"""
    LISTENING = "listening"           # Waiting for user input
    MULTI_AGENT = "multi_agent"       # Agents collaborating to solve problem
    CONVERSATIONAL = "conversational" # Guided step-by-step assistance
    EVALUATING = "evaluating"         # Checking progress and next steps

class RepairContext:
    """Comprehensive repair context and memory"""
    
    def __init__(self):
        # Core repair info
        self.device = None
        self.problem = None
        self.user_goal = None
        self.difficulty_level = None
        
        # Current state
        self.mode = SystemMode.LISTENING
        self.current_manual = None
        self.current_step = 0
        self.tools_available = []
        self.tools_needed = []
        
        # Agent coordination
        self.agent_findings = {}
        self.next_action_plan = []
        self.confidence_level = 0.0
        
        # Conversation flow
        self.conversation_history = []
        self.user_skill_level = "beginner"  # beginner, intermediate, advanced
        self.safety_concerns = []
        
        # Image analysis
        self.image_data = None
        self.visual_analysis = None
    
    def update_findings(self, agent_name: str, findings: Dict):
        """Update findings from an agent"""
        self.agent_findings[agent_name] = {
            **findings,
            "timestamp": time.time()
        }
    
    def get_context_for_agent(self, agent_name: str) -> str:
        """Get relevant context for specific agent"""
        context = f"Device: {self.device or 'Unknown'}\n"
        context += f"Problem: {self.problem or 'Unknown'}\n"
        context += f"User Goal: {self.user_goal or 'Fix the device'}\n"
        
        if self.visual_analysis:
            context += f"Visual Analysis: {self.visual_analysis}\n"
        
        # Include relevant findings from other agents
        if agent_name != "coordinator":
            for agent, findings in self.agent_findings.items():
                if agent != agent_name:
                    context += f"{agent.title()} findings: {findings.get('summary', '')}\n"
        
        return context.strip()
    
    def should_switch_to_conversational(self) -> bool:
        """Determine if we should switch to conversational mode"""
        return (
            self.current_manual is not None and
            len(self.agent_findings) >= 2 and  # At least 2 agents have contributed
            self.confidence_level > 0.7
        )

# Global context
repair_context = RepairContext()

# Enhanced Agent State for LangGraph
class AgentState(TypedDict):
    # Core communication
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Input data
    user_input: str
    image_data: Optional[str]
    
    # Agent coordination
    active_agents: List[str]  # Which agents should run
    completed_agents: List[str]  # Which agents have completed
    agent_results: Dict[str, Dict[str, Any]]  # Results from each agent
    
    # Task context
    device: Optional[str]
    problem: Optional[str]
    user_goal: Optional[str]
    
    # Flow control
    next_action: str  # "continue_agents", "start_guidance", "need_more_info"
    overall_confidence: float
    ready_for_guidance: bool
    
    # Guidance state
    current_manual: Optional[str]
    current_step: int
    conversation_history: List[Dict]

# Vision Agent - Analyzes images and visual problems
class VisionAgent:
    """Specialized agent for image analysis and visual diagnosis"""
    
    def __init__(self):
        self.llm = ChatOllama(
            model=Config.MODEL_NAME,
            base_url=Config.OLLAMA_BASE_URL,
            temperature=Config.TEMPERATURE_PLANNING
        )
        self.name = "vision"
    
    def analyze_image(self, image_base64: str, user_description: str = "") -> Dict[str, Any]:
        """Analyze image for repair opportunities"""
        system_prompt = """You are a vision specialist repair agent. Analyze images to identify:
1. Device type and model (if visible)
2. Specific damage or issues
3. Repair complexity (1-5 scale)
4. Safety concerns
5. Whether this is DIY-friendly

Be precise and focus on actionable insights."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=[
                    {"type": "text", "text": f"Analyze this repair situation: {user_description}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ])
            ]
            
            response = self.llm.invoke(messages)
            analysis = response.content
            print(f"[TOOL] Vision LLM | [INPUT] {user_description[:100]}...")
            print(f"[EXTRACTED] {analysis[:500]}{'...' if len(analysis) > 500 else ''}")
            
            # Extract structured info
            findings = {
                "device": self._extract_device(analysis),
                "damage_type": self._extract_damage_type(analysis),
                "complexity": self._extract_complexity(analysis),
                "safety_concerns": self._extract_safety_concerns(analysis),
                "summary": analysis,
                "confidence": 0.8
            }
            
            # Update global context
            repair_context.visual_analysis = analysis
            repair_context.device = findings["device"]
            repair_context.safety_concerns = findings["safety_concerns"]
            repair_context.update_findings(self.name, findings)
            
            return findings
            
        except Exception as e:
            return {"error": f"Vision analysis failed: {str(e)}", "confidence": 0.0}
    
    def _extract_device(self, analysis: str) -> str:
        """Use AI to detect the exact device name and model."""
        try:
            llm_prompt = f"""
            Identify the exact device make and model from the following repair analysis text.
            Be as specific as possible (e.g., 'Framework Laptop 12', 'Samsung Galaxy S20', 'iPhone 14 Pro').
            If you are not sure, make your best guess but keep it short.
            
            Analysis text:
            {analysis}
            """
            response = self.llm.invoke([HumanMessage(content=llm_prompt)])
            device_name = response.content.strip()
            return device_name or "unknown device"
        except Exception:
            return "unknown device"

    def _extract_damage_type(self, analysis: str) -> str:
        """Extract damage type"""
        analysis_lower = analysis.lower()
        damages = ['cracked screen', 'battery', 'water damage', 'broken', 'not charging', 'overheating']
        for damage in damages:
            if damage in analysis_lower:
                return damage
        return "unknown"
    
    def _extract_complexity(self, analysis: str) -> int:
        """Extract repair complexity (1-5)"""
        analysis_lower = analysis.lower()
        if any(word in analysis_lower for word in ['simple', 'easy', 'basic']):
            return 2
        elif any(word in analysis_lower for word in ['complex', 'difficult', 'advanced']):
            return 4
        else:
            return 3
    
    def _extract_safety_concerns(self, analysis: str) -> List[str]:
        """Extract safety concerns"""
        concerns = []
        analysis_lower = analysis.lower()
        if 'battery' in analysis_lower:
            concerns.append('Battery handling')
        if 'electrical' in analysis_lower:
            concerns.append('Electrical safety')
        if 'sharp' in analysis_lower:
            concerns.append('Sharp components')
        return concerns

# Research Agent - Finds and analyzes repair manuals
class ResearchAgent:
    """Agent specialized in finding and evaluating repair resources"""
    
    def __init__(self):
        self.llm = ChatOllama(
            model=Config.MODEL_NAME,
            base_url=Config.OLLAMA_BASE_URL,
            temperature=Config.TEMPERATURE_PLANNING
        )
        self.name = "research"
    
    def find_repair_guide(self, device: str, problem: str) -> Dict[str, Any]:
        """Search iFixit, then WikiHow, then Manualslib for guides"""
        context = repair_context.get_context_for_agent(self.name)

        # 🔍 1. Search iFixit API
        search_results = search_ifixit_guides.invoke(f"{device} {problem}")
        print(f"[TOOL] search_ifixit_guides | [QUERY] {device} {problem}")
        print(f"[EXTRACTED] {search_results[:500]}{'...' if len(search_results) > 500 else ''}")

        # Extract Guide ID if possible
        match = re.search(r"guide\s*id[:\s]+(\d+)", search_results, re.I)
        best_guide_id = int(match.group(1)) if match else None

        detailed_steps = ""
        wikihow_results = ""
        manuals_results = ""
        
        if best_guide_id:
            detailed_steps = get_ifixit_guide_steps.invoke({"guideid": best_guide_id})
        
        if not detailed_steps:
            # 2. Try WikiHow
            wikihow_results = search_wikihow.invoke(f"{device} {problem}")
            print(f"[TOOL] search_wikihow | [QUERY] {device} {problem}")
            if wikihow_results and "wikihow" in wikihow_results.lower():
                detailed_steps = wikihow_results
        
        if not detailed_steps:
            # 3. Try Manualslib
            manuals_results = search_manualslib.invoke(f"{device} {problem}")
            print(f"[TOOL] search_manualslib | [QUERY] {device} {problem}")
            if manuals_results and "manualslib" in manuals_results.lower():
                detailed_steps = manuals_results

        # Save to context if we found something
        if detailed_steps:
            repair_context.current_manual = detailed_steps
            repair_context.current_step = 0

        findings = {
            "search_results": search_results,
            "wikihow_results": wikihow_results,
            "manualslib_results": manuals_results,
            "recommended_guideid": best_guide_id,
            "detailed_steps": detailed_steps,
            "confidence": 0.9 if detailed_steps else 0.3,
            "summary": f"Found repair resources for {device} {problem} (iFixit/WikiHow/Manualslib)"
        }

        repair_context.update_findings(self.name, findings)
        return findings

# Planning Agent - Creates repair strategies and coordinates approach
class PlanningAgent:
    """Agent that creates repair strategies and coordinates the overall approach"""
    
    def __init__(self):
        self.llm = ChatOllama(
            model=Config.MODEL_NAME,
            base_url=Config.OLLAMA_BASE_URL,
            temperature=Config.TEMPERATURE_PLANNING
        )
        self.name = "planning"
    
    def create_repair_strategy(self) -> Dict[str, Any]:
        """Create comprehensive repair strategy based on all agent findings"""
        context = repair_context.get_context_for_agent(self.name)
        all_findings = json.dumps(repair_context.agent_findings, indent=2)
        
        strategy_prompt = f"""You are a master repair strategist. Based on all agent findings, create a comprehensive repair plan.

Context: {context}

Agent Findings:
{all_findings}

Create a strategy that includes:
1. Overall approach and difficulty assessment
2. Required tools and materials 
3. Key safety considerations
4. Step-by-step plan outline
5. Potential challenges and solutions
6. Success criteria
7. When to seek professional help

Consider the user's skill level and available resources."""

        response = self.llm.invoke([HumanMessage(content=strategy_prompt)])
        
        # Extract structured plan
        strategy_analysis = response.content

        print(f"[TOOL] Planning LLM | [INPUT] strategy_prompt")
        print(f"[EXTRACTED] {strategy_analysis[:500]}{'...' if len(strategy_analysis) > 500 else ''}")
        
        findings = {
            "strategy": strategy_analysis,
            "confidence": self._assess_confidence(),
            "recommended_mode": "conversational" if repair_context.current_manual else "research_more",
            "safety_priority": "high" if repair_context.safety_concerns else "medium",
            "summary": "Comprehensive repair strategy created"
        }
        
        repair_context.confidence_level = findings["confidence"]
        repair_context.update_findings(self.name, findings)
        
        return findings
    
    def _assess_confidence(self) -> float:
        """Assess overall confidence in repair plan"""
        total_confidence = 0
        agent_count = 0
        
        for agent_findings in repair_context.agent_findings.values():
            if "confidence" in agent_findings:
                total_confidence += agent_findings["confidence"]
                agent_count += 1
        
        return total_confidence / agent_count if agent_count > 0 else 0.5

# LangGraph Node Functions
def coordinator_node(state: AgentState) -> AgentState:
    """Initial coordinator - analyzes input and determines which agents to run"""
    
    print("🤖 Coordinator: Analyzing situation...")
    
    # Analyze user input to extract basic info
    user_input = state.get("user_input", "")
    
    # Simple problem extraction (can be enhanced with LLM)
    problem = "repair"
    user_input_lower = user_input.lower()
    if "screen" in user_input_lower or "display" in user_input_lower:
        problem = "screen replacement"
    elif "battery" in user_input_lower:
        problem = "battery replacement" 
    elif "charging" in user_input_lower:
        problem = "charging issue"
    elif "upgrade" in user_input_lower:
        problem = "hardware upgrade"
    
    # Determine which agents should run
    active_agents = []
    
    # Always run planning agent
    active_agents.append("planning")
    
    # Run vision agent if image provided
    if state.get("image_data"):
        active_agents.append("vision")
    
    # Always run research agent
    active_agents.append("research")
    
    # Update state
    new_state = state.copy()
    new_state["active_agents"] = active_agents
    new_state["problem"] = problem
    new_state["user_goal"] = user_input
    
    # Initialize empty results dict
    if "agent_results" not in new_state:
        new_state["agent_results"] = {}
    if "completed_agents" not in new_state:
        new_state["completed_agents"] = []
    
    print(f"🎯 Coordinator: Activating agents: {active_agents}")
    return new_state

def run_agents_parallel(state: AgentState) -> AgentState:
    """Run all active agents in parallel (simulated)"""
    
    print("🚀 Running agents in parallel...")
    
    active_agents = state.get("active_agents", [])
    new_state = state.copy()
    
    # Initialize agent results if not present
    if "agent_results" not in new_state:
        new_state["agent_results"] = {}
    
    # Run Vision Agent if active and image available
    if "vision" in active_agents and state.get("image_data"):
        print("  👁 Running Vision Agent...")
        try:
            vision_agent = VisionAgent()
            vision_results = vision_agent.analyze_image(
                state["image_data"], 
                state.get("user_input", "")
            )
            new_state["agent_results"]["vision"] = vision_results
            
            # Update device info if found
            if vision_results.get("device"):
                new_state["device"] = vision_results["device"]
        except Exception as e:
            print(f"❌ Vision Agent error: {e}")
            new_state["agent_results"]["vision"] = {"error": str(e), "confidence": 0.0}
    
    # Run Research Agent if active
    if "research" in active_agents:
        print("  📚 Running Research Agent...")
        try:
            research_agent = ResearchAgent()
            device = new_state.get("device", "unknown device")
            problem = new_state.get("problem", "repair")
            
            # If device still unknown, try to extract from user input
            if device == "unknown device" and state.get("user_input"):
                user_input = state["user_input"].lower()
                if any(brand in user_input for brand in ["iphone", "samsung", "laptop", "framework"]):
                    device = state["user_input"]
            
            research_results = research_agent.find_repair_guide(device, problem)
            new_state["agent_results"]["research"] = research_results
            
            # Update manual info if found
            if research_results.get("detailed_steps"):
                new_state["current_manual"] = research_results["detailed_steps"]
            
        except Exception as e:
            print(f"❌ Research Agent error: {e}")
            new_state["agent_results"]["research"] = {"error": str(e), "confidence": 0.0}
    
    # Run Planning Agent if active
    if "planning" in active_agents:
        print("  📋 Running Planning Agent...")
        try:
            planning_agent = PlanningAgent()
            
            # Set up repair context with current state
            repair_context.device = new_state.get("device")
            repair_context.problem = new_state.get("problem")
            repair_context.user_goal = new_state.get("user_goal")
            repair_context.agent_findings = new_state.get("agent_results", {})
            
            planning_results = planning_agent.create_repair_strategy()
            new_state["agent_results"]["planning"] = planning_results
            new_state["overall_confidence"] = planning_results.get("confidence", 0.5)
            
        except Exception as e:
            print(f"❌ Planning Agent error: {e}")
            new_state["agent_results"]["planning"] = {"error": str(e), "confidence": 0.0}
    
    # Mark all as completed
    new_state["completed_agents"] = active_agents.copy()
    
    print("✅ All agents completed in parallel")
    return new_state

def decision_node_simple(state: AgentState) -> AgentState:
    """Simplified decision node that evaluates results"""
    
    print("🔄 Decision Node: Evaluating results...")
    
    agent_results = state.get("agent_results", {})
    overall_confidence = state.get("overall_confidence", 0.0)
    has_manual = bool(state.get("current_manual"))
    
    # Check if we found a manual in research results
    if not has_manual and "research" in agent_results:
        research_results = agent_results["research"]
        if research_results.get("detailed_steps"):
            has_manual = True
            state["current_manual"] = research_results["detailed_steps"]
    
    # Determine readiness for guidance
    ready_for_guidance = (
        len(agent_results) >= 2 and  # At least 2 agents completed
        overall_confidence > 0.5 and  # Reasonable confidence
        has_manual  # Found repair manual
    )
    
    # Update state with decision
    new_state = state.copy()
    new_state["ready_for_guidance"] = ready_for_guidance
    
    if ready_for_guidance:
        new_state["next_action"] = "start_guidance"
        print("📊 Decision: Ready for step-by-step guidance!")
    else:
        new_state["next_action"] = "need_more_info"
        print("📊 Decision: Need more information")
    
    return new_state

# Build the LangGraph workflow
def build_sequential_multi_agent_graph():
    """Build sequential workflow with parallel agent block"""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("run_all_agents", run_agents_parallel)
    workflow.add_node("decision", decision_node_simple)
    
    # Sequential flow
    workflow.set_entry_point("coordinator")
    workflow.add_edge("coordinator", "run_all_agents")
    workflow.add_edge("run_all_agents", "decision")
    workflow.add_edge("decision", END)
    
    return workflow.compile()

# Conversational Guide - Provides step-by-step interactive assistance
class ConversationalGuide:
    """Handles step-by-step conversational repair guidance"""
    
    def __init__(self):
        self.llm = ChatOllama(
            model=Config.MODEL_NAME,
            base_url=Config.OLLAMA_BASE_URL,
            temperature=Config.TEMPERATURE_INSTRUCTION
        )
    
    def provide_guidance(self, user_message: str) -> str:
        """Provide contextual repair guidance"""
        context = repair_context.get_context_for_agent("guide")
        current_manual = repair_context.current_manual or "No specific manual found"
        findings_summary = self._summarize_agent_findings()
        
        guidance_prompt = f"""You are a friendly repair guide helping someone through their repair.

Context: {context}
Current Manual: {current_manual}
Agent Findings: {findings_summary}
Current Step: {repair_context.current_step}

User Message: {user_message}

Provide helpful, conversational guidance. Be encouraging and specific. 
If they're asking about the next step, guide them clearly.
If they're stuck, offer alternatives or troubleshooting.
Keep safety in mind always.
Try to make the texts look like conversations, don't write long messages
"""

        response_stream = self.llm.stream([HumanMessage(content=guidance_prompt)])
        print(f"[TOOL] Guide LLM | [INPUT] {user_message[:100]}...")
        
        full_response = ""
        print(f"\n🤖 ", end="")
        for chunk in response_stream:
            content = chunk.content
            print(content, end="", flush=True)
            full_response += content
        print("\n")

        print(f"[EXTRACTED] {full_response[:500]}{'...' if len(full_response) > 500 else ''}")
        
        # Update conversation history
        repair_context.conversation_history.append({
            "user": user_message,
            "assistant": full_response,
            "step": repair_context.current_step
        })
        
        return "" # Return empty string as output is streamed
    
    def _summarize_agent_findings(self) -> str:
        """Create a brief summary of key agent findings"""
        summary_parts = []
        for agent_name, findings in repair_context.agent_findings.items():
            if agent_name != "coordinator":
                summary_parts.append(f"{agent_name}: {findings.get('summary', 'No summary')}")
        return " | ".join(summary_parts)

# Main System Controller with LangGraph
class RepairAssistantSystem:
    """Main system using LangGraph for multi-agent coordination"""
    
    def __init__(self):
        # Initialize the multi-agent workflow
        self.workflow = build_sequential_multi_agent_graph()
        self.guide = ConversationalGuide()
        self.vision_processor = self.__init__vision_processor()
    
    def __init__vision_processor(self):
        """Initialize vision processing capabilities"""
        class VisionProcessor:
            @staticmethod
            def encode_image(image_path: str) -> Optional[str]:
                try:
                    with open(image_path, "rb") as f:
                        return base64.b64encode(f.read()).decode('utf-8')
                except Exception:
                    return None
        return VisionProcessor()
    
    def process_user_input(self, user_input: str, image_path: str = None) -> str:
        """Main entry point using LangGraph workflow"""
        
        # Handle image if provided
        image_data = None
        if image_path and os.path.exists(image_path):
            try:
                Image.open(image_path)  # Verify it's an image
                image_data = self.vision_processor.encode_image(image_path)
                if image_data:
                    print("📸 Image received and processed!")
            except Exception:
                print("⚠ Could not process image file")
        
        # Check current mode
        if repair_context.mode == SystemMode.CONVERSATIONAL:
            # Already in conversational mode - provide guidance
            self.guide.provide_guidance(user_input)
            return ""
        
        # New repair request - run multi-agent workflow
        print("🤖 Activating multi-agent workflow...")
        
        # Prepare initial state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_input)],
            "user_input": user_input,
            "image_data": image_data,
            "active_agents": [],
            "completed_agents": [],
            "agent_results": {},
            "device": None,
            "problem": None,
            "user_goal": user_input,
            "next_action": "",
            "overall_confidence": 0.0,
            "ready_for_guidance": False,
            "current_manual": None,
            "current_step": 0,
            "conversation_history": []
        }
        
        # Run the workflow
        try:
            final_state = self.workflow.invoke(initial_state)
            return self._format_workflow_response(final_state)
            
        except Exception as e:
            print(f"❌ Workflow error: {str(e)}")
            return f"Sorry, I encountered an error while analyzing your repair request: {str(e)}"
    
    def _format_workflow_response(self, state: AgentState) -> str:
        """Format the workflow response for the user"""
        
        response = "🔧 *Multi-Agent Analysis Complete!*\n\n"
        
        # Show agent results
        agent_results = state.get("agent_results", {})
        
        if "vision" in agent_results:
            vision_summary = agent_results["vision"].get("summary", "Image analyzed")
            response += f"👁 *Vision*: {vision_summary[:100]}...\n"
        
        if "research" in agent_results:
            research_summary = agent_results["research"].get("summary", "Resources found")  
            response += f"📚 *Research*: {research_summary}\n"
            
        if "planning" in agent_results:
            planning_summary = agent_results["planning"].get("summary", "Strategy created")
            response += f"📋 *Planning*: {planning_summary}\n"
        
        # Show confidence and next steps
        confidence = state.get("overall_confidence", 0.0)
        response += f"\n🎯 *Confidence*: {confidence:.1%}\n"
        
        if state.get("ready_for_guidance"):
            response += "\n✅ *Ready to start!* I'll now guide you step-by-step. Just ask me what to do next!"
            # Switch to conversational mode
            repair_context.mode = SystemMode.CONVERSATIONAL
            
            # Update global context with workflow results
            repair_context.current_manual = state.get("current_manual")
            repair_context.agent_findings = agent_results
            repair_context.confidence_level = confidence
            repair_context.device = state.get("device")
            repair_context.problem = state.get("problem")
            
        else:
            response += "\n🔍 *Need more information* - Let me know more details about your device and the issue."
        
        return response
    
    def get_status(self) -> str:
        """Get current system status"""
        status = f"*Current Status:*\n"
        status += f"Mode: {repair_context.mode.value}\n"
        status += f"Device: {repair_context.device or 'Unknown'}\n"
        status += f"Problem: {repair_context.problem or 'Unknown'}\n"
        status += f"Confidence: {repair_context.confidence_level:.1%}\n"
        status += f"Step: {repair_context.current_step}\n"
        
        if repair_context.safety_concerns:
            status += f"⚠ Safety: {', '.join(repair_context.safety_concerns)}\n"
        
        return status
    
    def reset(self):
        """Reset the system for a new repair"""
        global repair_context
        repair_context = RepairContext()
        print("🗑 System reset. Ready for new repair!")

async def main():
    """Main interactive loop"""
    print("🔧 *Agentic Repair Assistant*")
    print("I switch between multi-agent analysis and step-by-step guidance!")
    print("Commands: 'status' | 'reset' | 'exit' | provide image path + description\n")

    system = RepairAssistantSystem()
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("👋 Good luck with your repair!")
            break
        elif user_input.lower() == "status":
            print(system.get_status())
            continue
        elif user_input.lower() == "reset":
            system.reset()
            continue
        elif not user_input:
            continue
        
        # Check if input is an image path
        image_path = None
        if os.path.exists(user_input) and os.path.isfile(user_input):
            image_path = user_input
            user_input = input("Describe what needs repair: ").strip()
            if not user_input:
                continue
        
        try:
            response = system.process_user_input(user_input, image_path)
            if response:
                print(f"\n🤖 {response}\n")
            print("-" * 50)
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("Please try again or type 'reset' to start over.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")