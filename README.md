# 🎬 Dottie AI Creative Studio

An intelligent multi-agent system for automated AI-powered content generation. Dottie orchestrates specialized agents to create synchronized music, images, videos, voice-overs, subtitles, and sound effects from simple text prompts.

## 🎯 Project Overview

Dottie AI Creative Studio is a full-stack application that leverages LangGraph and specialized AI models to generate complete multimedia content. The system uses a supervisor agent that coordinates multiple specialized agents to work together seamlessly.

### Key Features

- **🎵 Music Generation**: AI-powered music composition and generation
- **🖼️ Image Creation**: Intelligent image generation from text descriptions
- **🎥 Video Production**: Automatic video synthesis and editing
- **🎙️ Voice-Over Generation**: Natural voice synthesis for narration
- **📝 Subtitle Generation**: Automatic subtitle creation and synchronization
- **🔊 Sound Effects**: Context-aware SFX generation
- **🧠 Smart Planning**: Multi-step content planning with safety checks

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────┐
│     Frontend (React/HTML)               │
│  Dottie AI Creative Studio UI           │
└────────────────┬────────────────────────┘
                 │ HTTP/REST API
┌────────────────▼────────────────────────┐
│     FastAPI Backend (main.py)           │
│  - CORS enabled for frontend            │
│  - Static file serving                  │
│  - Media cleanup janitor                │
└────────────────┬────────────────────────┘
                 │ Orchestration
┌────────────────▼────────────────────────┐
│   Supervisor Agent (LangGraph)          │
│  - Routes requests to agents            │
│  - Coordinates agent workflows          │
└─────┬──────┬──────┬──────┬──────┬───────┘
      │      │      │      │      │
  ┌───▼─┐ ┌──▼──┐ ┌─▼──┐ ┌─▼──┐ ┌─▼──┐
 │Plan │ │Music│ │Image│ │Video│ │Voice│
 └──────┘ └─────┘ └─────┘ └──────┘ └─────┘
      │      │      │      │      │
 ┌────▼──────▼──────▼──────▼──────▼────┐
 │    Specialized Models & APIs         │
 │ - HuggingFace Transformers           │
 │ - Groq LLM API                       │
 │ - Pexels Image API                   │
 │ - Pollinations API                   │
 │ - Google API                         │
 └──────────────────────────────────────┘
```

### Backend Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration and API keys
├── Agents/                # Specialized AI agents
│   ├── supervisor_agent.py      # Orchestrates all agents
│   ├── planner_agent.py         # Content planning
│   ├── music_agent.py           # Music generation
│   ├── image_agent.py           # Image creation
│   ├── video_agent.py           # Video synthesis
│   ├── voice_over_agent.py      # Voice synthesis
│   ├── subtitle_agent.py        # Subtitle generation
│   └── sfx_agent.py             # Sound effects
├── models/                # AI models and LLM interfaces
│   ├── llm.py            # LLM model wrapper
│   ├── image_gen.py      # Image generation models
│   └── music.py          # Music generation models
├── prompts/              # System prompts for agents
│   ├── planner/
│   ├── music/
│   ├── image/
│   ├── video/
│   ├── voice_over/
│   ├── sfx/
│   └── supervisor/
├── utils/               # Utility functions
│   └── subtitle_utils.py
├── generated_media/     # Output directory for generated content
├── requirements.txt     # Python dependencies
└── README.md           # Backend documentation
```

### Frontend Structure

```
frontend/
├── index.html           # Main UI application
├── requirements.txt     # Frontend dependencies (if any)
└── [static assets]      # CSS, JavaScript, etc.
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip or conda
- API Keys for:
  - Groq API (for LLM)
  - HuggingFace Token (for transformers)
  - Pexels API (for image search)
  - Pollinations API (for image generation)
  - Google API (for various services)

### Installation

1. **Clone or setup the project**
   ```bash
   cd d:\Projects\content_agent
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   # or
   source .venv/bin/activate  # On macOS/Linux
   ```

3. **Install backend dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Configure API keys**
   Create a `.env` file in the `backend/` directory:
   ```env
   GROQ_API_KEY=your_groq_key
   HF_TOKEN=your_huggingface_token
   PEXELS_API_KEY=your_pexels_key
   POLLINATIONS_API_KEY=your_pollinations_key
   GOOGLE_API_KEY=your_google_key
   ```

### Running the Application

1. **Start the backend server**
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   The API will be available at `http://localhost:8000`

2. **Access the frontend**
   Open your browser and navigate to the frontend URL (typically served by the FastAPI app)

3. **Generate content**
   Submit a prompt through the UI, and Dottie will orchestrate the agents to create your multimedia content.

## 📋 API Endpoints

The backend provides REST API endpoints for content generation. Check the FastAPI documentation at `/docs` (Swagger UI) or `/redoc` (ReDoc) when the server is running.

### Main Workflow

1. **User submits prompt** → Frontend sends to backend
2. **Backend receives request** → FastAPI processes it
3. **Supervisor Agent** analyzes request and creates a workflow plan
4. **Planner Agent** breaks down the task with safety checks
5. **Specialized Agents execute**:
   - Music Agent generates soundtrack
   - Image Agent creates visuals
   - Video Agent synthesizes video
   - Voice Agent generates narration
   - Subtitle Agent creates captions
   - SFX Agent adds sound effects
6. **Generated media** is stored in `generated_media/`
7. **Response** is sent back to frontend with media URLs

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq LLM API key | `gsk_...` |
| `HF_TOKEN` | HuggingFace API token | `hf_...` |
| `PEXELS_API_KEY` | Pexels image API key | `...` |
| `POLLINATIONS_API_KEY` | Pollinations image generation key | `...` |
| `GOOGLE_API_KEY` | Google API key | `...` |

### Backend Settings

Located in `backend/config.py`:
- `MAX_FILE_AGE_SECONDS`: Auto-cleanup timeout for generated media (default: 100s)
- `MEDIA_DIR`: Output directory for generated content (default: `generated_media/`)

## 📦 Dependencies

### Backend
- **FastAPI**: Web framework for APIs
- **Uvicorn**: ASGI server
- **LangChain**: LLM and chain orchestration
- **LangGraph**: Agent graph orchestration
- **Transformers**: Hugging Face models
- **Torch**: Deep learning framework
- **SciPy**: Scientific computing

See `backend/requirements.txt` for the complete list.

## 🎨 Agent Details

### Planner Agent
- Analyzes incoming prompts
- Creates multi-step execution plans
- Performs safety violation checks
- Generates context for other agents

### Music Agent
- Generates music tracks based on mood/style
- Uses advanced AI models for composition
- Refines prompts for optimal output

### Image Agent
- Creates images from text descriptions
- Uses multiple image generation APIs
- Refines prompts iteratively

### Video Agent
- Synthesizes videos from images and audio
- Handles video composition and effects
- Uses Pixel Video technology

### Voice Agent
- Generates natural voice-overs
- Supports multiple languages and voices
- Parses and formats voice requirements

### Subtitle Agent
- Generates accurate subtitles
- Synchronizes with video timeline
- Supports multiple languages

### SFX Agent
- Generates contextual sound effects
- Parses SFX requirements
- Integrates with audio pipeline

## 🧹 Media Cleanup

The backend includes an automatic janitor service that:
- Runs every 2 minutes
- Removes generated media files older than 100 seconds
- Prevents disk space overflow
- Runs asynchronously in the background

## 🔐 Security Considerations

- API keys should never be committed to version control
- Use environment variables for sensitive data
- CORS is configured for secure cross-origin requests
- Input validation is performed by Pydantic models

## 🐛 Troubleshooting

### Port Already in Use
```bash
# On Windows, find process using port 8000
netstat -ano | findstr :8000
# Kill the process
taskkill /PID <PID> /F
```

### API Key Issues
- Verify all required API keys are set in `.env`
- Check API key validity and permissions
- Ensure keys have appropriate quotas

### Module Import Errors
```bash
# Reinstall dependencies
pip install --upgrade -r backend/requirements.txt
```

### Generated Media Not Showing
- Check `generated_media/` directory exists
- Verify write permissions for the directory
- Check backend logs for cleanup errors

## 📖 Documentation

- **Backend**: See `backend/README.md`
- **API Docs**: Available at `http://localhost:8000/docs` (Swagger UI)
- **Agent Prompts**: System prompts in `backend/prompts/`

## 🤝 Contributing

When contributing to this project:
1. Follow the existing code structure
2. Add new agents under `backend/Agents/`
3. Add system prompts under `backend/prompts/`
4. Update requirements.txt if adding dependencies
5. Test with the FastAPI development server

## 📄 License

Specify your project license here.

## 🎯 Future Enhancements

- [ ] Real-time media streaming
- [ ] Batch processing support
- [ ] Advanced caching for repeated requests
- [ ] Multi-language support expansion
- [ ] Custom agent creation interface
- [ ] Performance analytics dashboard
- [ ] Advanced error recovery mechanisms

## 📧 Support

For issues, questions, or feature requests, please create an issue in the project repository.

---

**Dottie AI Creative Studio** - Empowering creators with AI 🚀
