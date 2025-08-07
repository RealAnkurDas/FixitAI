# 🔧 FixitAI API Documentation

This document describes the API endpoints and services for the FixitAI mobile application.

## 📋 Overview

The FixitAI API provides endpoints for:
- **Authentication & User Management**
- **Repair Workflow Processing**
- **AI Analysis & Instruction Generation**
- **Social Community Features**
- **Local Expert Finding**

## 🏗️ Architecture

### Core Services
- **Gemini Agent**: Orchestrates AI interactions
- **MCP Service**: Core reasoning and instruction generation
- **Camera Module**: Image processing and analysis
- **Voice/Text Input**: Natural language processing
- **Social Sharing**: Community features
- **Local Fix Finder**: Expert matching

### API Base URL
```
Development: http://localhost:3000/api/v1
Production: https://api.fixitai.com/v1
```

## 🔐 Authentication

All API requests require authentication via JWT tokens.

### Headers
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

## 📡 Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh token

### Repairs
- `POST /repairs` - Create new repair request
- `GET /repairs` - Get user's repairs
- `GET /repairs/:id` - Get specific repair
- `PUT /repairs/:id` - Update repair
- `DELETE /repairs/:id` - Delete repair
- `POST /repairs/analyze` - Analyze repair request

### AI Services
- `POST /ai/gemini` - Gemini AI processing
- `POST /ai/mcp` - MCP reasoning engine
- `POST /ai/analysis` - Image and text analysis

### Social
- `GET /social/posts` - Get community posts
- `POST /social/posts` - Create new post
- `POST /social/likes` - Like/unlike post
- `POST /social/comments` - Comment on post

### Experts
- `GET /experts/search` - Search for local experts
- `GET /experts/:id` - Get expert details
- `POST /experts/:id/book` - Book consultation

## 📊 Response Format

All API responses follow this format:

```json
{
  "success": true,
  "data": {},
  "message": "Operation successful",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🚨 Error Handling

Errors are returned with appropriate HTTP status codes:

```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🔧 Rate Limiting

- **Standard**: 100 requests per minute
- **AI Endpoints**: 10 requests per minute
- **Image Upload**: 5 requests per minute

## 📝 Examples

### Create Repair Request
```bash
curl -X POST /repairs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Broken Phone Screen",
    "description": "Cracked screen on iPhone 12",
    "image": "base64_encoded_image",
    "itemType": "electronics"
  }'
```

### Analyze Repair
```bash
curl -X POST /repairs/analyze \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_encoded_image",
    "description": "Screen is cracked and unresponsive"
  }'
```

---

*For detailed endpoint documentation, see individual service files.*
