import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import time
import json

class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    FINDING = "finding"
    COLLABORATION = "collaboration"
    URGENT = "urgent"

@dataclass
class AgentMessage:
    """Structured message between agents"""
    from_agent: str
    to_agent: str
    message_type: MessageType
    content: Any
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    requires_response: bool = False

class MessageBroker:
    """Async message broker for agent communication"""
    
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._message_handlers: Dict[str, Dict[MessageType, Callable]] = {}
        self._running = False
    
    async def start(self):
        """Start the message broker"""
        self._running = True
        print("Message Broker: Started")
    
    async def stop(self):
        """Stop the message broker"""
        self._running = False
        print("Message Broker: Stopped")
    
    def register_agent(self, agent_name: str):
        """Register an agent with the broker"""
        if agent_name not in self._queues:
            self._queues[agent_name] = asyncio.Queue(maxsize=100)
            self._message_handlers[agent_name] = {}
            print(f"Message Broker: Registered agent {agent_name}")
    
    def register_handler(self, agent_name: str, message_type: MessageType, handler: Callable):
        """Register a message handler for an agent"""
        if agent_name not in self._message_handlers:
            self._message_handlers[agent_name] = {}
        self._message_handlers[agent_name][message_type] = handler
    
    async def send_message(self, message: AgentMessage):
        """Send message to target agent"""
        if message.to_agent not in self._queues:
            print(f"Message Broker: Agent {message.to_agent} not registered")
            return
        
        try:
            await self._queues[message.to_agent].put(message)
            print(f"Message Broker: Sent {message.message_type.value} from {message.from_agent} to {message.to_agent}")
        except asyncio.QueueFull:
            print(f"Message Broker: Queue full for agent {message.to_agent}")
    
    async def receive_messages(self, agent_name: str) -> List[AgentMessage]:
        """Receive all pending messages for an agent"""
        if agent_name not in self._queues:
            return []
        
        messages = []
        queue = self._queues[agent_name]
        
        # Get all available messages without blocking
        while not queue.empty():
            try:
                message = queue.get_nowait()
                messages.append(message)
                queue.task_done()
            except asyncio.QueueEmpty:
                break
        
        return messages
    
    async def broadcast_message(self, message: AgentMessage, exclude_sender: bool = True):
        """Broadcast message to all agents"""
        for agent_name in self._queues.keys():
            if exclude_sender and agent_name == message.from_agent:
                continue
            
            broadcast_msg = AgentMessage(
                from_agent=message.from_agent,
                to_agent=agent_name,
                message_type=message.message_type,
                content=message.content,
                confidence=message.confidence
            )
            await self.send_message(broadcast_msg)

class CommunicatingAgent:
    """Base agent class with proper communication capabilities"""
    
    def __init__(self, name: str, message_broker: MessageBroker):
        self.name = name
        self.broker = message_broker
        self.broker.register_agent(name)
        self.is_running = False
        self._setup_message_handlers()
    
    def _setup_message_handlers(self):
        """Setup message handlers for different message types"""
        self.broker.register_handler(self.name, MessageType.REQUEST, self._handle_request)
        self.broker.register_handler(self.name, MessageType.RESPONSE, self._handle_response)
        self.broker.register_handler(self.name, MessageType.FINDING, self._handle_finding)
        self.broker.register_handler(self.name, MessageType.URGENT, self._handle_urgent)
    
    async def start(self):
        """Start the agent's message processing loop"""
        self.is_running = True
        await self._message_processing_loop()
    
    async def stop(self):
        """Stop the agent"""
        self.is_running = False
    
    async def send_message(self, to_agent: str, message_type: MessageType, content: Any, 
                          requires_response: bool = False):
        """Send a message to another agent"""
        message = AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            requires_response=requires_response
        )
        await self.broker.send_message(message)
    
    async def broadcast_finding(self, findings: Dict[str, Any]):
        """Broadcast findings to all other agents"""
        message = AgentMessage(
            from_agent=self.name,
            to_agent="all",
            message_type=MessageType.FINDING,
            content=findings
        )
        await self.broker.broadcast_message(message)
    
    async def request_collaboration(self, target_agent: str, request_content: str):
        """Request collaboration from specific agent"""
        await self.send_message(
            target_agent, 
            MessageType.REQUEST, 
            request_content,
            requires_response=True
        )
    
    async def _message_processing_loop(self):
        """Main message processing loop"""
        while self.is_running:
            # Process incoming messages
            messages = await self.broker.receive_messages(self.name)
            
            for message in messages:
                try:
                    handler = self.broker._message_handlers[self.name].get(message.message_type)
                    if handler:
                        await handler(message)
                    else:
                        print(f"{self.name}: No handler for {message.message_type}")
                except Exception as e:
                    print(f"{self.name}: Error processing message: {e}")
            
            # Do agent work
            await self._do_work()
            
            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.1)
    
    async def _do_work(self):
        """Override in subclasses for agent-specific work"""
        pass
    
    # Message handlers - override in subclasses
    async def _handle_request(self, message: AgentMessage):
        """Handle incoming requests"""
        print(f"{self.name}: Received request from {message.from_agent}: {message.content}")
    
    async def _handle_response(self, message: AgentMessage):
        """Handle incoming responses"""
        print(f"{self.name}: Received response from {message.from_agent}")
    
    async def _handle_finding(self, message: AgentMessage):
        """Handle incoming findings from other agents"""
        print(f"{self.name}: Received findings from {message.from_agent}")
    
    async def _handle_urgent(self, message: AgentMessage):
        """Handle urgent messages"""
        print(f"{self.name}: URGENT message from {message.from_agent}: {message.content}")

# Example usage of improved communication system
class ImprovedVisionAgent(CommunicatingAgent):
    """Vision agent with proper communication"""
    
    def __init__(self, message_broker: MessageBroker):
        super().__init__("vision", message_broker)
        self.analysis_complete = False
        self.current_findings = {}
    
    async def _do_work(self):
        """Vision agent work with communication"""
        if not self.analysis_complete:
            # Simulate analysis work
            await asyncio.sleep(0.5)
            
            self.current_findings = {
                "device": "iPhone 12",
                "problem": "cracked screen",
                "confidence": 0.85
            }
            
            # Broadcast findings to other agents
            await self.broadcast_finding(self.current_findings)
            
            # Request technical details from research agent
            await self.request_collaboration(
                "research", 
                f"Need repair guides for {self.current_findings['device']}"
            )
            
            self.analysis_complete = True
    
    async def _handle_request(self, message: AgentMessage):
        """Handle requests from other agents"""
        if "clarification" in str(message.content).lower():
            # Send clarification
            await self.send_message(
                message.from_agent,
                MessageType.RESPONSE,
                {"clarification": self.current_findings},
                requires_response=False
            )

# Usage example
async def demo_improved_communication():
    """Demonstrate improved agent communication"""
    broker = MessageBroker()
    await broker.start()
    
    # Create agents
    vision_agent = ImprovedVisionAgent(broker)
    
    # Start agents (would run in parallel)
    vision_task = asyncio.create_task(vision_agent.start())
    
    # Let them run for a bit
    await asyncio.sleep(2)
    
    # Stop agents
    await vision_agent.stop()
    await broker.stop()
    
    vision_task.cancel()
    
    print("Communication demo completed")
