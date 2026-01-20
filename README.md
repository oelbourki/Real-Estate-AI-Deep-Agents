# 🏠 Real Estate AI Deep Agents

<div align="center">

**An enterprise-level real estate AI solution powered by DeepAgents and LangGraph**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0-orange.svg)](https://github.com/langchain-ai/langgraph)
[![DeepAgents](https://img.shields.io/badge/DeepAgents-0.1-purple.svg)](https://github.com/deepagents/deepagents)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [API Reference](#-api-reference)

</div>

---

## 📖 Overview

The **Real Estate AI Deep Agents** is a sophisticated, production-ready AI system that helps users search, analyze, and evaluate real estate properties with comprehensive insights. Built on a multi-agent architecture using **DeepAgents** for orchestration and **LangGraph** for state management, it provides:

- 🔍 **Intelligent Property Search**: Search properties for sale or rent across the US
- 📊 **Financial Analysis**: ROI calculations, mortgage estimates, property tax analysis
- 📍 **Location Intelligence**: Neighborhood analysis, amenity discovery, route calculation
- 📈 **Market Research**: Trend analysis, price history, market comparisons
- 📄 **Report Generation**: Comprehensive property analysis reports in multiple formats
- 🤖 **Multi-Agent System**: 1 orchestrator + 6 specialized subagents for complex workflows

### Key Highlights

- ✅ **Production-Ready**: Monitoring, caching, rate limiting, error handling
- ✅ **Multi-LLM Support**: OpenRouter (default), Ollama, OpenAI, Groq, Anthropic, Google
- ✅ **Enterprise Features**: HITL workflows, persistent memory, retry logic
- ✅ **Modern Stack**: FastAPI, LangGraph, LangChain v1.0+, TypeScript frontend
- ✅ **Comprehensive Tools**: 15+ tools for property search, analysis, and research

---

## 🚀 Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Property Search** | Search properties for sale/rent using RealtyUS API with advanced filtering |
| **Financial Analysis** | Calculate ROI, mortgage payments, property tax, and compare properties |
| **Location Analysis** | Geocode addresses, find nearby amenities, calculate routes, analyze neighborhoods |
| **Market Research** | Research market trends, price history, and compare markets |
| **Data Extraction** | Scrape property pages from Zillow, Realtor.com, Redfin |
| **Report Generation** | Generate comprehensive property analysis reports (Markdown, JSON, HTML) |

### Architecture Features

- **Multi-Agent System**: Intelligent task delegation to specialized subagents
- **Persistent Memory**: Long-term memory for user preferences and property history
- **Hybrid Storage**: Filesystem backend with composite routing for reports and memories
- **Token Management**: Smart token counting and validation to prevent API rate limits
- **Caching**: Redis-based caching for API responses (1-hour TTL)
- **Monitoring**: LangSmith integration for tracing and debugging
- **Rate Limiting**: Per-IP rate limiting for API protection
- **Error Handling**: Graceful error handling with retry logic

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface                             │
│              (agent-chat-ui / Direct API)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Main Orchestrator Agent                          │
│         (DeepAgents + LangGraph StateGraph)                  │
│                                                               │
│  Direct Tools:                                               │
│  • realty_us_search_buy                                      │
│  • realty_us_search_rent                                    │
│                                                               │
│  Subagent Delegation:                                        │
│  • property-research  • location-analysis                   │
│  • financial-analysis • data-extraction                      │
│  • market-trends      • report-generator                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Subagents  │ │    Tools     │ │   Storage    │
│              │ │              │ │              │
│ • property   │ │ • RealtyUS   │ │ • Filesystem │
│ • location   │ │ • Location   │ │ • Composite  │
│ • financial  │ │ • Financial  │ │ • Memory     │
│ • extraction │ │ • Market     │ │              │
│ • trends     │ │ • Scraping   │ │              │
│ • reports    │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Technology Stack

- **Backend Framework**: FastAPI (Python 3.11+)
- **Agent Framework**: DeepAgents (orchestration) + LangGraph (state management)
- **LLM Integration**: LangChain v1.0+ with multi-provider support
- **Storage**: Filesystem backend + Composite routing
- **Caching**: Redis (optional)
- **Frontend**: agent-chat-ui (Next.js, TypeScript)
- **API Gateway**: LangGraph Platform API (via `langgraph dev`)

For detailed architecture documentation, see [BACKEND_AND_AGENTS_REPORT.md](./BACKEND_AND_AGENTS_REPORT.md).

---

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.11 or 3.12 (Python 3.13 has SQLite compatibility issues)
- **Node.js**: 18+ (for agent-chat-ui frontend)
- **Redis**: Optional, for caching (recommended for production)
- **Ollama**: Optional, for local LLM (no API key needed)

### Installation

1. **Clone the repository**:

```bash
git clone --recurse-submodules https://github.com/your-username/real-estate-ai-agent.git
cd real-estate-ai-agent
```

2. **Set up backend**:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -U "langgraph-cli[inmem]"
```

3. **Configure environment variables**:

```bash
cp .env.example .env
# Edit .env with your API keys (see Configuration section)
```

4. **Initialize memory files**:

```bash
python -c "from backends.memory import initialize_memory_files; initialize_memory_files()"
```

5. **Set up frontend** (if using agent-chat-ui):

```bash
cd ../agent-chat-ui
pnpm install
```

### Running the Application

#### Option 1: LangGraph Dev Server (Recommended)

```bash
# From project root
langgraph dev
```

Server starts on `http://localhost:2024` with LangGraph Platform API endpoints.

#### Option 2: FastAPI Backend

```bash
cd backend
python run.py
```

Server starts on `http://localhost:8000` with FastAPI endpoints.

#### Option 3: Frontend (agent-chat-ui)

```bash
cd agent-chat-ui
pnpm dev
```

Frontend starts on `http://localhost:3000`.

---

## ⚙️ Configuration

### Required Environment Variables

Create `backend/.env` from `backend/.env.example`:

#### 1. LLM Provider (choose at least one)

**OpenRouter (Recommended - Default)**:
```bash
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Get your API key from [OpenRouter](https://openrouter.ai/keys).

**Ollama (Local, No API Key)**:
```bash
# Install: curl -fsSL https://ollama.com/install.sh | sh
# Pull model: ollama pull llama3.2
# Start: ollama serve
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

**Other Providers**:
```bash
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

#### 2. Real Estate API

```bash
RAPIDAPI_KEY=your_rapidapi_key_here
```

Get your RapidAPI key from [RapidAPI Hub](https://rapidapi.com/hub) and subscribe to the **Realty-US API**.

### Optional Configuration

- **Redis**: `REDIS_URL=redis://localhost:6379/0` (for caching)
- **LangSmith**: For monitoring and debugging
- **Token Limits**: `ENABLE_TOKEN_LIMITS=true`, `MAX_TOKENS_PER_REQUEST=100000`

See `backend/.env.example` for all available options.

---

## 💡 Usage Examples

### Example 1: Simple Property Search

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find houses in San Francisco, CA under $2M",
    "user_name": "John"
  }'
```

**Response**: List of properties with addresses, prices, beds, baths, photos, and listing URLs.

### Example 2: Complex Analysis

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find 3 bedroom houses in Austin, TX, analyze their locations, and calculate ROI assuming $3000/month rent",
    "user_name": "Jane"
  }'
```

**Response**: Properties found → Location analysis → ROI calculations → Comprehensive report.

### Example 3: Financial Analysis

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Calculate ROI for a $500k property with $3000/month rent, 20% down, 6.5% interest",
    "user_name": "Bob"
  }'
```

**Response**: Detailed ROI breakdown with cash flow, cap rate, and expense breakdown.

### Example 4: Location Analysis

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What amenities are near 123 Main St, San Francisco, CA?",
    "user_name": "Alice"
  }'
```

**Response**: Nearby schools, restaurants, parks, hospitals, shopping centers, etc.

### Using the Frontend (agent-chat-ui)

1. Open `http://localhost:3000`
2. Enter:
   - **Deployment URL**: `http://localhost:2024`
   - **Assistant ID**: `real-estate-agent`
3. Start chatting with the AI agent!

---

## 📚 API Reference

### Main Endpoints

#### Chat Endpoint

```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "Find houses in San Francisco",
  "user_name": "John",
  "conversation_id": "thread_123"  // Optional
}
```

**Response** (LangGraph format):
```json
{
  "messages": [
    {
      "type": "human",
      "content": "Find houses in San Francisco"
    },
    {
      "type": "ai",
      "content": "I found 8 properties..."
    }
  ],
  "thread_id": "thread_123"
}
```

#### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "redis": "connected",
  "timestamp": 1234567890
}
```

#### Metrics

```http
GET /metrics
```

**Response**: Request counts, error rates, response times, cache performance.

### LangGraph Platform API

When using `langgraph dev`, these endpoints are automatically available:

- `GET /info` - Server information
- `GET /threads/search` - Search threads
- `POST /threads` - Create thread
- `GET /assistants/{assistant_id}/threads/{thread_id}/runs` - Get run history
- `POST /assistants/{assistant_id}/threads/{thread_id}/runs` - Create run
- `POST /assistants/{assistant_id}/threads/{thread_id}/runs/stream` - Stream run

See [docs/](./docs/) for detailed API documentation.

---

## 🛠️ Development

### Project Structure

```
real-estate-ai-agent/
├── backend/                  # Backend Python code
│   ├── agents/              # Agent implementations
│   │   ├── main_agent.py    # Main orchestrator
│   │   └── subagents.py     # Subagent definitions
│   ├── api/                 # FastAPI endpoints
│   │   ├── main.py          # FastAPI app
│   │   └── schemas.py       # Request/response models
│   ├── tools/               # Tool implementations
│   │   ├── realty_us.py     # Property search
│   │   ├── location.py      # Location analysis
│   │   ├── financial.py     # Financial calculations
│   │   ├── market_research.py
│   │   └── web_scraping.py
│   ├── backends/            # Storage backends
│   ├── config/              # Configuration
│   ├── utils/               # Utilities
│   └── tests/               # Test suite
├── agent-chat-ui/           # Frontend (Git submodule)
├── docs/                     # Documentation
├── langgraph.json           # LangGraph configuration
└── README.md                # This file
```

### Running Tests

```bash
cd backend
pytest
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy .
```

### Adding New Tools

1. Create tool in `backend/tools/`
2. Add to appropriate subagent in `backend/agents/subagents.py`
3. Update documentation

### Adding New Subagents

1. Define subagent in `backend/agents/subagents.py`
2. Create system prompt in `backend/config/subagent_prompts.py`
3. Add tools to subagent definition

---

## 📖 Documentation

### Comprehensive Guides

- **[Backend and Agents Report](./BACKEND_AND_AGENTS_REPORT.md)** - Complete architecture documentation
- **[GitHub Push Analysis](./GITHUB_PUSH_ANALYSIS.md)** - What to push to GitHub
- **[Deployment Guide](./docs/DEPLOYMENT.md)** - Production deployment instructions
- **[Monitoring Guide](./docs/MONITORING.md)** - Monitoring and observability
- **[Production Checklist](./docs/PRODUCTION_CHECKLIST.md)** - Pre-deployment checklist
- **[Runbook](./docs/RUNBOOK.md)** - Operations runbook

### API Documentation

- FastAPI docs: `http://localhost:8000/docs` (when running FastAPI backend)
- LangGraph Platform API: See [LangGraph documentation](https://langchain-ai.github.io/langgraph/)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**:
   - Follow PEP 8 style guide
   - Write tests for new features
   - Update documentation
   - Use type hints
4. **Commit your changes**:
   ```bash
   git commit -m 'Add amazing feature'
   ```
5. **Push to the branch**:
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Development Guidelines

- **Code Style**: Follow PEP 8, use `black` for formatting
- **Testing**: Write unit tests for new features, aim for >80% coverage
- **Documentation**: Update README and docstrings as needed
- **Type Hints**: Use type hints for all function signatures
- **Commit Messages**: Write clear, descriptive commit messages

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "No LLM provider available"

**Solution**: Configure at least one LLM provider in `backend/.env`:
- Set `OPENROUTER_API_KEY` (recommended)
- Or install and run Ollama locally
- Or set another provider's API key

#### 2. "ModuleNotFoundError: No module named 'config'"

**Solution**: Make sure you're running from the project root or have the backend directory in your Python path. The code uses absolute imports (`from backend.config.settings`).

#### 3. "BlockingError: Blocking call to os.getcwd"

**Solution**: This occurs when using `langgraph dev`. Options:
- Use `langgraph dev --allow-blocking` for development
- Or fix the blocking call in `backend/backends/storage.py` (see [BACKEND_AND_AGENTS_REPORT.md](./BACKEND_AND_AGENTS_REPORT.md))

#### 4. "Request too large" error (Groq)

**Solution**: 
- Use OpenRouter instead (higher limits)
- Or upgrade Groq tier
- Or set `MAX_TOKENS_PER_REQUEST=5500` for Groq free tier

#### 5. Frontend can't connect to backend

**Solution**: 
- Make sure `langgraph dev` is running on `http://localhost:2024`
- Check `agent-chat-ui/.env.local` has correct `NEXT_PUBLIC_API_URL`
- Verify CORS settings in `backend/config/settings.py`

For more troubleshooting, see [docs/](./docs/).

---

## 📊 Project Status

- ✅ **Phase 1**: Foundation - Complete
- ✅ **Phase 2**: Subagent Development - Complete
- ✅ **Phase 3**: Advanced Features - Complete
- ✅ **Phase 4**: Enterprise Features - Complete
- ✅ **Phase 5**: Production Readiness - Complete

**Current Version**: 1.0.0  
**Status**: Production Ready

---

## 📝 License

[Add your license here - MIT, Apache 2.0, etc.]

---

## 🙏 Acknowledgments

- **[DeepAgents](https://github.com/deepagents/deepagents)** - Agent orchestration framework
- **[LangGraph](https://github.com/langchain-ai/langgraph)** - State management and agent graphs
- **[LangChain](https://github.com/langchain-ai/langchain)** - LLM integration
- **[agent-chat-ui](https://github.com/langchain-ai/agent-chat-ui)** - Frontend chat interface
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern web framework
- **[Realty-US API](https://rapidapi.com/)** - Property search data

---

## 📧 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/your-username/real-estate-ai-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/real-estate-ai-agent/discussions)
- **Email**: [Your email]

---

<div align="center">

**Built with ❤️ using DeepAgents, LangGraph, and FastAPI**

[⭐ Star this repo](https://github.com/your-username/real-estate-ai-agent) • [🐛 Report Bug](https://github.com/your-username/real-estate-ai-agent/issues) • [💡 Request Feature](https://github.com/your-username/real-estate-ai-agent/issues)

</div>
