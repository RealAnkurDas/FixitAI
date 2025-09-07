# FixitAI Backend

The backend system for FixitAI, a multi-agent repair assistance platform that combines LLM-powered analysis with external data sources to provide comprehensive repair guidance.

## Architecture Overview

The backend consists of three main components:

### 1. **FixAgent.py** - Core Multi-Agent System
- **LangGraph-based workflow** orchestrating multiple specialized agents
- **LLM Integration**: Uses Qwen2.5vl:7b and Llama3.1:8b models via Ollama
- **Agent Types**:
  - `conversation_node`: Handles user queries and context management
  - `examine_node`: Analyzes uploaded images using vision models
  - `search_node`: Coordinates external data source searches
  - `synthesize_node`: Combines findings into comprehensive repair guidance

### 2. **fixagent_api.py** - FastAPI Web Service
- **REST API endpoints** for Flutter frontend communication
- **Key endpoints**:
  - `/api/chat`: Main conversation endpoint
  - `/api/upload`: Image upload and analysis
  - `/api/local-repair`: Local repair shop search
  - `/api/upcycle-ideas`: Creative upcycling suggestions
- **User Management**: Firebase Auth integration with user-specific query storage

### 3. **modules/** - Specialized Search Tools
- **External Data Sources**: Reddit, Medium, WikiHow, iFixit, StackExchange, ManualsLib
- **Local Services**: Google Maps integration for repair shop discovery
- **AI Tools**: Tavily search, upcycling idea generation
- **User Storage**: LocalUserStorage for query persistence

## Data Flow

1. **User Query** → FastAPI endpoint
2. **Query Processing** → FixAgent workflow
3. **Multi-Source Search** → External APIs and web scraping
4. **LLM Analysis** → Context synthesis and repair guidance
5. **Response Generation** → Structured JSON output to frontend

## Setup
1. clone the repo
2. make an ngrok account using the link https://ngrok.com and follow the instructions for your recommended OS and activate the static link
3. install and activate the virtual environment
```
> py -m venv venv

# for Windows
> /venv/Scripts/activate

# for Linux and MacOS
> source <path_to_venv>/bin/activate 
```
4. Install the modules from `requirements.txt`
```
> pip install -r requirements.txt
```
5. Install `gemma3:latest` from ollama, if you haven't installed ollama yet, install it from this link: https://ollama.com/download
```
ollama pull gemma3:latest
```

## Run the backend
1. Enter the following command
```
> python api.py
```
2. to test this, go to `streamlittest.py`, switch the API_URL to your static Ngrok URL, and run the following command
```
> streamlit run streamlittest.py
```