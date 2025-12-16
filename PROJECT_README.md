# AI Personal Tutor

> A podcast-style learning platform powered by AWS AI services

## Overview

AI Personal Tutor transforms any web content into engaging, conversational podcast lessons. Using Amazon Lex for natural conversation, Ollama for content understanding, and Amazon Polly for realistic speech synthesis, the platform creates a unique learning experience featuring two AI hosts:

- **Alex** (Matthew voice) - A senior engineer who explains complex topics clearly
- **Sam** (Joanna voice) - A curious learner who asks the questions students are thinking

![Architecture Diagram](docs/architecture-diagram.png)

## Features

- 🎙️ **Podcast-Style Lessons** - Two-host conversational format for engaging learning
- 💬 **Conversational UI** - Amazon Lex-powered chat for natural interaction
- 🔗 **URL Ingestion** - Learn from any web content
- 🎧 **Neural Voices** - Amazon Polly's most realistic speech synthesis
- 📝 **Transcript Support** - Follow along with synchronized text
- ☁️ **Infrastructure as Code** - Full Terraform deployment

## Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Terraform >= 1.5.0
- Node.js >= 18
- Python >= 3.11

### 1. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform apply
```

### 2. Start Backend (Local Dev)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables from Terraform outputs
export AWS_REGION=us-east-1
export S3_BUCKET=$(terraform -chdir=../terraform output -raw s3_bucket_name)
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=llama3.2

python src/app.py
```

### 3. Start Frontend (Local Dev)

```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  React Frontend │────▶│  Amazon Lex V2  │────▶│  Lambda Handler │
│  (Vite + AWS)   │     │  (Conversational│     │  (Fulfillment)  │
│                 │     │   Interface)    │     │                 │
└────────┬────────┘     └─────────────────┘     └────────┬────────┘
         │                                               │
         │                                               │
         ▼                                               ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Flask API     │◀────│     Ollama      │◀────│  Content URLs   │
│   (Backend)     │     │   (llama3.2)    │     │                 │
│                 │     │                 │     │                 │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │
│  Amazon Polly   │────▶│   S3 Bucket     │
│  (Neural TTS)   │     │  (Audio Files)  │
│                 │     │                 │
└─────────────────┘     └─────────────────┘
```

## Project Structure

```
aico-delta-assessment-ii/
├── backend/
│   ├── cli/
│   │   ├── __init__.py
│   │   └── demo.py                # CLI demo tool
│   ├── src/
│   │   ├── app.py                 # Flask API
│   │   ├── config.py              # Configuration
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── api_v2.py          # API v2 routes
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── tutor_session.py       # Session orchestration
│   │   │   ├── content_extractor.py   # URL extraction
│   │   │   ├── content_processor.py   # Content processing
│   │   │   ├── podcast_generator.py   # Script generation
│   │   │   ├── audio_synthesizer.py   # Basic Polly synthesis
│   │   │   ├── enhanced_audio_synthesizer.py  # Advanced synthesis
│   │   │   ├── audio_stitcher.py      # Audio concatenation
│   │   │   ├── audio_coordinator.py   # Audio orchestration
│   │   │   ├── dialogue_models.py     # Script data models
│   │   │   ├── prompt_templates.py    # LLM prompts
│   │   │   └── script_formatter.py    # Script formatting
│   │   └── utils/
│   │       ├── url_validator.py
│   │       └── cache.py
│   ├── tests/
│   │   ├── test_content_extraction.py
│   │   ├── test_podcast_generation.py
│   │   ├── test_audio_synthesis.py
│   │   └── test_integration.py    # End-to-end tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   ├── LexChat.jsx
│   │   │   ├── PodcastPlayer.jsx
│   │   │   └── LessonList.jsx
│   │   └── pages/
│   │       ├── Home.jsx
│   │       └── Tutor.jsx
│   ├── package.json
│   └── vite.config.js
├── terraform/
│   ├── main.tf
│   ├── vpc.tf
│   ├── lex.tf
│   ├── lambda.tf
│   ├── cognito.tf
│   └── ...
├── lambda/
│   └── lex_fulfillment/
│       └── handler.py
└── docs/
    ├── ARCHITECTURE.md
    ├── DEPLOYMENT.md
    └── API.md
```

## AWS Services Used

| Service            | Purpose                                  |
| ------------------ | ---------------------------------------- |
| **Amazon Lex V2**  | Conversational interface for onboarding  |
| **Amazon Polly**   | Neural text-to-speech (Matthew & Joanna) |
| **Amazon S3**      | Audio file storage                       |
| **Amazon Cognito** | Identity pool for browser Lex access     |
| **AWS Lambda**     | Lex fulfillment handler                  |
| **EC2 + ASG**      | Backend and frontend hosting             |
| **ALB**            | Load balancing and routing               |

## API Endpoints

### API v1 (Legacy)

| Method   | Endpoint                  | Description              |
| -------- | ------------------------- | ------------------------ |
| `POST`   | `/api/ingest`             | Extract content from URL |
| `GET`    | `/api/session`            | Get session information  |
| `DELETE` | `/api/session`            | Clear session            |
| `GET`    | `/api/lesson/{num}/audio` | Get lesson audio URL     |

### API v2 (Recommended)

The v2 API provides improved session management and lesson generation capabilities.

#### Session Endpoints

| Method   | Endpoint                | Description                 |
| -------- | ----------------------- | --------------------------- |
| `POST`   | `/api/v2/sessions`      | Create new session from URL |
| `GET`    | `/api/v2/sessions`      | List all sessions           |
| `GET`    | `/api/v2/sessions/{id}` | Get session details         |
| `DELETE` | `/api/v2/sessions/{id}` | Delete session              |

#### Lesson Endpoints

| Method | Endpoint                                         | Description                    |
| ------ | ------------------------------------------------ | ------------------------------ |
| `GET`  | `/api/v2/sessions/{id}/lessons`                  | List all lessons               |
| `GET`  | `/api/v2/sessions/{id}/lessons/{num}`            | Get lesson details             |
| `POST` | `/api/v2/sessions/{id}/lessons/{num}/generate`   | Generate lesson script + audio |
| `GET`  | `/api/v2/sessions/{id}/lessons/{num}/transcript` | Get lesson transcript          |
| `GET`  | `/api/v2/sessions/{id}/lessons/{num}/audio`      | Get audio URL                  |

#### Batch Operations

| Method | Endpoint                             | Description          |
| ------ | ------------------------------------ | -------------------- |
| `POST` | `/api/v2/sessions/{id}/generate-all` | Generate all lessons |

#### Admin Endpoints

| Method | Endpoint                | Description           |
| ------ | ----------------------- | --------------------- |
| `POST` | `/api/v2/admin/cleanup` | Clean up old sessions |

See [API Documentation](docs/API.md) for full details.

## Configuration

### Environment Variables

**Backend:**

```bash
AWS_REGION=us-east-1
S3_BUCKET=ai-tutor-audio-xxxxx
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
PORT=8000
```

**Frontend:**

```bash
VITE_AWS_REGION=us-east-1
VITE_COGNITO_IDENTITY_POOL_ID=us-east-1:xxxxx
VITE_LEX_BOT_ID=XXXXXXXXXX
VITE_LEX_BOT_ALIAS_ID=XXXXXXXXXX
VITE_API_URL=http://localhost:8000
```

## Development

### Running Ollama Locally

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3.2

# Start server
ollama serve
```

### Testing the Backend

```bash
# Run all tests
cd backend
pytest tests/ -v

# Run specific test modules
pytest tests/test_integration.py -v
pytest tests/test_audio_synthesis.py -v

# Health check
curl http://localhost:8000/health

# Create session (v2 API)
curl -X POST http://localhost:8000/api/v2/sessions \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# Generate lesson
curl -X POST http://localhost:8000/api/v2/sessions/{session_id}/lessons/1/generate

# Get transcript
curl http://localhost:8000/api/v2/sessions/{session_id}/lessons/1/transcript
```

### CLI Demo

```bash
cd backend

# Run demo with URL
python -m cli.demo https://docs.python.org/3/tutorial/introduction.html

# Generate specific number of lessons
python -m cli.demo https://example.com/article --lessons 2

# Save outputs to directory
python -m cli.demo https://example.com/doc --output ./my-lessons

# Interactive mode
python -m cli.demo --interactive
```

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [API Reference](docs/API.md)

## License

Educational use only - Code Platoon AI Cohort

---

_Built with ❤️ for the AICO Delta cohort_
