# Enterprise Real Estate AI Agent

Enterprise-level real estate AI solution powered by **DeepAgents** and **LangGraph**, featuring advanced property search, location analysis, financial calculations, and comprehensive reporting capabilities.

## 🚀 Features

- **Property Search**: Search for properties to buy or rent using RealtyUS API
- **Location Analysis**: Analyze neighborhoods, find amenities, calculate routes
- **Financial Analysis**: ROI calculations, mortgage estimates, property tax analysis
- **Market Research**: Market trends, price history, market comparisons
- **Data Extraction**: Web scraping for property data from Zillow, Realtor.com, Redfin
- **Report Generation**: Comprehensive property analysis reports
- **Multi-LLM Support**: OpenRouter (default), Ollama, OpenAI, Groq, Anthropic, Google
- **LangGraph API Compatibility**: Full integration with agent-chat-ui

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+ (for agent-chat-ui)
- API Keys:
  - **OpenRouter** (recommended, default) - [Get here](https://openrouter.ai/keys)
  - **RapidAPI** (for RealtyUS) - [Get here](https://rapidapi.com/ntd119/api/realty-us)
  - Optional: OpenAI, Groq, Anthropic, Google API keys

## 🛠️ Installation

### 1. Clone This Repository

```bash
# Clone with submodules (recommended)
git clone --recurse-submodules https://github.com/yourusername/enterprise-real-estate-ai-agent.git
cd enterprise-real-estate-ai-agent

# OR if you already cloned without submodules:
git submodule update --init --recursive
```

### 2. Set Up Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

Create `.env` file in `backend/`:

```env
# OpenRouter (default, recommended)
OPENROUTER_API_KEY=sk-or-your-key-here
OPENROUTER_MODEL=openai/gpt-4o-mini

# Real Estate API
RAPIDAPI_KEY=your_rapidapi_key_here

# Optional: Other LLM providers
# OPENAI_API_KEY=your_key
# GROQ_API_KEY=your_key
# ANTHROPIC_API_KEY=your_key
# GOOGLE_API_KEY=your_key

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 4. Set Up Frontend (agent-chat-ui)

This project uses **Git Submodules** to include `agent-chat-ui`. After cloning, initialize submodules:

```bash
# If you cloned without --recurse-submodules
git submodule update --init --recursive

# Navigate to agent-chat-ui
cd agent-chat-ui
pnpm install
```

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ASSISTANT_ID=real-estate-agent
```

## 🚀 Running

### Start Backend

```bash
cd backend
python run.py
```

Backend will be available at: http://localhost:8000

### Start Frontend (agent-chat-ui)

```bash
cd agent-chat-ui
pnpm dev
```

Frontend will be available at: http://localhost:3000

## 📖 Usage

### API Endpoints

- **Health Check**: `GET /health`
- **Chat**: `POST /api/v1/chat`
- **Property Search**: `POST /api/v1/properties/search`
- **LangGraph API**: `/assistants/{assistant_id}/threads/*`

### Example API Call

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find 3 bedroom houses in San Francisco under $2M",
    "user_name": "John"
  }'
```

### Using agent-chat-ui

1. Open http://localhost:3000
2. Enter:
   - **Deployment URL**: `http://localhost:8000`
   - **Assistant ID**: `real-estate-agent`
3. Start chatting!

## 🏗️ Architecture

- **Backend**: FastAPI + DeepAgents + LangGraph
- **Frontend**: agent-chat-ui (Next.js + React)
- **LLM**: OpenRouter (default), supports multiple providers
- **Storage**: Filesystem backend for reports, MemorySaver for conversations
- **Caching**: Redis (optional)

## 📁 Project Structure

```
enterprise-real-estate-ai-agent/
├── backend/              # FastAPI backend
│   ├── agents/          # AI agents (main + subagents)
│   ├── tools/           # Tool implementations
│   ├── api/             # API endpoints
│   ├── config/          # Configuration
│   └── utils/           # Utilities
├── agent-chat-ui/       # Frontend (clone separately)
├── docs/                # Documentation
└── tests/               # Tests
```

## 🔧 Configuration

See `backend/config/settings.py` for all configuration options.

### LLM Providers

Priority order:
1. OpenRouter (default)
2. Ollama (local)
3. OpenAI
4. Groq
5. Anthropic
6. Google

### Token Limits

Token limits are automatically disabled for:
- Ollama (local, no limits)
- OpenRouter (high limits)

For other providers, configure in `.env`:
```env
ENABLE_TOKEN_LIMITS=true
MAX_TOKENS_PER_REQUEST=100000
```

## 📚 Documentation

- [Setup Guide](SETUP.md)
- [Quick Start](QUICK_START.md)
- [LangGraph API Endpoints](LANGGRAPH_API_ENDPOINTS.md)
- [GitHub Setup](GITHUB_SETUP.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

[Add your license here]

## 🙏 Acknowledgments

- [DeepAgents](https://github.com/langchain-ai/langchain/tree/main/libs/deepagents)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [agent-chat-ui](https://github.com/langchain-ai/agent-chat-ui)
- [RealtyUS API](https://rapidapi.com/ntd119/api/realty-us)

## 📧 Support

For issues and questions, please open an issue on GitHub.
