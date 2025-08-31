import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import threading
import json
from copy import deepcopy

@dataclass
class ThreadSafeAgentState:
    """Thread-safe state management for multi-agent systems"""
    
    def __init__(self):
        self._state: Dict[str, Any] = {
            "user_input": "",
            "image_data": None,
            "agent_findings": {},
            "agent_confidence": {},
            "agent_requests": {},
            "workflow_phase": "analysis"
        }
        self._lock = asyncio.Lock()
        self._subscribers: Dict[str, list] = {}
    
    async def update_agent_finding(self, agent_name: str, findings: Dict[str, Any]):
        """Thread-safe agent findings update with notifications"""
        async with self._lock:
            if "agent_findings" not in self._state:
                self._state["agent_findings"] = {}
            
            self._state["agent_findings"][agent_name] = deepcopy(findings)
            
            # Notify subscribers
            await self._notify_subscribers(f"finding_updated_{agent_name}", findings)
    
    async def update_agent_confidence(self, agent_name: str, confidence: float):
        """Thread-safe confidence update"""
        async with self._lock:
            if "agent_confidence" not in self._state:
                self._state["agent_confidence"] = {}
            self._state["agent_confidence"][agent_name] = confidence
    
    async def add_agent_request(self, from_agent: str, to_agent: str, request: str):
        """Thread-safe request addition"""
        async with self._lock:
            if "agent_requests" not in self._state:
                self._state["agent_requests"] = {}
            if to_agent not in self._state["agent_requests"]:
                self._state["agent_requests"][to_agent] = []
            
            self._state["agent_requests"][to_agent].append({
                "from": from_agent,
                "request": request,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Notify the target agent
            await self._notify_subscribers(f"request_{to_agent}", request)
    
    async def get_state_snapshot(self) -> Dict[str, Any]:
        """Get thread-safe state snapshot"""
        async with self._lock:
            return deepcopy(self._state)
    
    async def subscribe_to_updates(self, agent_name: str, event_type: str, callback):
        """Subscribe to state updates"""
        async with self._lock:
            key = f"{event_type}_{agent_name}"
            if key not in self._subscribers:
                self._subscribers[key] = []
            self._subscribers[key].append(callback)
    
    async def _notify_subscribers(self, event_key: str, data: Any):
        """Notify subscribers of state changes"""
        if event_key in self._subscribers:
            tasks = []
            for callback in self._subscribers[event_key]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(data))
                else:
                    # Run sync callbacks in thread pool
                    tasks.append(asyncio.get_event_loop().run_in_executor(None, callback, data))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
