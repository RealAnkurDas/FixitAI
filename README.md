# 🔧 FixitAI - Multi-Agent Repair Assistance Platform

FixitAI is a comprehensive repair assistance platform that combines AI-powered analysis with community-driven repair guidance. The system uses a multi-agent architecture to provide intelligent repair suggestions, local service discovery, and creative upcycling ideas.

## 📱 Project Overview

FixitAI integrates multiple technologies to deliver comprehensive repair assistance:

- **Multi-Agent AI System** - LangGraph-based workflow with specialized agents
- **LLM Integration** - Qwen2.5vl:7b model via Ollama
- **External Data Sources** - iFixit, WikiHow, Medium, Reddit, StackExchange, ManualsLib
- **Local Services** - Google Maps integration for repair shop discovery
- **Social Community** - Firebase-based social features for sharing repair experiences
- **Mobile Interface** - Flutter-based cross-platform mobile application

## 🏗️ System Architecture

### **Backend (Python/FastAPI)**
- **FixAgent.py**: Core multi-agent system using LangGraph
- **fixagent_api.py**: RESTful API endpoints for frontend communication
- **modules/**: Specialized search tools and utilities
- **json_schemas.py**: Structured data handling and LLM response processing

### **Frontend (Flutter)**
- **Authentication**: Firebase Auth integration
- **Main Screens**: Home, conversation, profile, social features
- **Services**: API communication, local storage, social features
- **Models**: User, post, and repair data structures

### **Data Flow**
1. **User Input** → Flutter UI → FastAPI endpoints
2. **Query Processing** → FixAgent multi-agent workflow
3. **External Search** → Multiple data sources (iFixit, WikiHow, etc.)
4. **LLM Analysis** → Context synthesis and repair guidance
5. **Response Generation** → Structured JSON to Flutter frontend

## 🚀 Getting Started

1. Choose your mobile framework (React Native, Flutter, etc.)
2. Set up the project structure as defined in the directories below
3. Configure environment variables for API keys
4. Install dependencies for your chosen framework
5. Start development!

## 📋 Environment Variables Needed

```
GEMINI_API_KEY=your_gemini_api_key
MCP_SERVER_URL=your_mcp_server_url
DATABASE_URL=your_database_url
STORAGE_BUCKET=your_storage_bucket
LOCATION_API_KEY=your_location_api_key
```

## 🔧 Core Features

- **Smart Camera Integration** - Capture and analyze broken items
- **AI-Powered Repair Instructions** - Step-by-step guidance with difficulty ratings
- **Voice & Text Input** - Natural language problem description
- **Social Community** - Share repairs and connect with others
- **Local Expert Finder** - Find nearby repair professionals
- **Feedback System** - Continuous improvement through user feedback

---

*This structure is designed to be framework-agnostic and can be adapted for React Native, Flutter, or other mobile frameworks.*