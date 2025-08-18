#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
True Agentic Multi-Agent Repair Assistant
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
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

# Image processing
import base64
from PIL import Image

# Import tools
from tools import MyFixitDataset, search_repair_manuals, get_repair_steps, search_ifixit_guides, get_ifixit_guide_steps, search_wikihow, search_manualslib

# Configuration
class Config:
    MODEL_NAME = "gemma3:latest"
    OLLAMA_BASE_URL = "http://localhost:11434"
    DATASET_PATH = "MyFixit-Dataset/jsons"
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

# Agent State
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    task: str
    context: str
    agent_findings: Dict[str, Any]
    next_agents: List[str]
    confidence: float
    action_needed: str

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
        self.dataset = MyFixitDataset(Config.DATASET_PATH)
    
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
        if best_guide_id:
            detailed_steps = get_ifixit_guide_steps.invoke({"guideid": best_guide_id})
        elif not detailed_steps:
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
            "wikihow_results": wikihow_results if 'wikihow_results' in locals() else None,
            "manualslib_results": manuals_results if 'manuals_results' in locals() else None,
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

# Coordinator Agent - Manages agent collaboration and decides next steps
class CoordinatorAgent:
    """Meta-agent that coordinates other agents and makes strategic decisions"""
    
    def __init__(self):
        self.llm = ChatOllama(
            model=Config.MODEL_NAME,
            base_url=Config.OLLAMA_BASE_URL,
            temperature=0.5
        )
        self.name = "coordinator"
        
        # Initialize specialized agents
        self.vision_agent = VisionAgent()
        self.research_agent = ResearchAgent()
        self.planning_agent = PlanningAgent()
    
    def analyze_situation_and_coordinate(self, user_input: str, image_data: str = None) -> Dict[str, Any]:
        """Analyze situation and coordinate appropriate agents"""
        
        # Initial situation analysis
        situation_prompt = f"""Analyze this repair request and determine what agents should be activated:

User Request: {user_input}
Has Image: {bool(image_data)}
Current Context: {repair_context.get_context_for_agent('coordinator')}

Decide:
1. Which agents should be activated? (vision, research, planning)
2. What information do we need to gather?
3. What's the primary goal?
4. How urgent/complex is this?

Respond with agent activation plan."""

        response = self.llm.invoke([HumanMessage(content=situation_prompt)])
        coordination_plan = response.content
        print(f"[TOOL] Coordinator LLM | [INPUT] situation_prompt")
        print(f"[EXTRACTED] {coordination_plan[:500]}{'...' if len(coordination_plan) > 500 else ''}")
        
        # Activate appropriate agents based on analysis
        results = {}
        
        # Extract user intent
        repair_context.user_goal = user_input
        repair_context.problem = self._extract_problem(user_input)
        
        # Activate Vision Agent if image provided
        if image_data:
            repair_context.image_data = image_data
            results['vision'] = self.vision_agent.analyze_image(image_data, user_input)
        
        # Activate Research Agent if device/problem identified
        if repair_context.device and repair_context.problem:
            results['research'] = self.research_agent.find_repair_guide(
                repair_context.device, repair_context.problem
            )
        
        # Always activate Planning Agent to synthesize findings
        results['planning'] = self.planning_agent.create_repair_strategy()
        
        # Determine next system mode
        next_mode = self._determine_next_mode()
        repair_context.mode = next_mode
        
        coordination_results = {
            "coordination_plan": coordination_plan,
            "agent_results": results,
            "next_mode": next_mode.value,
            "ready_for_guidance": repair_context.should_switch_to_conversational(),
            "summary": f"Coordinated {len(results)} agents, ready for {next_mode.value} mode"
        }
        
        repair_context.update_findings(self.name, coordination_results)
        return coordination_results
    
    def _extract_problem(self, user_input: str) -> str:
        """Use AI to detect the required repair or modification"""
        try:
            context = repair_context.visual_analysis or ""
            llm_prompt = f"""
            You are a repair task classifier.
            Based on the user's request and any visual analysis, identify the most likely
            repair, replacement, or modification needed. Keep it short (2-5 words).
            
            User request: {user_input}
            Visual analysis: {context}
            
            Example outputs: 
            "mainboard replacement", "CPU upgrade", "screen replacement",
            "battery swap", "RAM installation", "fan cleaning"
            """
            response = self.llm.invoke([HumanMessage(content=llm_prompt)])
            problem = response.content.strip().lower()
            return problem
        except Exception:
            return "unknown issue"

    
    def _determine_next_mode(self) -> SystemMode:
        """Determine what mode the system should enter next"""
        if repair_context.should_switch_to_conversational():
            return SystemMode.CONVERSATIONAL
        elif repair_context.confidence_level < 0.5:
            return SystemMode.MULTI_AGENT  # Need more agent collaboration
        else:
            return SystemMode.CONVERSATIONAL

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
try to make the texts look like conversations, don't write long messages
"""

        response = self.llm.invoke([HumanMessage(content=guidance_prompt)])
        print(f"[TOOL] Guide LLM | [INPUT] {user_message[:100]}...")
        print(f"[EXTRACTED] {response.content[:500]}{'...' if len(response.content) > 500 else ''}")
        
        # Update conversation history
        repair_context.conversation_history.append({
            "user": user_message,
            "assistant": response.content,
            "step": repair_context.current_step
        })
        
        return response.content
    
    def _summarize_agent_findings(self) -> str:
        """Create a brief summary of key agent findings"""
        summary_parts = []
        for agent_name, findings in repair_context.agent_findings.items():
            if agent_name != "coordinator":
                summary_parts.append(f"{agent_name}: {findings.get('summary', 'No summary')}")
        return " | ".join(summary_parts)

# Main System Controller
class RepairAssistantSystem:
    """Main system that orchestrates between multi-agent and conversational modes"""
    
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.guide = ConversationalGuide()
        self.vision_processor = self._init_vision_processor()
    
    def _init_vision_processor(self):
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
        """Main entry point for processing user input"""
        
        # Handle image if provided
        image_data = None
        if image_path and os.path.exists(image_path):
            try:
                Image.open(image_path)  # Verify it's an image
                image_data = self.vision_processor.encode_image(image_path)
                if image_data:
                    print("📸 Image received and processed!")
            except Exception:
                print("⚠️ Could not process image file")
        
        # Determine current system mode and respond accordingly
        if repair_context.mode == SystemMode.LISTENING:
            # New repair request - activate multi-agent system
            print("🤖 Activating repair agents...")
            repair_context.mode = SystemMode.MULTI_AGENT
            
            coordination_results = self.coordinator.analyze_situation_and_coordinate(
                user_input, image_data
            )
            
            return self._format_multi_agent_response(coordination_results)
            
        elif repair_context.mode == SystemMode.CONVERSATIONAL:
            # Ongoing repair guidance
            return self.guide.provide_guidance(user_input)
            
        elif repair_context.mode == SystemMode.MULTI_AGENT:
            # Continue multi-agent collaboration if needed
            coordination_results = self.coordinator.analyze_situation_and_coordinate(
                user_input, image_data
            )
            return self._format_multi_agent_response(coordination_results)
        
        else:
            # Fallback to conversational mode
            repair_context.mode = SystemMode.CONVERSATIONAL
            return self.guide.provide_guidance(user_input)
    
    def _format_multi_agent_response(self, coordination_results: Dict) -> str:
        """Format the multi-agent system response for user"""
        response = "🔧 **Analysis Complete!**\n\n"
        
        # Add key findings
        agent_results = coordination_results.get("agent_results", {})
        
        if "vision" in agent_results:
            vision_findings = agent_results["vision"]
            response += f"📸 **Visual Analysis**: {vision_findings.get('summary', 'Image analyzed')}\n"
        
        if "research" in agent_results:
            research_findings = agent_results["research"]
            response += f"📚 **Research**: {research_findings.get('summary', 'Resources found')}\n"
        
        if "planning" in agent_results:
            planning_findings = agent_results["planning"]
            response += f"📋 **Plan**: Ready to guide you through the repair\n"
        
        # Indicate mode switch
        if coordination_results.get("ready_for_guidance"):
            response += f"\n✅ **Ready to start!** I'll now guide you step-by-step. Just ask me what to do next!\n"
            repair_context.mode = SystemMode.CONVERSATIONAL
        else:
            response += f"\n🔍 **Gathering more info...** I need a bit more information to help you effectively.\n"
        
        return response.strip()
    
    def get_status(self) -> str:
        """Get current system status"""
        status = f"**Current Status:**\n"
        status += f"Mode: {repair_context.mode.value}\n"
        status += f"Device: {repair_context.device or 'Unknown'}\n"
        status += f"Problem: {repair_context.problem or 'Unknown'}\n"
        status += f"Confidence: {repair_context.confidence_level:.1%}\n"
        status += f"Step: {repair_context.current_step}\n"
        
        if repair_context.safety_concerns:
            status += f"⚠️ Safety: {', '.join(repair_context.safety_concerns)}\n"
        
        return status
    
    def reset(self):
        """Reset the system for a new repair"""
        global repair_context
        repair_context = RepairContext()
        print("🗑️ System reset. Ready for new repair!")

async def main():
    """Main interactive loop"""
    print("🔧 **Agentic Repair Assistant**")
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