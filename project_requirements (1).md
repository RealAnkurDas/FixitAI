# 📄 FixitAI - Project Requirements

FixitAI is a mobile-first AI-powered assistant designed to help users repair and upcycle broken items. It integrates visual input, natural language understanding, and agentic AI to guide users through DIY repair workflows — with fallback to human repair assistance and community sharing.

---

## 🧭 High-Level User Journey

### 1. App Entry Flow
- On app launch:
  - Load authentication screen (Login / Sign Up)
  - Post-login landing page includes:
    - **Fixing Workflow Hub**
    - **Social Media Feed**
    - **User Profile**

### 2. Core Fixing Workflow (FixitAI Engine)
#### Step-by-step flow based on user interaction and AI assistance:
1. **Camera Loads**: User takes a picture of the broken item.
2. **User Describes the Problem**: Text or voice input.
3. **Problem & Image sent to Gemini → MCP**: Gemini acts as orchestrator, MCP as the core reasoning engine.
4. **MCP Searches**:
   - Web sources
   - AIFIXIT database
   - Other structured repair guides
5. **Solution returned to Gemini**.
6. **Difficulty Rating System** determines:
   - Can the average user fix this?
     - **Yes** → Instructions provided
     - **No** → Offer local repair help
7. **Instruction Loop**:
   - User follows steps, sends updates
   - If unresolved, loop continues
   - If resolved:
     - Task termination
     - Post shared on social media (optional)
     - User feedback requested

### 3. Social Media Interaction Flow
- Feed loads community posts: images, repair stories, profiles
- Post view includes:
  - Image + Description
  - Repair narrative ("How it was done")
  - Account details
  - Options to **like**, **comment**, **follow**

---

## 🧠 Core System Components

| Module                  | Responsibility                                                  |
|--------------------------|------------------------------------------------------------------|
| `camera_module`          | Capture image input from user                                   |
| `voice_text_input`       | Convert user speech to text                                     |
| `gemini_agent`           | Orchestrates between UI and backend reasoning engine            |
| `mcp_core`               | Agentic reasoning; retrieves, composes repair instructions       |
| `difficulty_rating`      | Determines complexity for user capability triage                |
| `instruction_feedback`   | Monitors progress; processes user updates and satisfaction       |
| `local_fix_finder`       | Suggests nearby experts if repair is not DIY-friendly            |
| `social_sharing`         | Posts successful fixes to community                             |
| `user_feedback_module`   | Collects feedback for AI performance evaluation                  |

---

## 🔐 User Flow Branches

- **Resolved**: Task complete → Share to feed → Ask for feedback
- **Not Resolved**: Continue instructions OR escalate to human help
- **Too Complex**: Gemini gives user the choice:
  - Attempt anyway
  - Find a nearby expert

---

## 🔄 Feedback Loops

- Post-repair feedback: “Was this helpful?” → Why?
- Repair difficulty helps tune model suggestions
- Social validation (likes/comments) informs solution quality

---

## 🧩 Dependencies & APIs (To Be Scoped in Detail)

- Vision-to-text pipeline (image analysis)
- Natural language understanding (voice & typed)
- Web scraping or RAG pipeline (for repair info)
- Location-based services (local fixer matching)
- Social media layer (posts, profiles, interactions)

---

## 📌 MVP Scope

- [ ] Camera + Problem Intake (Text + Image)
- [ ] Gemini ↔ MCP integration
- [ ] Instruction loop with feedback handling
- [ ] Difficulty rating mechanism
- [ ] Social media post template for successful fixes
- [ ] Feedback collection after task