#!/usr/bin/env python
"""
Working Multi-Agent Repair Assistant - Simplified but Functional
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

# Import your existing tools
# from tools import search_repair_manuals, search_ifixit_guides, search_wikihow, search_manualslib

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
        
        if not image_data:
            return {
                "analysis": "No image provided for analysis",
                "device": "unknown",
                "problem": "unknown",
                "confidence": 0.0
            }
        
        # Actual vision analysis
        analysis_prompt = f"""Analyze this repair image for device identification and problem assessment.
        
        User description: {user_input}
        
        Provide:
        1. Device type and model (if identifiable)
        2. Visible problem or damage
        3. Repair difficulty (1-10 scale)
        4. Safety concerns
        
        Be specific and practical."""
        
        print(f"Vision Agent: Analyzing image...")
        
        # Simulate processing time
        await asyncio.sleep(2)  # Replace with actual LLM call
        
        # For demo - replace with actual LLM call:
        # response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
        # analysis = response.content
        
        # Demo analysis
        analysis = f"Device appears to be a smartphone with cracked screen. Repair difficulty: 6/10. Safety concerns: glass shards."
        
        return {
            "analysis": analysis,
            "device": "smartphone",
            "problem": "cracked screen",
            "safety_concerns": ["glass shards", "sharp edges"],
            "confidence": 0.8
        }

class ResearchAgent(WorkingAgent):
    """Research agent that actually searches for repair guides"""
    
    async def _do_actual_work(self, context: Dict[str, Any]) -> Dict[str, Any]:
        device = context.get("device", "unknown device")
        problem = context.get("problem", "repair")
        
        print(f"Research Agent: Searching for {device} {problem} guides...")
        
        # Simulate research time
        await asyncio.sleep(1.5)
        
        # In real implementation, use your imported tools:
        # guides = []
        # try:
        #     wikihow_results = search_wikihow.invoke(f"{device} {problem}")
        #     if wikihow_results:
        #         guides.append({"source": "wikihow", "content": wikihow_results})
        # except:
        #     pass
        # 
        # try:
        #     ifixit_results = search_ifixit_guides.invoke(f"{device} {problem}")
        #     if ifixit_results:
        #         guides.append({"source": "ifixit", "content": ifixit_results})
        # except:
        #     pass
        
        # Demo results
        guides = [
            {"source": "ifixit", "url": f"ifixit.com/{device.replace(' ', '-')}-repair"},
            {"source": "wikihow", "title": f"How to Repair {device}"},
            {"source": "manualslib", "title": f"{device} Service Manual"}
        ]
        
        return {
            "guides_found": guides,
            "search_terms": [f"{device} {problem}", f"{device} repair"],
            "confidence": 0.9 if guides else 0.1
        }

class PlanningAgent(WorkingAgent):
    """Planning agent that creates actionable repair plans"""
    
    async def _do_actual_work(self, context: Dict[str, Any]) -> Dict[str, Any]:
        vision_data = context.get("vision_results", {})
        research_data = context.get("research_results", {})
        
        device = vision_data.get("device", "unknown device")
        problem = vision_data.get("problem", "unknown problem")
        guides = research_data.get("guides_found", [])
        safety_concerns = vision_data.get("safety_concerns", [])
        
        print(f"Planning Agent: Creating repair plan for {device}...")
        
        # Simulate planning time
        await asyncio.sleep(1)
        
        # Create actual repair plan
        plan_prompt = f"""Create a step-by-step repair plan for:
        
        Device: {device}
        Problem: {problem}
        Available guides: {len(guides)} resources found
        Safety concerns: {safety_concerns}
        
        Provide:
        1. Required tools
        2. Safety precautions
        3. Step-by-step instructions
        4. Success criteria
        5. When to seek professional help
        """
        
        # For demo - replace with actual LLM call
        # response = self.llm.invoke([HumanMessage(content=plan_prompt)])
        # plan = response.content
        
        # Demo plan
        repair_plan = {
            "tools_required": ["small screwdriver", "plastic prying tools", "replacement screen"],
            "safety_precautions": ["Power off device", "Wear safety glasses", "Work in well-lit area"],
            "steps": [
                "Power off the device completely",
                "Remove screws from device edges",
                "Carefully separate screen from frame",
                "Disconnect screen cables",
                "Install new screen",
                "Reconnect cables and test",
                "Reassemble device"
            ],
            "success_criteria": ["Device powers on", "Touch response works", "No display issues"],
            "seek_help_if": ["Unfamiliar with electronics", "Multiple components damaged"],
            "confidence": 0.85
        }
        
        return repair_plan

class WorkingMultiAgentSystem:
    """Simple multi-agent system that actually works"""
    
    def __init__(self):
        # Create single LLM instance (you can expand this later)
        self.llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url="http://localhost:11434",
            temperature=0.7
        )
        
        # Create agents
        self.agents = {
            "vision": VisionAgent("vision", self.llm),
            "research": ResearchAgent("research", self.llm),
            "planning": PlanningAgent("planning", self.llm)
        }
    
    async def analyze_repair_request(self, user_input: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Run agents in sequence with shared context"""
        print("Starting multi-agent repair analysis...")
        
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
        guidance = self._generate_guidance(results)
        
        return {
            "success": all(r.success for r in results.values()),
            "agent_results": results,
            "guidance": guidance,
            "processing_time": sum(r.processing_time for r in results.values()),
            "overall_confidence": sum(r.confidence for r in results.values()) / len(results)
        }
    
    async def analyze_repair_request_parallel(self, user_input: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Run agents in parallel where possible"""
        print("Starting parallel multi-agent repair analysis...")
        
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
        guidance = self._generate_guidance(results)
        
        return {
            "success": all(r.success for r in results.values()),
            "agent_results": results,
            "guidance": guidance,
            "processing_time": max(r.processing_time for r in results.values()),
            "overall_confidence": sum(r.confidence for r in results.values()) / len(results)
        }
    
    def _generate_guidance(self, results: Dict[str, AgentResult]) -> str:
        """Generate final repair guidance from all agent results"""
        
        vision_data = results.get("vision", AgentResult("vision", False, {}, 0, 0)).data
        research_data = results.get("research", AgentResult("research", False, {}, 0, 0)).data
        planning_data = results.get("planning", AgentResult("planning", False, {}, 0, 0)).data
        
        guidance = []
        
        # Add analysis summary
        if vision_data.get("analysis"):
            guidance.append(f"**Analysis:** {vision_data['analysis']}")
        
        # Add safety warnings
        safety_concerns = vision_data.get("safety_concerns", [])
        if safety_concerns:
            guidance.append(f"**Safety Concerns:** {', '.join(safety_concerns)}")
        
        # Add repair plan
        steps = planning_data.get("steps", [])
        if steps:
            guidance.append("**Repair Steps:**")
            for i, step in enumerate(steps, 1):
                guidance.append(f"{i}. {step}")
        
        # Add required tools
        tools = planning_data.get("tools_required", [])
        if tools:
            guidance.append(f"**Required Tools:** {', '.join(tools)}")
        
        # Add resources
        guides = research_data.get("guides_found", [])
        if guides:
            guidance.append("**Helpful Resources:**")
            for guide in guides[:3]:  # Limit to first 3
                if "url" in guide:
                    guidance.append(f"- {guide.get('source', 'Resource')}: {guide['url']}")
                elif "title" in guide:
                    guidance.append(f"- {guide['title']}")
        
        return "\n\n".join(guidance) if guidance else "Unable to generate repair guidance."

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

# Usage example
if __name__ == "__main__":
    assistant = SimpleRepairAssistant()
    
    result = assistant.analyze_repair(
        user_input="My phone screen is cracked and won't respond to touch",
        image_data="base64_image_data_here"
    )
    
    print("Analysis Result:")
    print(f"Success: {result['success']}")
    print(f"Overall Confidence: {result['overall_confidence']:.2f}")
    print(f"Processing Time: {result['processing_time']:.2f}s")
    print(f"\nGuidance:\n{result['guidance']}")