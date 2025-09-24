# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Character standing image generation app (Standing-Set-5) that creates 4-5 expression variations through chat-based interviews. The app has three generation modes:
1. **Normal Mode**: 4 expressions with green screen background for removal
2. **Emo Mode**: 4 expressions with black background (no removal needed)
3. **Fantasy Mode**: 4 expressions with black background for game assets

Workflow:
1. Chat-based interview to collect character details
2. Convert responses to JSON format
3. Send to Google Vertex AI Gemini 2.5 Flash Image Preview API
4. Apply background removal (normal mode only)
5. Return as ZIP download or base64 list

## Build & Run Commands
```bash
# Frontend development
cd frontend
npm install
npm run dev        # Dev server on localhost:5173
npm run build      # Production build
npm run lint       # Run ESLint

# Backend local testing
pip install -r requirements.txt
export NANOBANANA_API_KEY=your_key  # Legacy env var name still used
uvicorn server.main:app --reload --port 8080

# Docker local testing
docker build -t standing-set .
docker run -e NANOBANANA_API_KEY=xxxxx -p 8080:8080 standing-set

# Docker Compose (full stack)
docker-compose up --build

# Cloud Run deployment
gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/standing-set
gcloud run deploy standing-set \
  --image gcr.io/$(gcloud config get-value project)/standing-set \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

## Architecture & Code Structure

### Backend (`server/main.py`)
- **Framework**: FastAPI with Pydantic models
- **Image Generation**: Google Vertex AI Gemini 2.5 Flash Image Preview API
  - Credentials: Uses Google default credentials (ADC)
  - Project ID: Hardcoded as "812480532939"
  - Parallel generation with ThreadPoolExecutor for expressions 2-4
- **Background Removal**: rembg library with custom green artifact cleanup
- **Key Endpoints**:
  - `POST /api/generate` - Legacy endpoint for full character data
  - `POST /api/generate/simple` - Main endpoint supporting all three modes
  - `GET /api/health` - Health check with credential status

### Frontend (`frontend/src/`)
- **Framework**: React + Vite
- **Components**:
  - `App.jsx` - Main app with mode selection
  - `SimpleChatInterview.jsx` - Normal mode interview
  - `EmoMode.jsx` - Emo character creation
  - `FantasyMode.jsx` - Fantasy character creation
  - `GenerateButton.jsx` - Handles API calls and downloads
  - `JsonPreview.jsx` - Live JSON preview panel

### Character Data Models
- **SimpleCharacter**: age, body_type, eyes, hair, outfit, accessories
- **EmoCharacter**: height, hair, eyes, outfit (simplified)  
- **FantasyCharacter**: height, hair details, outfit, eye details, expression
- Legacy **Character** model with nested structure still supported

## Key Implementation Details

### Prompt Engineering
- **Normal Mode**: Green screen background (#00FF00), 4 expressions, high-key lighting
- **Emo Mode**: Black background, pastel palette, 1px thin lines, gradient-based shading
- **Fantasy Mode**: Black background, soft muted colors, game asset style

### Expression Generation Flow
1. First expression generated from text prompt
2. Use first image as base reference for remaining expressions
3. Parallel generation of expressions 2-4 using ThreadPoolExecutor
4. Fallback to fresh generation if edit mode fails

### Background Processing
- **Green Screen Removal** (normal mode only):
  - Initial removal with rembg
  - Custom post-processing to remove green artifacts
  - Edge detection and green suppression
- **Black backgrounds** (emo/fantasy): No processing needed

## Environment & Configuration
- Google Cloud credentials required (uses Application Default Credentials)
- Legacy `NANOBANANA_API_KEY` env var name kept for compatibility
- Docker images use Python 3.11-slim base
- Frontend uses Vite proxy for local API calls