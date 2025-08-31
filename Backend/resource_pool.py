import asyncio
from typing import Dict, List, Any, Optional
import time
from dataclasses import dataclass
from contextlib import asynccontextmanager

@dataclass
class LLMRequest:
    """Request for LLM processing"""
    agent_name: str
    messages: List[Any]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    priority: int = 1  # Lower number = higher priority
    timestamp: float = 0.0

class LLMResourcePool:
    """Thread-safe resource pool for LLM access"""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.request_queue = asyncio.PriorityQueue()
        self.active_requests: Dict[str, LLMRequest] = {}
        self.llm_instances = {}
        self._stats = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "queue_waits": []
        }
    
    def add_llm_instance(self, name: str, llm_instance):
        """Add LLM instance to the pool"""
        self.llm_instances[name] = llm_instance
        print(f"LLM Pool: Added {name} instance")
    
    @asynccontextmanager
    async def get_llm(self, agent_name: str, priority: int = 1):
        """Context manager for getting LLM access with queuing"""
        request = LLMRequest(
            agent_name=agent_name,
            messages=[],
            priority=priority,
            timestamp=time.time()
        )
        
        # Add to queue with priority
        await self.request_queue.put((priority, time.time(), request))
        self._stats["total_requests"] += 1
        
        # Wait for semaphore (concurrent access control)
        async with self.semaphore:
            # Get from queue (FIFO within same priority)
            _, _, queued_request = await self.request_queue.get()
            
            queue_wait_time = time.time() - queued_request.timestamp
            self._stats["queue_waits"].append(queue_wait_time)
            
            try:
                self.active_requests[agent_name] = queued_request
                
                # Get appropriate LLM instance (round-robin or least loaded)
                llm_instance = self._get_available_llm()
                
                print(f"LLM Pool: {agent_name} acquired LLM (waited {queue_wait_time:.2f}s)")
                yield llm_instance
                
                self._stats["completed_requests"] += 1
                
            except Exception as e:
                self._stats["failed_requests"] += 1
                print(f"LLM Pool: Error for {agent_name}: {e}")
                raise
            finally:
                # Clean up
                if agent_name in self.active_requests:
                    del self.active_requests[agent_name]
                self.request_queue.task_done()
                print(f"LLM Pool: {agent_name} released LLM")
    
    def _get_available_llm(self):
        """Get available LLM instance"""
        if "default" in self.llm_instances:
            return self.llm_instances["default"]
        elif self.llm_instances:
            return next(iter(self.llm_instances.values()))
        else:
            raise RuntimeError("No LLM instances available")
    
    async def process_with_retry(self, agent_name: str, messages: List[Any], 
                               max_retries: int = 3, priority: int = 1):
        """Process request with automatic retry logic"""
        for attempt in range(max_retries):
            try:
                async with self.get_llm(agent_name, priority) as llm:
                    result = llm.invoke(messages)
                    return result
            except Exception as e:
                print(f"LLM Pool: Attempt {attempt + 1} failed for {agent_name}: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        avg_wait = sum(self._stats["queue_waits"]) / len(self._stats["queue_waits"]) if self._stats["queue_waits"] else 0
        
        return {
            "active_requests": len(self.active_requests),
            "queue_size": self.request_queue.qsize(),
            "total_requests": self._stats["total_requests"],
            "completed_requests": self._stats["completed_requests"],
            "failed_requests": self._stats["failed_requests"],
            "average_queue_wait": avg_wait,
            "success_rate": (self._stats["completed_requests"] / max(self._stats["total_requests"], 1)) * 100
        }

# Improved agent base class with resource pool
class ResourceAwareAgent:
    """Agent that properly uses LLM resource pool"""
    
    def __init__(self, name: str, llm_pool: LLMResourcePool, priority: int = 1):
        self.name = name
        self.llm_pool = llm_pool
        self.priority = priority
        self.processing_stats = {
            "llm_calls": 0,
            "total_processing_time": 0.0
        }
    
    async def process_with_llm(self, messages: List[Any], high_priority: bool = False):
        """Process messages using the LLM pool"""
        priority = 0 if high_priority else self.priority
        start_time = time.time()
        
        try:
            result = await self.llm_pool.process_with_retry(
                self.name, 
                messages, 
                priority=priority
            )
            
            processing_time = time.time() - start_time
            self.processing_stats["llm_calls"] += 1
            self.processing_stats["total_processing_time"] += processing_time
            
            return result
            
        except Exception as e:
            print(f"Agent {self.name}: LLM processing failed: {e}")
            return None
    
    def get_processing_stats(self):
        """Get agent's processing statistics"""
        avg_time = (self.processing_stats["total_processing_time"] / 
                   max(self.processing_stats["llm_calls"], 1))
        
        return {
            "agent": self.name,
            "llm_calls": self.processing_stats["llm_calls"],
            "average_processing_time": avg_time,
            "total_processing_time": self.processing_stats["total_processing_time"]
        }

# Example improved vision agent with resource management
class ResourceAwareVisionAgent(ResourceAwareAgent):
    """Vision agent with proper resource management"""
    
    def __init__(self, llm_pool: LLMResourcePool):
        super().__init__("vision", llm_pool, priority=1)  # High priority for vision
        self.analysis_stages = ["initial", "device_id", "problem_assess", "safety"]
        self.current_stage = 0
        self.findings = {}
    
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

# Usage example
async def demo_resource_management():
    """Demonstrate resource pool usage"""
    from langchain_ollama import ChatOllama
    
    # Create resource pool
    llm_pool = LLMResourcePool(max_concurrent=2)
    
    # Add LLM instances
    llm_pool.add_llm_instance("default", ChatOllama(model="qwen2.5vl:7b"))
    
    # Create agents
    vision_agent = ResourceAwareVisionAgent(llm_pool)
    
    # Simulate concurrent processing
    tasks = []
    for i in range(3):
        task = vision_agent.analyze_image(f"image_data_{i}", f"repair request {i}")
        tasks.append(task)
    
    # Wait for all to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Print statistics
    print("Resource Pool Stats:", llm_pool.get_stats())
    print("Agent Stats:", vision_agent.get_processing_stats())
    
    return results
