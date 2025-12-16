# AI Personal Tutor - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                    │
│  │  Lex Chat    │    │ Lesson List  │    │Podcast Player│                    │
│  │  Component   │    │  Component   │    │  Component   │                    │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                    │
│         │                   │                   │                            │
│  ┌──────┴───────────────────┴───────────────────┴──────┐                     │
│  │                React Frontend (Vite)                 │                     │
│  │                    Port 3000 (dev)                   │                     │
│  └──────────────────────────┬──────────────────────────┘                     │
└─────────────────────────────┼───────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS INFRASTRUCTURE                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Application Load Balancer                          │   │
│  │                         (HTTP :80)                                    │   │
│  └────────────┬─────────────────────────────────────────┬───────────────┘   │
│               │ /                                       │ /api/*            │
│               ▼                                         ▼                   │
│  ┌─────────────────────────┐           ┌─────────────────────────────────┐  │
│  │    Frontend EC2/ASG     │           │      Backend EC2/ASG            │  │
│  │    ┌─────────────┐      │           │  ┌───────────────────────────┐  │  │
│  │    │   Nginx     │      │           │  │    Flask API (Gunicorn)   │  │  │
│  │    │  Port 80    │      │           │  │        Port 8000          │  │  │
│  │    └─────────────┘      │           │  └─────────────┬─────────────┘  │  │
│  └─────────────────────────┘           │                │                │  │
│                                        │                ▼                │  │
│                                        │  ┌───────────────────────────┐  │  │
│                                        │  │   Ollama LLM Server       │  │  │
│                                        │  │      Port 11434           │  │  │
│                                        │  │  (llama3.2 model)         │  │  │
│                                        │  └───────────────────────────┘  │  │
│                                        └─────────────────────────────────┘  │
│                                                                             │
│  ┌────────────────────────┐  ┌────────────────────────────────────────────┐ │
│  │   Amazon Lex V2 Bot    │  │           AWS Services                     │ │
│  │  ┌──────────────────┐  │  │  ┌─────────────────┐  ┌────────────────┐  │ │
│  │  │  WelcomeIntent   │  │  │  │   AWS Polly     │  │   S3 Bucket    │  │ │
│  │  │ CreateLessonPlan │  │  │  │  Matthew Voice  │  │  Audio Storage │  │ │
│  │  │   StartLesson    │  │  │  │  Joanna Voice   │  │                │  │ │
│  │  │   HelpIntent     │  │  │  └─────────────────┘  └────────────────┘  │ │
│  │  │  FallbackIntent  │  │  │                                          │ │
│  │  └────────┬─────────┘  │  │  ┌─────────────────┐                     │ │
│  │           │            │  │  │ Cognito Identity│                     │ │
│  │           ▼            │  │  │      Pool       │                     │ │
│  │  ┌──────────────────┐  │  │  │ (Unauth Access) │                     │ │
│  │  │ Lambda Fulfillment│  │  │  └─────────────────┘                     │ │
│  │  └──────────────────┘  │  │                                          │ │
│  └────────────────────────┘  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. URL Ingestion Flow

```
User → LexChat → Lex Bot → Lambda → Backend API → ContentExtractor
                                              ↓
                              PodcastGenerator → Ollama
                                              ↓
                                    Create Lesson Plan
                                              ↓
                                    Return Session ID
```

### 2. Lesson Generation Flow

```
User → Select Lesson → Backend API → PodcastGenerator
                                           ↓
                          Generate Dialogue Script (Ollama)
                                           ↓
                               AudioSynthesizer → AWS Polly
                                           ↓
                        Matthew (Alex) + Joanna (Sam) Voices
                                           ↓
                              Concatenate Audio Segments
                                           ↓
                                    Upload to S3
                                           ↓
                              Return Presigned URL
```

### 3. Audio Playback Flow

```
User → PodcastPlayer → Presigned S3 URL → Audio Stream
                           ↓
              Transcript Display (synchronized)
```

## Component Details

### Frontend Components

| Component           | Purpose                                |
| ------------------- | -------------------------------------- |
| `LexChat.jsx`       | Chat interface for Lex bot interaction |
| `PodcastPlayer.jsx` | Audio player with transcript display   |
| `LessonList.jsx`    | List of available lessons              |
| `Layout.jsx`        | App shell with navigation              |

### Backend Services

| Service            | Purpose                             |
| ------------------ | ----------------------------------- |
| `ContentExtractor` | Extracts readable content from URLs |
| `PodcastGenerator` | Generates two-host dialogue scripts |
| `AudioSynthesizer` | Synthesizes multi-voice audio       |

### AWS Resources

| Resource | Purpose                             |
| -------- | ----------------------------------- |
| VPC      | Network isolation                   |
| ALB      | Load balancing & routing            |
| EC2/ASG  | Compute (frontend & backend)        |
| Lex V2   | Conversational interface            |
| Cognito  | Unauthenticated access for frontend |
| Lambda   | Lex fulfillment                     |
| Polly    | Text-to-speech synthesis            |
| S3       | Audio file storage                  |

## Podcast Hosts

### Alex (Matthew Voice)

- **Role**: Senior Software Engineer (15 years experience)
- **Style**: Patient, uses analogies, explains concepts clearly
- **Voice**: AWS Polly Neural - Matthew (warm, confident)

### Sam (Joanna Voice)

- **Role**: Junior Developer (2 years experience)
- **Style**: Curious, asks clarifying questions, summarizes key points
- **Voice**: AWS Polly Neural - Joanna (friendly, enthusiastic)

## Episode Structure

1. **Intro (1 min)**: Alex welcomes listeners, introduces topic
2. **Discussion (6-8 min)**: Back-and-forth explaining concepts
3. **Examples (2-3 min)**: Real-world applications
4. **Recap (1-2 min)**: Sam summarizes key takeaways
5. **Outro (30 sec)**: Alex thanks listeners, previews next lesson

## Security Considerations

- Cognito Identity Pool for unauthenticated Lex access
- IAM roles with least privilege
- S3 bucket with presigned URLs (1-hour expiry)
- VPC security groups limiting access
- No public database access

## Scalability

- Auto Scaling Groups for EC2 instances
- S3 for unlimited audio storage
- Polly scales automatically
- Lex handles concurrent conversations
