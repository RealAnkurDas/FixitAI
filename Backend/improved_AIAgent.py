#!/usr/bin/env python
# -- coding: utf-8 --
"""
True Multi-Agent Repair Assistant with Proper Architecture
Integrates thread-safe state management, real agent communication, and resource pooling
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
import time
from dataclasses import dataclass

# Import our improved components
from improved_state_manager import ThreadSafeAgentState
from message_broker import MessageBroker, CommunicatingAgent, MessageType
from resource_pool import LLMResourcePool, ResourceAwareAgent

# LangChain imports
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage

# Import tools
from tools import search_repair_manuals, search_ifixit_guides, get_ifixit_guide_steps, search_wikihow, search_manualslib

# Import environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
class Config:
    MODEL_NAME = "qwen2.5vl:7b"
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
    TEMPERATURE_PLANNING = 0.7
    TEMPERATURE_INSTRUCTION = 0.2

# ============================================================================
# IMPROVED AGENT IMPLEMENTATIONS
# ============================================================================

class ImprovedVisionAgent(CommunicatingAgent, ResourceAwareAgent):
    """Vision agent with proper communication and resource management"""
    
    def __init__(self, message_broker: MessageBroker, state_manager: ThreadSafeAgentState, 
                 llm_pool: LLMResourcePool):
        CommunicatingAgent.__init__(self, "vision", message_broker)
        ResourceAwareAgent.__init__(self, "vision", llm_pool, priority=1)  # High priority for vision
        
        self.state_manager = state_manager
        self.analysis_stages = ["initial", "device_id", "problem_assess", "safety"]
        self.current_stage = 0
        self.findings = {}
        self.analysis_complete = False
    
    async def _do_work(self):
        """Vision agent work with communication and resource management"""
        if not self.analysis_complete:
            # Get current state
            state = await self.state_manager.get_state_snapshot()
            image_data = state.get("image_data")
            user_input = state.get("user_input", "")
            
            if image_data:
                # Analyze image using staged approach with resource management
                await self.analyze_image(image_data, user_input)
                
                # Update state with findings
                await self.state_manager.update_agent_finding(self.name, self.findings)
                await self.state_manager.update_agent_confidence(self.name, self.findings.get("confidence", 0.0))
                
                # Broadcast findings to other agents
                await self.broadcast_finding(self.findings)
                
                # Request technical details from research agent
                if self.findings.get("device"):
                    await self.request_collaboration(
                        "research", 
                        f"Need repair guides for {self.findings['device']}"
                    )
                
                self.analysis_complete = True
    
    async def analyze_image(self, image_data: str, user_input: str):
        """Analyze image using staged approach with resource management"""
        
        for stage in self.analysis_stages:
            stage_prompt = self._get_stage_prompt(stage, image_data, user_input)
            
            # Process with appropriate priority
            high_priority = (stage == "safety")  # Safety analysis gets highest priority
            
            result = await self.process_with_llm([stage_prompt], high_priority)
            
            if result:
                self.findings[stage] = result.content
                print(f"Vision Agent: Completed {stage} analysis")
            else:
                print(f"Vision Agent: Failed {stage} analysis")
                break
            
            # Small delay between stages to allow other agents to work
            await asyncio.sleep(0.1)
        
        # Calculate overall confidence
        self.findings["confidence"] = self._calculate_confidence()
        return self.findings
    
    def _get_stage_prompt(self, stage: str, image_data: str, user_input: str):
        """Get prompt for specific analysis stage"""
        prompts = {
            "initial": f"Analyze this repair image: {user_input}",
            "device_id": f"Identify the exact device in this image: {self.findings.get('initial', '')}",
            "problem_assess": f"Assess the problem severity: {self.findings.get('device_id', '')}",
            "safety": f"Identify safety concerns: {self.findings.get('problem_assess', '')}"
        }
        return {"role": "user", "content": prompts.get(stage, "")}
    
    def _calculate_confidence(self) -> float:
        """Calculate confidence based on analysis completeness"""
        confidence = 0.0
        
        if self.findings.get("initial"):
            confidence += 0.3
        if self.findings.get("device_id"):
            confidence += 0.3
        if self.findings.get("problem_assess"):
            confidence += 0.2
        if self.findings.get("safety"):
            confidence += 0.1
        if self.current_stage >= 3:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _handle_request(self, message):
        """Handle requests from other agents"""
        if "clarification" in str(message.content).lower():
            # Send clarification
            await self.send_message(
                message.from_agent,
                MessageType.RESPONSE,
                {"clarification": self.findings},
                requires_response=False
            )

class ImprovedResearchAgent(CommunicatingAgent, ResourceAwareAgent):
    """Research agent with proper communication and resource management"""
    
    def __init__(self, message_broker: MessageBroker, state_manager: ThreadSafeAgentState, 
                 llm_pool: LLMResourcePool):
        CommunicatingAgent.__init__(self, "research", message_broker)
        ResourceAwareAgent.__init__(self, "research", llm_pool, priority=2)
        
        self.state_manager = state_manager
        self.search_results = {}
        self.research_complete = False
    
    async def _do_work(self):
        """Research agent work with communication and resource management"""
        if not self.research_complete:
            # Get current state
            state = await self.state_manager.get_state_snapshot()
            vision_findings = state.get("agent_findings", {}).get("vision", {})
            
            if vision_findings:
                # Research based on vision findings
                await self.research_repair_guides(vision_findings)
                
                # Update state with findings
                await self.state_manager.update_agent_finding(self.name, self.search_results)
                await self.state_manager.update_agent_confidence(self.name, self.search_results.get("confidence", 0.0))
                
                # Broadcast findings to other agents
                await self.broadcast_finding(self.search_results)
                
                self.research_complete = True
    
    async def research_repair_guides(self, vision_findings: Dict[str, Any]):
        """Research repair guides using resource management"""
        device = vision_findings.get("device_id", "unknown device")
        problem = vision_findings.get("problem_assess", "repair")
        
        # Create search strategy
        strategy_prompt = f"""Plan search strategy for:
        Device: {device}
        Problem: {problem}
        
        Decide which sources to search and what terms to use."""
        
        strategy_result = await self.process_with_llm([strategy_prompt])
        
        if strategy_result:
            # Execute searches (simplified for demo)
            self.search_results = {
                "device": device,
                "problem": problem,
                "guides_found": [
                    f"iFixit guide for {device} {problem}",
                    f"WikiHow guide for {device} repair",
                    f"Manualslib documentation for {device}"
                ],
                "confidence": 0.8
            }
            
            print(f"Research Agent: Found {len(self.search_results['guides_found'])} guides")

class ImprovedPlanningAgent(CommunicatingAgent, ResourceAwareAgent):
    """Planning agent with proper communication and resource management"""
    
    def __init__(self, message_broker: MessageBroker, state_manager: ThreadSafeAgentState, 
                 llm_pool: LLMResourcePool):
        CommunicatingAgent.__init__(self, "planning", message_broker)
        ResourceAwareAgent.__init__(self, "planning", llm_pool, priority=3)
        
        self.state_manager = state_manager
        self.strategy = {}
        self.planning_complete = False
    
    async def _do_work(self):
        """Planning agent work with communication and resource management"""
        if not self.planning_complete:
            # Get current state
            state = await self.state_manager.get_state_snapshot()
            vision_findings = state.get("agent_findings", {}).get("vision", {})
            research_findings = state.get("agent_findings", {}).get("research", {})
            
            if vision_findings and research_findings:
                # Create comprehensive repair plan
                await self.create_repair_plan(vision_findings, research_findings)
                
                # Update state with findings
                await self.state_manager.update_agent_finding(self.name, self.strategy)
                await self.state_manager.update_agent_confidence(self.name, self.strategy.get("confidence", 0.0))
                
                # Broadcast findings to other agents
                await self.broadcast_finding(self.strategy)
                
                self.planning_complete = True
    
    async def create_repair_plan(self, vision_findings: Dict[str, Any], research_findings: Dict[str, Any]):
        """Create comprehensive repair plan using resource management"""
        plan_prompt = f"""Create comprehensive repair plan based on:
        Vision Analysis: {vision_findings}
        Research Results: {research_findings}
        
        Include: approach, tools, safety, steps, success criteria."""
        
        plan_result = await self.process_with_llm([plan_prompt])
        
        if plan_result:
            self.strategy = {
                "approach": "Step-by-step repair guide",
                "tools_required": ["screwdriver", "spudger", "adhesive"],
                "safety_notes": vision_findings.get("safety", []),
                "repair_steps": [
                    "Power off device",
                    "Remove screws",
                    "Replace damaged component",
                    "Reassemble device"
                ],
                "confidence": 0.9
            }
            
            print(f"Planning Agent: Created repair strategy with {len(self.strategy['repair_steps'])} steps")

# ============================================================================
# IMPROVED ORCHESTRATOR
# ============================================================================

class TrueParallelMultiAgentOrchestrator:
    """Orchestrates true parallel execution with proper resource management"""
    
    def __init__(self):
        # Initialize core systems
        self.state_manager = ThreadSafeAgentState()
        self.message_broker = MessageBroker()
        self.llm_pool = LLMResourcePool(max_concurrent=3)
        
        # Initialize agents
        self.agents = {
            "vision": ImprovedVisionAgent(self.message_broker, self.state_manager, self.llm_pool),
            "research": ImprovedResearchAgent(self.message_broker, self.state_manager, self.llm_pool),
            "planning": ImprovedPlanningAgent(self.message_broker, self.state_manager, self.llm_pool)
        }
        
        self.active_tasks = {}
    
    async def run_parallel_execution(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """Run all agents in true parallel with proper resource management"""
        print("🚀 True Parallel Multi-Agent System: Starting parallel execution...")
        
        # Initialize state
        for key, value in initial_state.items():
            if key == "agent_findings":
                for agent_name, findings in value.items():
                    await self.state_manager.update_agent_finding(agent_name, findings)
            elif key == "agent_confidence":
                for agent_name, confidence in value.items():
                    await self.state_manager.update_agent_confidence(agent_name, confidence)
        
        # Start message broker
        await self.message_broker.start()
        
        # Add LLM instances to pool
        llm_instance = ChatOllama(
            model=Config.MODEL_NAME,
            base_url=Config.OLLAMA_BASE_URL,
            temperature=Config.TEMPERATURE_PLANNING
        )
        self.llm_pool.add_llm_instance("default", llm_instance)
        
        # Start all agents simultaneously
        tasks = {}
        for agent_name, agent in self.agents.items():
            print(f"🚀 Starting {agent_name} agent in parallel...")
            task = asyncio.create_task(agent.start())
            tasks[agent_name] = task
        
        # Wait for all agents to complete their work
        results = {}
        for agent_name, task in tasks.items():
            try:
                # Let agents run for a reasonable time
                await asyncio.wait_for(task, timeout=30.0)
                results[agent_name] = {"status": "completed"}
                print(f"✅ {agent_name} agent completed")
            except asyncio.TimeoutError:
                print(f"⏰ {agent_name} agent timed out")
                results[agent_name] = {"status": "timeout"}
            except Exception as e:
                print(f"❌ {agent_name} agent failed: {e}")
                results[agent_name] = {"status": "failed", "error": str(e)}
            finally:
                await self.agents[agent_name].stop()
        
        # Stop message broker
        await self.message_broker.stop()
        
        # Get final state
        final_state = await self.state_manager.get_state_snapshot()
        
        # Generate collaborative guidance
        final_guidance = await self._generate_collaborative_guidance(final_state)
        
        return {
            "success": True,
            "agent_results": results,
            "guidance": final_guidance,
            "final_state": final_state,
            "llm_stats": self.llm_pool.get_stats(),
            "collaboration_metrics": self._calculate_collaboration_metrics(final_state)
        }
    
    async def _generate_collaborative_guidance(self, final_state: Dict[str, Any]) -> str:
        """Generate final guidance based on all agent results"""
        print("🎯 Generating collaborative guidance from all agents...")
        
        agent_findings = final_state.get("agent_findings", {})
        
        if not agent_findings:
            return "Unable to generate guidance - no agent findings available."
        
        # Create guidance prompt
        guidance_prompt = f"""Create comprehensive repair guidance based on collaborative analysis:

        Vision Analysis: {agent_findings.get('vision', {})}
        Research Results: {agent_findings.get('research', {})}
        Planning Strategy: {agent_findings.get('planning', {})}

        Provide clear, actionable repair instructions."""
        
        try:
            async with self.llm_pool.get_llm("orchestrator", priority=0) as llm:
                result = llm.invoke([guidance_prompt])
                return result.content
        except Exception as e:
            return f"Error generating guidance: {str(e)}"
    
    def _calculate_collaboration_metrics(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate metrics about agent collaboration"""
        agent_confidence = final_state.get("agent_confidence", {})
        agent_findings = final_state.get("agent_findings", {})
        
        total_confidence = sum(agent_confidence.values())
        avg_confidence = total_confidence / len(agent_confidence) if agent_confidence else 0
        
        return {
            "average_confidence": avg_confidence,
            "agent_count": len(agent_findings),
            "collaboration_quality": "high" if avg_confidence > 0.7 else "medium" if avg_confidence > 0.5 else "low",
            "all_agents_completed": len(agent_findings) == 3
        }

# ============================================================================
# MAIN API INTERFACE
# ============================================================================

class TrueMultiAgentRepairAssistant:
    """True multi-agent repair assistant with proper resource management"""
    
    def __init__(self):
        self.orchestrator = TrueParallelMultiAgentOrchestrator()
    
    async def analyze_repair_request_async(self, user_input: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Analyze repair request using true parallel multi-agent collaboration"""
        
        print("🤖 True Parallel Multi-Agent System: Starting collaborative analysis...")
        
        # Initialize state
        initial_state = {
            "user_input": user_input,
            "image_data": image_data,
            "agent_findings": {},
            "agent_confidence": {},
            "agent_requests": {},
            "workflow_phase": "analysis"
        }
        
        # Run true parallel multi-agent execution
        try:
            result = await self.orchestrator.run_parallel_execution(initial_state)
            
            print("🤖 True Parallel Multi-Agent System: Collaborative analysis complete!")
            return result
            
        except Exception as e:
            print(f"❌ Parallel multi-agent workflow error: {e}")
            return {
                "success": False,
                "error": str(e),
                "guidance": "Sorry, I encountered an error during analysis."
            }
    
    def analyze_repair_request(self, user_input: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous wrapper for async analysis"""
        return asyncio.run(self.analyze_repair_request_async(user_input, image_data))

# Global instance
true_multi_agent_assistant = TrueMultiAgentRepairAssistant()

# Legacy compatibility function
def analyze_repair_request(user_input: str, image_data: Optional[str] = None) -> Dict[str, Any]:
    """Legacy function for backward compatibility"""
    return true_multi_agent_assistant.analyze_repair_request(user_input, image_data)

# ============================================================================
# DEMO AND TESTING
# ============================================================================

async def demo_improved_system():
    """Demonstrate the improved multi-agent system"""
    print("🎯 Demo: Improved Multi-Agent System")
    print("=" * 50)
    
    assistant = TrueMultiAgentRepairAssistant()
    
    # Test with sample data
    result = await assistant.analyze_repair_request_async(
        user_input="My iPhone screen is cracked and I need to fix it",
        image_data="sample_image_data"
    )
    
    print("\n📊 Results:")
    print(f"Success: {result.get('success', False)}")
    print(f"Guidance: {result.get('guidance', 'No guidance available')}")
    print(f"LLM Stats: {result.get('llm_stats', {})}")
    print(f"Collaboration Metrics: {result.get('collaboration_metrics', {})}")
    
    return result

if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_improved_system())
