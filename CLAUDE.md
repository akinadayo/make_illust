# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a character standing image generation application (Standing-Set-5) that creates 5 expression variations of a single character through a chat-based interview system. The workflow is:
1. Chat-based interview (6 questions + 2 confirmations) to collect character appearance details
2. Convert responses to JSON
3. Send to NanoBanana API for 5-image batch generation (full-body, white background)
4. Apply background removal with rembg
5. Return as ZIP download

## Key Technical Components

### Backend
- **Framework**: FastAPI (Python)
- **Main endpoints**:
  - `POST /api/generate` - Receives character JSON, generates images via NanoBanana, applies background removal, returns ZIP
  - `GET /api/health` - Health check
- **Dependencies**: fastapi, uvicorn, pydantic, requests, rembg, pillow, python-multipart
- **Environment variable**: `NANOBANANA_API_KEY` (required for API access)

### Frontend Requirements
- React + Vite or Next.js
- Left panel: Chat-style interview (6 questions + 2 confirmations)
- Right panel: JSON preview of responses
- Generate button → Progress display → ZIP download

### Docker/Cloud Run Deployment
- Containerized with Python 3.11-slim base image
- Configured for Cloud Run deployment on port 8080
- Deploy command: `gcloud run deploy standing-set`

## Character Data Schema
The core JSON structure includes:
- `character_id`: Unique identifier
- `seed`: Fixed seed for consistent generation
- `basic`: Age appearance, height, build
- `hair`: Color, length, bangs, style, accessories
- `face`: Eye color/shape, features
- `outfit`: Style, top, bottom, accessories, shoes
- `persona`: Keywords and role
- `framing`: Shot type (full-body), camera angle (front-facing)
- `constraints`: Background (white), forbidden elements

## NanoBanana Prompt Requirements
- Generate 5 images in single request with n=5, same seed, size 1024×1536 (portrait)
- Color palette: Pale/light grayish/soft pastel tones with gray outlines
- Expressions vary per image: neutral, smile, surprise, troubled, pouting
- Keep character, pose, framing identical across all 5 images

## Development Commands
```bash
# Local Docker testing
docker build -t standing-set .
docker run -e NANOBANANA_API_KEY=xxxxx -p 8080:8080 standing-set

# Test API
curl http://localhost:8080/api/health

# Cloud Run deployment
gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/standing-set
gcloud run deploy standing-set --image gcr.io/$(gcloud config get-value project)/standing-set --platform managed --region asia-northeast1 --allow-unauthenticated --set-env-vars NANOBANANA_API_KEY=YOUR_KEY
```

## Testing Focus Areas
- Ensure full body is captured without cropping (head to toes)
- Verify consistency across 5 images (same outline, hair, outfit, build, framing)
- Confirm only facial expressions change between images
- Check background removal quality, especially around hair edges
- Handle API failures gracefully (4xx/5xx responses, timeouts)