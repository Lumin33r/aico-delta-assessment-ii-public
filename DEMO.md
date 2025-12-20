# AI Personal Tutor - Assessment Demo Guide

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [AWS Services Deep Dive](#aws-services-deep-dive)
4. [Code Walkthrough](#code-walkthrough-during-resource-spin-up)
5. [Deployment Steps](#deployment-steps)
6. [Live Demo Flow](#live-demo-flow)
7. [Concrete Request Flow Example](#concrete-request-flow-example)
8. [Key Technical Highlights](#key-technical-highlights)
9. [Backend Tests](#backend-tests)
10. [Troubleshooting History](#troubleshooting-history)

---

## Project Overview

The **AI Personal Tutor** transforms any web content into engaging podcast-style lessons using two AI hosts:

| Host     | Voice            | Role                                       |
| -------- | ---------------- | ------------------------------------------ |
| **Alex** | Matthew (Neural) | Senior engineer, explains concepts clearly |
| **Sam**  | Joanna (Neural)  | Curious learner, asks clarifying questions |

### User Flow

```
User → Provides URL → Content Extracted → LLM Generates Lesson Plan →
Podcast Script Created → AWS Polly Synthesizes Audio → User Listens
```

---

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         AWS CLOUD                                                  │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                   │
│  ┌─────────────────────────────────────── VPC (10.0.0.0/16) ──────────────────────────────────┐  │
│  │                                                                                             │  │
│  │   ┌─────────────────────────────────┐    ┌─────────────────────────────────┐               │  │
│  │   │      Public Subnets (x2)        │    │      Private Subnets (x2)       │               │  │
│  │   │     10.0.1.0/24, 10.0.2.0/24    │    │    10.0.101.0/24, 10.0.102.0/24 │               │  │
│  │   │                                 │    │                                 │               │  │
│  │   │  ┌───────────────────────────┐  │    │  ┌───────────────────────────┐  │               │  │
│  │   │  │   Application Load        │  │    │  │    VPC Endpoints          │  │               │  │
│  │   │  │      Balancer (ALB)       │  │    │  │  ┌─────────────────────┐  │  │               │  │
│  │   │  │    [ALB Security Group]   │  │    │  │  │ SSM Endpoint        │  │  │               │  │
│  │   │  │      HTTP :80/:443        │  │    │  │  │ SSM Messages        │  │  │               │  │
│  │   │  └───────────┬───────────────┘  │    │  │  │ EC2 Messages        │  │  │               │  │
│  │   │              │                  │    │  │  │ [VPCE Security Grp] │  │  │               │  │
│  │   │              ▼                  │    │  │  └─────────────────────┘  │  │               │  │
│  │   │  ┌───────────────────────────┐  │    │  └───────────────────────────┘  │               │  │
│  │   │  │   Auto Scaling Group      │  │    └─────────────────────────────────┘               │  │
│  │   │  │  ┌─────────────────────┐  │  │                                                      │  │
│  │   │  │  │   EC2 Instance      │  │  │         ┌─────────────────────────────┐             │  │
│  │   │  │  │   (Launch Template) │  │  │         │      Lambda Function        │             │  │
│  │   │  │  │   [Backend Sec Grp] │◀─┼──┼─────────│    (Lex Fulfillment)        │             │  │
│  │   │  │  │   [IAM Role]        │  │  │         │    [Lambda Security Grp]    │             │  │
│  │   │  │  │                     │  │  │         │    [Lambda Execution Role]  │             │  │
│  │   │  │  │ ┌─────────────────┐ │  │  │         └──────────────┬──────────────┘             │  │
│  │   │  │  │ │ Docker Compose  │ │  │  │                        │                            │  │
│  │   │  │  │ │ ┌────┐ ┌─────┐  │ │  │  │                        │                            │  │
│  │   │  │  │ │ │Nginx│ │Flask│  │ │  │  │                        │                            │  │
│  │   │  │  │ │ │:80  │ │:8000│  │ │  │  │                        │                            │  │
│  │   │  │  │ │ └────┘ └──┬──┘  │ │  │  │                        │                            │  │
│  │   │  │  │ │      ┌────▼───┐ │ │  │  │                        │                            │  │
│  │   │  │  │ │      │ Ollama │ │ │  │  │                        │                            │  │
│  │   │  │  │ │      │ :11434 │ │ │  │  │                        │                            │  │
│  │   │  │  │ │      └────────┘ │ │  │  │                        │                            │  │
│  │   │  │  │ └─────────────────┘ │  │  │                        │                            │  │
│  │   │  │  └─────────────────────┘  │  │                        │                            │  │
│  │   │  └───────────────────────────┘  │                        │                            │  │
│  │   │              │                  │                        │                            │  │
│  │   │  ┌───────────▼───────────────┐  │                        │                            │  │
│  │   │  │  CloudWatch Alarms        │  │                        │                            │  │
│  │   │  │  (CPU High/Low → Scale)   │  │                        │                            │  │
│  │   │  └───────────────────────────┘  │                        │                            │  │
│  │   └─────────────────────────────────┘                        │                            │  │
│  │              │                                               │                            │  │
│  │   ┌──────────▼──────────┐                                    │                            │  │
│  │   │   Internet Gateway  │                                    │                            │  │
│  │   └─────────────────────┘                                    │                            │  │
│  │                                                              │                            │  │
│  └──────────────────────────────────────────────────────────────┼────────────────────────────┘  │
│                                                                 │                               │
│  ┌──────────────────────────────────────────────────────────────┼────────────────────────────┐  │
│  │                          MANAGED SERVICES                    │                            │  │
│  │                                                              │                            │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────▼────────────────┐           │  │
│  │  │   Cognito    │    │  Amazon Lex  │    │         CloudWatch Logs           │           │  │
│  │  │  Identity    │    │     V2       │    │  ┌────────────────────────────┐   │           │  │
│  │  │    Pool      │    │    Bot       │    │  │ /aws/lambda/lex-fulfillment│   │           │  │
│  │  │ [Unauth Role]│    │  [Lex Role]  │    │  └────────────────────────────┘   │           │  │
│  │  └──────┬───────┘    └───────┬──────┘    └───────────────────────────────────┘           │  │
│  │         │                    │                                                            │  │
│  │         │                    │           ┌───────────────────────────────────┐           │  │
│  │         │                    │           │           S3 Bucket               │           │  │
│  │         │                    │           │    (Audio Storage + Presigned)    │           │  │
│  │         │                    │           └───────────────────────────────────┘           │  │
│  │         │                    │                          ▲                                │  │
│  │         │                    │                          │                                │  │
│  │         │                    │           ┌──────────────┴────────────────────┐           │  │
│  │         │                    │           │         AWS Polly                 │           │  │
│  │         │                    │           │    (Neural TTS: Matthew/Joanna)   │           │  │
│  │         │                    │           └───────────────────────────────────┘           │  │
│  │         │                    │                                                            │  │
│  └─────────┼────────────────────┼────────────────────────────────────────────────────────────┘  │
│            │                    │                                                               │
└────────────┼────────────────────┼───────────────────────────────────────────────────────────────┘
             │                    │
             ▼                    ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    USER (Browser)                                                  │
│                                                                                                   │
│    React App → AWS SDK (Cognito Auth) → Lex RecognizeText → Conversational UI → Audio Playback   │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Terraform Resources Summary

| Category           | Resources                                                                                       | Count |
| ------------------ | ----------------------------------------------------------------------------------------------- | ----- |
| **Networking**     | VPC, Internet Gateway, Public Subnets (2), Private Subnets (2), Route Tables, VPC Endpoints (3) | 11    |
| **Compute**        | Launch Template, Auto Scaling Group, Scaling Policies (2), CloudWatch Alarms (2)                | 6     |
| **Load Balancing** | ALB, Target Groups (2), Listener                                                                | 4     |
| **Security**       | Security Groups (ALB, Backend, Lambda, VPC Endpoints), IAM Roles (EC2, Lambda, Lex, Cognito)    | 8+    |
| **Serverless**     | Lambda Function, CloudWatch Log Group                                                           | 2     |
| **AI/ML**          | Lex Bot, Bot Locale, Intents (7+), Bot Alias/Version                                            | 10+   |
| **Storage**        | S3 Bucket (audio)                                                                               | 1     |
| **Identity**       | Cognito Identity Pool, IAM Policies (S3, Polly, SSM)                                            | 4+    |

---

## AWS Services Deep Dive

### 1. Amazon Lex V2 - Conversational Interface

**Purpose**: Natural language understanding for user interactions

**Key Configuration** (`terraform/lex.tf`):

```hcl
# Bot locale with NLU confidence threshold
resource "aws_lexv2models_bot_locale" "en_us" {
  locale_id = "en_US"
  # Lowered from 0.70 to 0.40 to allow URL patterns to match
  n_lu_intent_confidence_threshold = 0.40

  voice_settings {
    voice_id = "Joanna"
    engine   = "neural"
  }
}
```

**Intents Configured**:
| Intent | Purpose | Sample Utterances |
|--------|---------|-------------------|
| `WelcomeIntent` | Greet users | "hello", "hi", "help me learn" |
| `ProvideURLIntent` | Accept learning URLs | "https", "learn from this", "use this url" |
| `StartLessonIntent` | Begin lessons | "start lesson", "play lesson 1" |
| `CheckStatusIntent` | Async status polling | "check status", "is it ready" |
| `NextLessonIntent` | Navigation | "next lesson", "continue" |

**Demo Talking Point**:

> "The Lex bot uses a 0.40 confidence threshold, which is lower than default. This allows it to catch URL patterns that might otherwise fall through to fallback."

---

### 2. Amazon Polly - Neural Voice Synthesis

**Purpose**: Convert lesson scripts into natural-sounding audio

**Voice Configuration** (`backend/src/services/audio_synthesizer.py`):

```python
VOICE_CONFIG = {
    'alex': {
        'voice_id': 'Matthew',
        'engine': 'neural',
        'language_code': 'en-US',
        'description': 'Senior engineer, warm and professional'
    },
    'sam': {
        'voice_id': 'Joanna',
        'engine': 'neural',
        'language_code': 'en-US',
        'description': 'Junior developer, friendly and curious'
    }
}
```

**SSML Templates for Natural Speech**:

```python
SSML_TEMPLATES = {
    'intro': '<speak><prosody rate="medium" pitch="medium">{text}</prosody></speak>',
    'discussion': '<speak><prosody rate="medium">{text}</prosody></speak>',
    'example': '<speak><prosody rate="95%">{text}</prosody></speak>',  # Slightly slower
    'recap': '<speak><prosody rate="medium" pitch="+5%">{text}</prosody></speak>',
    'outro': '<speak><prosody rate="medium" pitch="medium">{text}</prosody></speak>',
}
```

**Demo Talking Point**:

> "We use neural voices which sound more natural. The SSML templates adjust prosody - for example, code examples speak slightly slower for clarity."

---

### 3. Amazon Cognito - Unauthenticated Access

**Purpose**: Allow browser-based Lex access without login

**Configuration** (`terraform/cognito.tf`):

```hcl
resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "${local.name_prefix}-identity-pool"
  allow_unauthenticated_identities = true  # Key setting!
  allow_classic_flow               = false
}
```

**Frontend Integration** (`frontend/src/components/LexChat.jsx`):

```javascript
// Get Cognito identity for Lex access
const cognitoClient = new CognitoIdentityClient({ region: config.AWS_REGION });

const getIdResponse = await cognitoClient.send(
  new GetIdCommand({
    IdentityPoolId: config.COGNITO_IDENTITY_POOL_ID,
  })
);

const getCredsResponse = await cognitoClient.send(
  new GetCredentialsForIdentityCommand({
    IdentityId: getIdResponse.IdentityId,
  })
);
```

**Demo Talking Point**:

> "Cognito provides temporary AWS credentials to the browser. Users don't need to log in - the identity pool allows unauthenticated access with limited IAM permissions."

---

### 4. AWS Lambda - Lex Fulfillment

**Purpose**: Bridge between Lex and backend API

**Key Challenge & Solution**:

- **Problem**: Lex has a 30-second Lambda timeout, but lesson generation takes 54+ seconds
- **Solution**: Async pattern with status polling

**Async Implementation** (`lambda/lex_fulfillment/handler.py`):

```python
def handle_provide_url(event, slots, session_attributes):
    """Uses async endpoint to avoid Lex timeout."""
    # Extract URL from user input
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, input_transcript)

    # Call async endpoint - returns immediately
    api_response = call_backend_api('/api/lex/create-lesson-async', {
        'url': url,
        'user_id': user_id
    })

    # Store session for later lookup
    session_attributes['tutor_session_id'] = api_response.get('session_id', '')

    return build_response(
        event,
        session_attributes,
        "I'm creating your lessons now. This takes about a minute. "
        "Say 'check status' when you're ready!",
        close_intent=True
    )
```

**Demo Talking Point**:

> "Lex only allows 30 seconds for Lambda to respond, but our LLM needs about a minute. We solve this with an async pattern - Lambda kicks off the job and tells the user to check back."

---

## Code Walkthrough (During Resource Spin-Up)

### 1. Content Extraction Pipeline

**File**: `backend/src/services/content_extractor.py`

```python
class ContentExtractor:
    """Extracts readable content from web pages."""

    def extract(self, url: str) -> Dict:
        """
        1. Fetch the page with proper headers
        2. Try trafilatura for clean extraction (removes nav, ads)
        3. Fall back to BeautifulSoup if needed
        4. Return: {text, title, url, metadata}
        """
        # Uses Trafilatura for intelligent content extraction
        if TRAFILATURA_AVAILABLE:
            result = self._extract_with_trafilatura(html, url)
            if result and result.get('text'):
                return result

        # BeautifulSoup fallback
        return self._extract_with_bs4(html, url)
```

---

### 2. LLM Integration (Ollama)

**File**: `backend/src/services/podcast_generator.py`

```python
class PodcastGenerator:
    """Generates podcast scripts using Ollama LLM."""

    def __init__(self, ollama_host="http://localhost:11434", model="llama3.2"):
        self.ollama_host = ollama_host
        self.model = model
        self.timeout = 300  # 5 minutes for long generations

    def create_lesson_plan(self, content: str, title: str, num_lessons: int):
        """
        Step 1: Analyze content and create lesson structure
        Returns list of topics with key concepts
        """
        prompt = self.LESSON_PLAN_PROMPT.format(
            title=title,
            content=content[:8000],  # Truncate for context window
            num_lessons=num_lessons
        )
        return self._query_ollama(prompt)

    def generate_episode_script(self, topic: dict, lesson_context: dict):
        """
        Step 2: Generate two-host dialogue script
        Structure: Intro → Discussion → Examples → Recap → Outro
        """
        prompt = self.EPISODE_SCRIPT_PROMPT.format(...)
        return self._query_ollama(prompt)
```

**Demo Talking Point**:

> "The LLM generates both the lesson plan AND the dialogue script. It creates natural conversation between Alex and Sam, including 'aha moments' where Sam connects concepts."

---

### 3. Audio Synthesis Pipeline

**File**: `backend/src/services/audio_synthesizer.py`

```python
def synthesize_podcast(self, script: List[Dict], session_id: str, lesson_num: int):
    """Synthesize full podcast from script segments."""

    audio_segments = []
    last_speaker = None

    for segment in script:
        speaker = segment['speaker']  # 'alex' or 'sam'
        text = segment['text']
        segment_type = segment['segment_type']  # intro/discussion/etc

        # Add natural pauses between speakers
        if last_speaker is not None:
            pause_ms = 500 if speaker != last_speaker else 200
            audio_segments.append(self._generate_silence(pause_ms))

        # Synthesize with SSML prosody
        audio_bytes, duration = self.synthesize_segment(
            text=text,
            speaker=speaker,
            segment_type=segment_type
        )
        audio_segments.append(audio_bytes)
        last_speaker = speaker

    # Concatenate and upload to S3
    return self._upload_to_s3(combined_audio, session_id, lesson_num)
```

---

### 4. Audio Stitching

**File**: `backend/src/services/audio_stitcher.py`

```python
class AudioStitcher:
    """Stitches audio segments with professional transitions."""

    def _stitch_with_pydub(self, chunks: List[AudioChunk]) -> Tuple[bytes, int]:
        """Professional-quality audio stitching."""
        combined = AudioSegment.empty()

        for chunk in chunks:
            audio = AudioSegment.from_mp3(io.BytesIO(chunk.audio_bytes))

            # Add crossfade for smooth transitions
            if combined.duration_seconds > 0:
                combined = combined.append(audio, crossfade=50)  # 50ms
            else:
                combined += audio

        # Normalize audio levels
        if self.config.normalize_audio:
            combined = normalize(combined, headroom=self.config.target_dbfs)

        return combined.export(format='mp3').read()
```

---

### 5. Audio Coordination

**File**: `backend/src/services/audio_coordinator.py`

```python
class AudioCoordinator:
    """Orchestrates the complete audio synthesis pipeline."""

    def process_episode(self, script: EpisodeScript, session_id: str):
        """
        Full pipeline:
        1. Validate script structure
        2. Format with SSML
        3. Synthesize with Polly (parallel segments)
        4. Stitch segments together
        5. Upload to S3
        6. Return playable URL
        """
        job = SynthesisJob(
            job_id=f"{session_id}_{script.lesson_number}",
            status=JobStatus.PENDING
        )

        # Progress tracking
        job.status = JobStatus.VALIDATING
        job.progress_percent = 10

        job.status = JobStatus.SYNTHESIZING
        job.progress_percent = 30

        result = self.synthesizer.synthesize_episode(script)

        job.status = JobStatus.COMPLETED
        job.progress_percent = 100

        return job
```

---

## Deployment Steps

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

### 2. Review Plan

```bash
terraform plan -out=tfplan
```

### 3. Apply Infrastructure

```bash
terraform apply tfplan
```

**Resources Created**:

- VPC with public/private subnets
- EC2 Auto Scaling Group
- Application Load Balancer
- S3 bucket for audio
- Lex V2 bot with intents
- Lambda for Lex fulfillment
- Cognito Identity Pool
- IAM roles and policies

### 4. User Data Execution (Automatic)

The EC2 instance runs this on startup (`terraform/templates/container_user_data.sh`):

```bash
# Install Docker
dnf install -y git docker

# Install Docker Compose v2
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose

# Clone and configure
git clone ${git_repo_url} app
cd app

# Create .env with Terraform values
cat > .env << 'ENVFILE'
AWS_REGION=${aws_region}
S3_BUCKET=${s3_bucket}
VITE_LEX_BOT_ID=${lex_bot_id}
VITE_LEX_BOT_ALIAS_ID=${lex_bot_alias_id}
VITE_COGNITO_IDENTITY_POOL_ID=${cognito_identity_pool_id}
OLLAMA_MODEL=${ollama_model}
ENVFILE

# Build and start
docker compose build --no-cache
docker compose up -d
```

---

## Live Demo Flow

### Step 1: Access the Application

```
http://<ALB_DNS_NAME>
```

### Step 2: Interact with Lex Chatbot

1. Say "Hello" → WelcomeIntent
2. Paste a URL → ProvideURLIntent (async processing starts)
3. Say "check status" → CheckStatusIntent (polls backend)
4. Say "start lesson 1" → StartLessonIntent (returns audio URL)

### Step 3: Show Backend Logs (via AWS SSM)

```bash
# Start SSM session to EC2 instance (no SSH key needed!)
aws ssm start-session --target <instance-id>

# Once connected, view live logs
cd /opt/ai-tutor/app
sudo docker compose logs -f backend

# Or run a single command without interactive session
aws ssm start-session --target <instance-id> \
  --document-name AWS-StartInteractiveCommand \
  --parameters command="cd /opt/ai-tutor/app && sudo docker compose logs --tail=50 backend"
```

**Why SSM over SSH?**

- No need to manage SSH keys or open port 22
- Full audit trail in CloudTrail
- Works through NAT/private subnets
- IAM-based access control

### Step 4: Demonstrate Audio

- Play the generated podcast audio
- Point out the two different voices (Matthew vs Joanna)
- Note the natural pauses between speakers

---

## Concrete Request Flow Example

Let's walk through a single request in the AI Tutor application:

### 1. Initial Chat Message Flow

```
Browser hits http://<ALB_DNS_NAME>/

ALB receives the request on port 80

ALB routes to healthy EC2 instance in Target Group (health check: /health)

On that instance, request hits the Frontend container (Nginx on port 80)

Nginx serves the React SPA (index.html, JS bundles)

React app loads and initializes:
  - Fetches Cognito credentials from Identity Pool
  - Creates Lex Runtime client with temporary AWS credentials
```

### 2. User Submits a URL (Lex Flow)

```
User types: "https://en.wikipedia.org/wiki/Python"

React Frontend (LexChat.jsx):
  - Calls AWS Lex V2 Runtime API directly (browser → AWS)
  - Uses Cognito Identity Pool for unauthenticated access

AWS Lex V2:
  - Matches "ProvideURLIntent" (confidence > 0.40)
  - Invokes Lambda fulfillment function

Lambda Function (in VPC public subnet):
  - Extracts URL from user input via regex
  - Calls Backend API: POST http://10.0.1.x:8000/api/lex/create-lesson-async
  - Returns immediately: "I'm analyzing that content now..."

Backend Container (Gunicorn with 1 worker, 8 threads):
  - Receives request on thread #3
  - Starts background thread for async processing:
    1. Extracts content from URL (trafilatura/BeautifulSoup)
    2. Calls Ollama container: POST http://ollama:11434/api/generate
    3. Parses LLM response into lesson topics
    4. Stores session in memory dict (sessions[session_id])
  - Returns 202 Accepted with session_id

Response flows back:
  Lambda → Lex → Browser (via AWS SDK)
```

### 3. User Checks Status

```
User says: "check status"

Lex matches "CheckStatusIntent" → Lambda invoked

Lambda:
  - Retrieves tutor_session_id from Lex session attributes
  - Calls: GET http://10.0.1.x:8000/api/lex/session-status/{session_id}

Backend (same worker process):
  - Looks up session in memory: sessions.get(session_id)
  - Returns status: "ready" with lesson titles

Lambda returns: "Your lessons are ready! Say 'start lesson 1' to begin."
```

### 4. User Starts a Lesson (Audio Generation)

```
User clicks lesson card in React UI

Frontend calls: GET /api/session/{id}/lesson/1

Nginx proxies: GET http://backend:8000/api/session/{id}/lesson/1

Backend Gunicorn (worker #1, thread #5):
  1. Retrieves lesson topic from session
  2. Calls AudioCoordinator.generate_lesson_audio():

     a. PodcastScriptGenerator:
        - POST http://ollama:11434/api/generate
        - Prompt: "Create a two-host podcast script..."
        - Timeout: 300 seconds (LLM generation is slow)

     b. AudioSynthesizer (for each dialogue line):
        - AWS Polly API: synthesize_speech()
        - Host Alex: Voice="Matthew", Engine="neural"
        - Host Sam: Voice="Joanna", Engine="neural"
        - Returns MP3 audio bytes

     c. AudioStitcher:
        - Concatenates MP3 segments with pydub
        - Adds 300ms silence between speakers
        - Exports final MP3

     d. Upload to S3:
        - Bucket: troy-ai-tutor-dev-audio
        - Key: sessions/{session_id}/lesson_{n}.mp3
        - Generate presigned URL (1 hour expiry)

Response flows back:
  Backend → Nginx → ALB → Browser

Frontend receives audio_url, plays via <audio> element
```

### 5. Failure Scenarios & Recovery

```
If EC2 instance dies:
  - ALB health check fails after 30 seconds (3 checks × 10s interval)
  - ASG launches replacement instance (min_size=1)
  - User data script runs: pulls code, starts Docker Compose
  - New instance registers with Target Group
  - Sessions in memory are LOST (stateless design limitation)
  - User must re-submit URL to create new session

If Gunicorn worker crashes:
  - Single worker mode: container health check fails
  - Docker restarts container (restart: unless-stopped)
  - In-flight requests fail; sessions in memory are LOST
  - Subsequent requests work after container restart

If Ollama container is slow/unresponsive:
  - Backend request times out after 300 seconds
  - Returns 504 Gateway Timeout
  - User can retry; Ollama container stays running

If Lambda times out (>120s):
  - Lex returns error to browser
  - Async pattern mitigates this: Lambda returns in <5s
  - Background processing continues on backend

If Lex confidence is low (<0.40):
  - FallbackIntent triggers
  - Returns: "I didn't catch that. Try sharing a URL..."
```

### 6. The "Automatic" Parts

```
Auto Scaling:
  - CloudWatch alarm monitors CPU > 70% for 2 minutes
  - ASG scales out: launches additional EC2 instance
  - ALB distributes traffic across both instances
  - Scale-in after CPU < 30% for 5 minutes

Health Checks:
  - ALB checks /health every 10 seconds
  - Docker checks container health via curl
  - Unhealthy containers restarted automatically

Session Management:
  - Lex session persists in AWS (managed service)
  - Frontend stores Lex session ID in localStorage
  - Backend sessions are ephemeral (in-memory)

Credential Rotation:
  - Cognito provides temporary credentials (1 hour)
  - Frontend automatically refreshes via AWS SDK
  - EC2 uses instance profile (auto-rotated by AWS)
```

### Request Path Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER BROWSER                                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │ React App   │───▶│ AWS SDK     │───▶│ Cognito Identity Pool           │  │
│  │ (LexChat)   │    │ (Lex Client)│    │ (Temp Credentials)              │  │
│  └─────────────┘    └──────┬──────┘    └─────────────────────────────────┘  │
└────────────────────────────┼────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS MANAGED SERVICES                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │ Amazon Lex V2   │───▶│ Lambda Function │───▶│ VPC (Public Subnet)     │  │
│  │ (NLU + Dialog)  │    │ (Fulfillment)   │    │ Security Group          │  │
│  └─────────────────┘    └────────┬────────┘    └─────────────────────────┘  │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │ HTTP POST to EC2 Private IP
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EC2 INSTANCE (Docker Host)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Docker Compose Network                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │    │
│  │  │   Frontend   │  │   Backend    │  │         Ollama             │ │    │
│  │  │   (Nginx)    │  │  (Gunicorn)  │  │     (llama3.2:1b)          │ │    │
│  │  │   Port 80    │  │  Port 8000   │  │      Port 11434            │ │    │
│  │  │              │  │              │  │                            │ │    │
│  │  │  /api/* ─────┼─▶│  Flask App   │─▶│  POST /api/generate        │ │    │
│  │  │  (proxy)     │  │              │  │  (LLM inference)           │ │    │
│  │  └──────────────┘  └──────┬───────┘  └────────────────────────────┘ │    │
│  └───────────────────────────┼──────────────────────────────────────────┘    │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS AI SERVICES                                      │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────────┐ │
│  │     Amazon Polly        │    │              Amazon S3                   │ │
│  │  (Neural TTS)           │    │    (Audio Storage + Presigned URLs)      │ │
│  │  - Matthew (Alex)       │    │    troy-ai-tutor-dev-audio               │ │
│  │  - Joanna (Sam)         │    │                                          │ │
│  └─────────────────────────┘    └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Technical Highlights

### 1. Async Processing Pattern

```
User → Lex → Lambda → Backend (async) → Returns immediately
User → "check status" → Lex → Lambda → Backend → Session ready!
```

### 2. Timeout Configuration (300s throughout)

```python
# Gunicorn (backend/Dockerfile)
CMD ["gunicorn", "--timeout", "300", ...]

# Ollama client (podcast_generator.py)
self.timeout = 300

# Nginx (frontend/nginx.conf)
proxy_read_timeout 300s;
```

### 3. Session Persistence

```javascript
// LexChat.jsx - Persist session ID across page refreshes
const [sessionId] = useState(() => {
  const stored = localStorage.getItem("lex_session_id");
  if (stored) return stored;
  const newId = uuidv4();
  localStorage.setItem("lex_session_id", newId);
  return newId;
});
```

### 4. Docker Service Architecture

```yaml
services:
  frontend: # Nginx + React (port 80)
  backend: # Flask + Gunicorn (port 8000)
  ollama: # LLM server (port 11434)
  model-init: # One-time model download
```

---

## Questions to Prepare For

1. **"Why not use a single voice?"**

   > Two voices create engaging podcast-style content. Research shows dialogue format improves retention.

2. **"Why Ollama instead of Bedrock?"**

   > Ollama runs locally on EC2 - no per-token costs, faster iteration during development. Easy to swap for Bedrock in production.

3. **"How do you handle Lex timeout?"**

   > Async pattern: Lambda starts the job and returns immediately. User polls with "check status" intent.

4. **"What if content extraction fails?"**

   > Trafilatura handles most sites. BeautifulSoup fallback for edge cases. Graceful error messages to user.

5. **"How does the frontend talk to Lex?"**
   > AWS SDK in browser. Cognito provides temporary credentials. RecognizeTextCommand for each message.

---

## Demo Checklist

- [ ] Terraform resources deployed
- [ ] EC2 instance healthy
- [ ] All 3 Docker containers running
- [ ] Lex bot version published
- [ ] Test URL ready (Wikipedia article works well)
- [ ] CloudWatch logs accessible
- [ ] Audio playback working

---

## Backend Tests

The `backend/tests/` directory contains **136 unit and integration tests** that validate the entire AI Personal Tutor pipeline.

### Test Suite Overview

| Test File                    | Tests   | What It Covers                             |
| ---------------------------- | ------- | ------------------------------------------ |
| `test_content_extraction.py` | 30      | Web scraping, URL validation, LRU caching  |
| `test_podcast_generation.py` | 38      | LLM prompts, dialogue scripts, SSML output |
| `test_audio_synthesis.py`    | 45      | AWS Polly, audio stitching, coordination   |
| `test_integration.py`        | 23      | Session CRUD, API endpoints, health checks |
| **Total**                    | **136** |                                            |

### When to Run Tests

| Scenario                      | Command                                                | Why                                 |
| ----------------------------- | ------------------------------------------------------ | ----------------------------------- |
| Before committing code        | `pytest tests/ -v`                                     | Catch regressions early             |
| After modifying service logic | `pytest tests/test_<service>.py -v`                    | Validate specific component changes |
| Before deployment             | `pytest tests/ -v --tb=short`                          | Ensure all systems work together    |
| Debugging a specific test     | `pytest tests/test_integration.py::TestAPIv2Routes -v` | Isolate and fix failures            |
| Generating coverage report    | `pytest tests/ --cov=src --cov-report=html`            | Identify untested code paths        |

### How to Run Tests

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source .venv/bin/activate

# Run all 136 tests with verbose output
PYTHONPATH=src pytest tests/ -v

# Run specific test file
PYTHONPATH=src pytest tests/test_content_extraction.py -v

# Run specific test class
PYTHONPATH=src pytest tests/test_integration.py::TestTutorSessionManager -v

# Run with coverage report (generates htmlcov/ directory)
PYTHONPATH=src pytest tests/ --cov=src --cov-report=html

# Run only failed tests from last run
PYTHONPATH=src pytest tests/ --lf

# Stop on first failure (useful for debugging)
PYTHONPATH=src pytest tests/ -x
```

### Test Categories Explained

#### Content Extraction Tests (`test_content_extraction.py`)

Validates the URL-to-text pipeline:

- **ContentExtractor**: HTML parsing, script tag removal, network error handling
- **ContentProcessor**: Text chunking, topic extraction, code block detection
- **URLValidator**: URL format validation, normalization, domain extraction
- **ContentCache**: LRU eviction, TTL expiration, cache statistics

#### Podcast Generation Tests (`test_podcast_generation.py`)

Validates script creation:

- **Speaker/DialogueTurn**: Voice mapping (Alex→Matthew, Sam→Joanna), duration estimation
- **EpisodeScript**: Script structure, speaker balance validation
- **ScriptFormatter**: SSML formatting for AWS Polly, SRT subtitle generation
- **PodcastGenerator**: Ollama integration, JSON response parsing

#### Audio Synthesis Tests (`test_audio_synthesis.py`)

Validates audio pipeline:

- **EnhancedAudioSynthesizer**: AWS Polly client mocking, cost estimation ($4/1M chars)
- **AudioStitcher**: Audio concatenation, pause calculation between speakers
- **AudioCoordinator**: Job tracking, batch processing, cleanup of old jobs

#### Integration Tests (`test_integration.py`)

Validates end-to-end workflows:

- **TutorSessionManager**: Session CRUD operations, lesson generation
- **APIv2Routes**: HTTP endpoint testing (POST, GET, DELETE), status codes
- **Health checks**: Service connectivity validation

### Key Testing Patterns Used

- **Mocking**: External services (AWS Polly, Ollama) are mocked to enable fast, isolated tests
- **Fixtures**: Shared test data via `@pytest.fixture` decorators
- **Parametrization**: Data-driven tests with `@pytest.mark.parametrize`
- **Integration isolation**: API tests use Flask test client, no real HTTP calls

### Example Test Output

```bash
$ PYTHONPATH=src pytest tests/ -v --tb=short

tests/test_content_extraction.py::TestContentExtractor::test_extract_success PASSED
tests/test_content_extraction.py::TestContentExtractor::test_extract_removes_script_tags PASSED
tests/test_content_extraction.py::TestURLValidator::test_normalize_url PASSED
...
tests/test_integration.py::TestAPIv2Routes::test_health_endpoint PASSED
tests/test_integration.py::TestAPIv2Routes::test_delete_session_endpoint PASSED

========================= 136 passed in 12.34s =========================
```

> 📖 **For detailed test documentation**, see [backend/tests/README.md](backend/tests/README.md)

---

## Troubleshooting History

This section documents the major issues encountered during development and deployment, along with the debugging process and solutions.

### Summary of Issues Resolved

| #   | Issue                   | Root Cause                    | Solution                    | Architectural Reasoning                                                                                                                 |
| --- | ----------------------- | ----------------------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Lambda syntax errors    | Missing `except` blocks       | Fixed exception handlers    | Proper error handling prevents silent failures and enables meaningful error messages to users                                           |
| 2   | Lambda VPC connectivity | Private subnets, no NAT       | Moved to public subnets     | For dev/cost savings, public subnets avoid NAT Gateway hourly charges (~$32/mo); production would use NAT or VPC endpoints for security |
| 3   | Nginx `/api/api/` path  | Double `/api` prefix          | Set `VITE_API_URL` to empty | Single source of truth for API path prefix; Nginx handles routing, frontend shouldn't duplicate                                         |
| 4   | Lex intent confidence   | 0.70 threshold too high       | Lowered to 0.40             | URLs are atypical NLU patterns; lower threshold trades precision for recall, acceptable since we validate URLs in Lambda                |
| 5   | Lex 30-second timeout   | LLM takes 54+ seconds         | Async pattern with polling  | Decouples synchronous Lex from long-running processes; follows AWS best practice for Lambda-based workflows                             |
| 6   | Gunicorn session loss   | Multi-worker memory isolation | Single worker, 8 threads    | Thread-safe in-memory storage; production would use Redis for horizontal scaling, but single-worker suffices for demo                   |
| 7   | Lex session refresh     | Session ID regenerated        | localStorage persistence    | Client-side state management; Lex sessions are server-side but keyed by client ID, so persistence maintains continuity                  |
| 8   | 504 Gateway timeout     | 60s default timeouts          | 300s across all layers      | End-to-end timeout alignment prevents partial failures; ALB→Nginx→Gunicorn→Ollama chain must all exceed max request time                |
| 9   | Docker port exposure    | Missing port mapping          | Added `8000:8000`           | Explicit port publishing required for host-to-container communication; Lambda calls EC2 host IP, not container network                  |
| 10  | Cognito access denied   | Missing IAM permissions       | Added `lex:RecognizeText`   | Principle of least privilege; Cognito unauth role only gets specific Lex actions needed for chat functionality                          |

---

### 1. Lambda Syntax Errors

**Symptom**: Lambda function failing immediately on invocation

**Diagnosis**:

```bash
# Check Lambda logs via CloudWatch
aws logs tail /aws/lambda/Troy-ai-tutor-dev-lex-fulfillment --follow
```

**Root Cause**: Missing `except` blocks in Python try statements

**Solution**: Fixed all incomplete exception handlers in `lambda/lex_fulfillment/handler.py`

---

### 2. Lambda VPC Connectivity (No Internet Access)

**Symptom**: Lambda timing out when calling backend API

**Diagnosis**:

```bash
# Check Lambda configuration
aws lambda get-function-configuration \
  --function-name Troy-ai-tutor-dev-lex-fulfillment \
  --query 'VpcConfig'

# Lambda was in private subnets with no NAT Gateway
```

**Root Cause**: Lambda in private subnets couldn't reach the ALB (public endpoint)

**Solution**: Moved Lambda to public subnets with proper security groups. For production, would use NAT Gateway or VPC endpoints.

```bash
# Update Lambda VPC config
aws lambda update-function-configuration \
  --function-name Troy-ai-tutor-dev-lex-fulfillment \
  --vpc-config SubnetIds=subnet-xxx,subnet-yyy,SecurityGroupIds=sg-zzz
```

---

### 3. Nginx Double Path Issue (`/api/api/`)

**Symptom**: Frontend API calls returning 404

**Diagnosis**:

```bash
# SSM into instance and check nginx logs
aws ssm start-session --target i-0296b2262a52021ce
sudo docker compose logs frontend | grep api

# Saw requests going to /api/api/health instead of /api/health
```

**Root Cause**: `VITE_API_URL` was set to `/api`, but frontend code already prepended `/api/`

**Solution**: Set `VITE_API_URL` to empty string in `.env`

```bash
# Fixed in docker-compose.yml
VITE_API_URL=${VITE_API_URL:-}  # Empty default
```

---

### 4. Lex Intent Confidence Threshold

**Symptom**: URLs being routed to FallbackIntent instead of ProvideURLIntent

**Diagnosis**:

```bash
# Test Lex recognition
aws lexv2-runtime recognize-text \
  --bot-id SBSIXCSH73 \
  --bot-alias-id QX1ZJI4KAG \
  --locale-id en_US \
  --session-id test123 \
  --text "https://example.com/article"

# Response showed low confidence for ProvideURLIntent
```

**Root Cause**: Default NLU confidence threshold (0.70) was too high for URL patterns

**Solution**: Lowered threshold to 0.40 in `terraform/lex.tf`

```hcl
n_lu_intent_confidence_threshold = 0.40
```

---

### 5. Lex 30-Second Lambda Timeout

**Symptom**: Lex returning timeout errors; lesson generation takes 54+ seconds

**Diagnosis**:

```bash
# Check Lambda timeout
aws lambda get-function-configuration \
  --function-name Troy-ai-tutor-dev-lex-fulfillment \
  --query 'Timeout'
# Returns: 30 (Lex maximum)

# Backend logs showed Ollama taking 54+ seconds
aws ssm start-session --target <instance-id>
cd /opt/ai-tutor/app && sudo docker compose logs backend | grep "duration"
```

**Root Cause**: Lex enforces 30-second max Lambda timeout; LLM generation exceeds this

**Solution**: Implemented async pattern with status polling

```python
# New endpoints added to backend
/api/lex/create-lesson-async  # Returns immediately, processes in background
/api/lex/session-status       # Polls for completion

# New Lex intent
CheckStatusIntent: "check status", "is it ready?", "status"
```

---

### 6. Gunicorn Multi-Worker Session Loss

**Symptom**: Session created but status check returns "session not found"

**Diagnosis**:

```bash
# Check Gunicorn config
aws ssm start-session --target <instance-id>
cd /opt/ai-tutor/app && cat backend/Dockerfile | grep gunicorn

# Was using 2 workers - each has separate memory!
```

**Root Cause**: In-memory session storage with 2 Gunicorn workers meant requests could hit different workers

**Solution**: Changed to 1 worker with 8 threads

```dockerfile
CMD ["gunicorn", "--workers", "1", "--threads", "8", ...]
```

---

### 7. Lex Session Loss on Page Refresh

**Symptom**: Refreshing browser lost all conversation context

**Diagnosis**: Lex session ID was being regenerated with `uuidv4()` on each page load

**Root Cause**: React state reset on refresh; session ID not persisted

**Solution**: Store session ID in localStorage

```javascript
const [sessionId] = useState(() => {
  const stored = localStorage.getItem("lex_session_id");
  if (stored) return stored;
  const newId = uuidv4();
  localStorage.setItem("lex_session_id", newId);
  return newId;
});
```

---

### 8. Audio Generation 504 Gateway Timeout

**Symptom**: Audio generation requests failing with 504 after ~60 seconds

**Diagnosis**:

```bash
# Check ALB idle timeout
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn <alb-arn> \
  --query 'Attributes[?Key==`idle_timeout.timeout_seconds`]'
# Returns: 60 (default)

# Audio generation takes 2-3 minutes for full podcast
```

**Root Cause**: Default 60-second timeouts at multiple layers:

- ALB idle timeout: 60s
- Nginx proxy timeout: 60s
- Gunicorn worker timeout: 120s
- Ollama client timeout: 120s

**Solution**: Increased all timeouts to 300 seconds

```bash
# ALB timeout
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <alb-arn> \
  --attributes Key=idle_timeout.timeout_seconds,Value=300

# Nginx (frontend/nginx.conf)
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
proxy_read_timeout 300s;

# Gunicorn (backend/Dockerfile)
CMD ["gunicorn", "--timeout", "300", ...]

# Ollama client (podcast_generator.py)
self.timeout = 300
```

---

### 9. Docker Port Exposure

**Symptom**: Lambda couldn't reach backend on port 8000

**Diagnosis**:

```bash
# Check container ports
aws ssm start-session --target <instance-id>
sudo docker compose ps

# Backend showed no port mapping!
```

**Root Cause**: Missing port exposure in docker-compose.yml

**Solution**: Added explicit port mapping

```yaml
backend:
  ports:
    - "8000:8000" # Host:Container
```

---

### 10. Cognito Unauthenticated Access Denied

**Symptom**: Browser console showing "Access Denied" for Lex calls

**Diagnosis**:

```bash
# Check identity pool config
aws cognito-identity describe-identity-pool \
  --identity-pool-id <pool-id>

# Check IAM role permissions
aws iam get-role-policy \
  --role-name <cognito-unauth-role> \
  --policy-name LexAccess
```

**Root Cause**: IAM policy missing `lex:RecognizeText` permission

**Solution**: Updated Cognito unauthenticated role policy

```json
{
  "Effect": "Allow",
  "Action": [
    "lex:RecognizeText",
    "lex:RecognizeUtterance",
    "lex:DeleteSession",
    "lex:PutSession"
  ],
  "Resource": "arn:aws:lex:*:*:bot-alias/*/*"
}
```

---

### Useful SSM Debugging Commands

```bash
# Start interactive session
aws ssm start-session --target <instance-id>

# View user-data execution log
sudo cat /var/log/user-data.log

# Check all container status
cd /opt/ai-tutor/app && sudo docker compose ps

# View specific container logs
sudo docker compose logs -f backend
sudo docker compose logs -f frontend
sudo docker compose logs -f ollama

# Check if Ollama model is loaded
curl http://localhost:11434/api/tags

# Test backend health
curl http://localhost:8000/health

# Restart all services
sudo docker compose restart

# Rebuild and restart (after code changes)
sudo docker compose up -d --build

# Check environment variables
sudo docker compose exec backend env | grep -E 'AWS|OLLAMA|S3'
```

---

_Good luck with your assessment! 🎓_
