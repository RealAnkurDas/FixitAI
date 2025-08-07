# 🔧 FixitAI - Mobile App Project Structure

FixitAI is a mobile-first AI-powered assistant designed to help users repair and upcycle broken items through visual input, natural language understanding, and agentic AI workflows.

## 📱 Project Overview

This is a mobile application that integrates:
- **Camera & Image Processing** - Capture and analyze broken items
- **AI-Powered Repair Guidance** - Gemini + MCP integration for intelligent repair instructions
- **Social Community** - Share successful repairs and connect with other DIY enthusiasts
- **Local Expert Matching** - Find nearby repair professionals when needed

## 🏗️ Architecture

The app follows a modular architecture with clear separation of concerns:

- **Frontend**: Mobile UI components and screens
- **Backend Services**: AI integration, data processing, and business logic
- **Core Engine**: FixitAI reasoning and instruction generation
- **Social Layer**: Community features and user interactions

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