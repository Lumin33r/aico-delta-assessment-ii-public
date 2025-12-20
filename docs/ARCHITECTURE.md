# AI Personal Tutor - Architecture Overview

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          AWS CLOUD (us-west-2)                                            │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    VPC (10.0.0.0/16) - vpc.tf                                       │  │
│  │                                                                                                     │  │
│  │   ┌─────────────────────────────────┐        ┌─────────────────────────────────┐                   │  │
│  │   │   Public Subnet A (10.0.1.0/24) │        │   Public Subnet B (10.0.2.0/24) │                   │  │
│  │   │          us-west-2a             │        │          us-west-2b             │                   │  │
│  │   └────────────────┬────────────────┘        └────────────────┬────────────────┘                   │  │
│  │                    │                                          │                                     │  │
│  │   ┌────────────────┴──────────────────────────────────────────┴────────────────┐                   │  │
│  │   │                    Application Load Balancer - alb.tf                       │                   │  │
│  │   │                    ┌──────────────────────────────────────┐                 │                   │  │
│  │   │                    │  HTTP Listener (:80)                 │                 │                   │  │
│  │   │                    │  • / → Frontend Target Group         │                 │                   │  │
│  │   │                    │  • /api/* → Backend Target Group     │                 │                   │  │
│  │   │                    └──────────────────────────────────────┘                 │                   │  │
│  │   └─────────────────────────────────┬───────────────────────────────────────────┘                   │  │
│  │                                     │                                                               │  │
│  │   ┌─────────────────────────────────┴───────────────────────────────────────────┐                   │  │
│  │   │               Auto Scaling Group (1-3 instances) - ec2.tf                   │                   │  │
│  │   │  ┌────────────────────────────────────────────────────────────────────────┐ │                   │  │
│  │   │  │  EC2 Instance (t3.medium) - Launch Template                            │ │                   │  │
│  │   │  │  ┌──────────────────────────────────────────────────────────────────┐  │ │                   │  │
│  │   │  │  │                     Docker Containers                             │  │ │                   │  │
│  │   │  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐  │  │ │                   │  │
│  │   │  │  │  │  Frontend   │ │  Backend    │ │   Ollama    │ │ PostgreSQL │  │  │ │                   │  │
│  │   │  │  │  │  (Nginx)    │ │  (Flask)    │ │   (LLM)     │ │   (DB)     │  │  │ │                   │  │
│  │   │  │  │  │  Port 80    │ │  Port 8000  │ │  Port 11434 │ │  Port 5432 │  │  │ │                   │  │
│  │   │  │  │  │  React App  │ │  Gunicorn   │ │ llama3.2:1b │ │  pgdata    │  │  │ │                   │  │
│  │   │  │  │  └─────────────┘ └──────┬──────┘ └─────────────┘ └────────────┘  │  │ │                   │  │
│  │   │  │  │                         │                                        │  │ │                   │  │
│  │   │  │  └─────────────────────────┼────────────────────────────────────────┘  │ │                   │  │
│  │   │  └────────────────────────────┼───────────────────────────────────────────┘ │                   │  │
│  │   └───────────────────────────────┼─────────────────────────────────────────────┘                   │  │
│  │                                   │                                                                 │  │
│  │   ┌───────────────────────────────┼─────────────────────────────────────────────┐                   │  │
│  │   │   Private Subnets (10.0.10.0/24, 10.0.11.0/24) - Lambda VPC                 │                   │  │
│  │   │   ┌───────────────────────────┴─────────────────────────────────────────┐   │                   │  │
│  │   │   │                  Lambda Function - lambda.tf                        │   │                   │  │
│  │   │   │                  (lex-fulfillment, Python 3.11)                     │   │                   │  │
│  │   │   │                  Proxies requests to Backend ALB                    │   │                   │  │
│  │   │   └─────────────────────────────────────────────────────────────────────┘   │                   │  │
│  │   └─────────────────────────────────────────────────────────────────────────────┘                   │  │
│  │                                                                                                     │  │
│  │   VPC Endpoints (vpc_endpoints.tf):  SSM, SSM Messages, EC2 Messages                               │  │
│  │   Internet Gateway, NAT Gateway (optional), Route Tables                                            │  │
│  │                                                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                           │
│  ┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐                      │
│  │     Amazon Lex V2 Bot - lex.tf       │  │        AWS Services                   │                      │
│  │  ┌────────────────────────────────┐  │  │  ┌────────────────────────────────┐  │                      │
│  │  │  Intents:                      │  │  │  │   S3 Bucket - s3.tf            │  │                      │
│  │  │  • WelcomeIntent               │  │  │  │   • Audio file storage         │  │                      │
│  │  │  • ProvideURLIntent            │  │  │  │   • Lifecycle rules (90 days)  │  │                      │
│  │  │  • StartLessonIntent           │  │  │  │   • CORS enabled               │  │                      │
│  │  │  • NextLessonIntent            │  │  │  │   • Server-side encryption     │  │                      │
│  │  │  • RepeatLessonIntent          │  │  │  └────────────────────────────────┘  │                      │
│  │  │  • GetProgressIntent           │  │  │  ┌────────────────────────────────┐  │                      │
│  │  │  • GetHelpIntent               │  │  │  │   AWS Polly (via IAM)          │  │                      │
│  │  │  • FallbackIntent (built-in)   │  │  │  │   • Neural TTS                 │  │                      │
│  │  └────────────────────────────────┘  │  │  │   • Matthew voice (Alex)       │  │                      │
│  │  ┌────────────────────────────────┐  │  │  │   • Joanna voice (Sam)         │  │                      │
│  │  │  Bot Locale: en_US             │  │  │  └────────────────────────────────┘  │                      │
│  │  │  Confidence Threshold: 0.40    │  │  │  ┌────────────────────────────────┐  │                      │
│  │  │  Voice: Joanna (Neural)        │  │  │  │   Secrets Manager - secrets.tf │  │                      │
│  │  └────────────────────────────────┘  │  │  │   • PostgreSQL credentials     │  │                      │
│  │  ┌────────────────────────────────┐  │  │  │   • 32-char random password    │  │                      │
│  │  │  Lambda Fulfillment Hook       │──┼──│──│   • Fetched at EC2 startup     │  │                      │
│  │  └────────────────────────────────┘  │  │  └────────────────────────────────┘  │                      │
│  └──────────────────────────────────────┘  │  ┌────────────────────────────────┐  │                      │
│                                            │  │   CloudWatch Logs              │  │                      │
│  ┌──────────────────────────────────────┐  │  │   • Lambda logs                │  │                      │
│  │   Cognito Identity Pool - cognito.tf │  │  │   • EC2 metrics                │  │                      │
│  │   • Unauthenticated access           │  │  │   • Auto Scaling alarms        │  │                      │
│  │   • Lex bot permissions              │  │  └────────────────────────────────┘  │                      │
│  └──────────────────────────────────────┘  └──────────────────────────────────────┘                      │
│                                                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                  IAM Roles & Policies - iam.tf                                      │  │
│  │  ┌─────────────────────────────┐ ┌─────────────────────────────┐ ┌───────────────────────────────┐  │  │
│  │  │  Backend EC2 Role           │ │  Lambda Execution Role      │ │  Cognito Unauth Role          │  │  │
│  │  │  • S3 access                │ │  • Basic execution          │ │  • Lex RecognizeText          │  │  │
│  │  │  • Polly access             │ │  • VPC access               │ │  • Lex RecognizeUtterance     │  │  │
│  │  │  • CloudWatch logs          │ │  • ELB describe             │ │  • Lex session management     │  │  │
│  │  │  • Secrets Manager          │ └─────────────────────────────┘ └───────────────────────────────┘  │  │
│  │  │  • SSM Session Manager      │ ┌─────────────────────────────┐                                    │  │
│  │  └─────────────────────────────┘ │  Lex Service Role           │                                    │  │
│  │                                  │  • Lex runtime permissions  │                                    │  │
│  │                                  └─────────────────────────────┘                                    │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              Security Groups - security_groups.tf                                   │  │
│  │  ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐                   │  │
│  │  │  ALB Security Group    │ │  Backend Security Group│ │  Lambda Security Group │                   │  │
│  │  │  • Inbound: 80, 443    │ │  • Inbound: 80 from ALB│ │  • Outbound: All       │                   │  │
│  │  │  • Outbound: All       │ │  • Inbound: 8000 (ALB) │ │  • VPC CIDR access     │                   │  │
│  │  └────────────────────────┘ │  • Outbound: All       │ └────────────────────────┘                   │  │
│  │                             └────────────────────────┘                                              │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Terraform Resource Summary

### Networking (vpc.tf, vpc_endpoints.tf)

| Resource                      | Name/Count         | Purpose                    |
| ----------------------------- | ------------------ | -------------------------- |
| `aws_vpc`                     | main               | Primary VPC (10.0.0.0/16)  |
| `aws_subnet`                  | public[2]          | Public subnets (2 AZs)     |
| `aws_subnet`                  | private[2]         | Private subnets for Lambda |
| `aws_internet_gateway`        | main               | Internet access            |
| `aws_nat_gateway`             | main (optional)    | Private subnet outbound    |
| `aws_route_table`             | public, private    | Routing configuration      |
| `aws_route_table_association` | public[2], priv[2] | Subnet associations        |
| `aws_vpc_endpoint`            | ssm, ssm_messages  | SSM Session Manager        |
| `aws_vpc_endpoint`            | ec2_messages       | EC2 messaging              |

### Compute (ec2.tf)

| Resource                      | Name/Count | Purpose                       |
| ----------------------------- | ---------- | ----------------------------- |
| `aws_launch_template`         | backend    | EC2 instance configuration    |
| `aws_autoscaling_group`       | backend    | Auto scaling (1-3 instances)  |
| `aws_autoscaling_policy`      | scale_up   | Scale out on high CPU         |
| `aws_autoscaling_policy`      | scale_down | Scale in on low CPU           |
| `aws_cloudwatch_metric_alarm` | high_cpu   | Trigger scale up (>70% CPU)   |
| `aws_cloudwatch_metric_alarm` | low_cpu    | Trigger scale down (<30% CPU) |

### Load Balancing (alb.tf)

| Resource              | Name/Count | Purpose                    |
| --------------------- | ---------- | -------------------------- |
| `aws_lb`              | main       | Application Load Balancer  |
| `aws_lb_target_group` | frontend   | Route to EC2 port 80       |
| `aws_lb_target_group` | backend    | Route to EC2 port 8000     |
| `aws_lb_listener`     | http       | HTTP listener with routing |

### Serverless (lambda.tf)

| Resource                   | Name/Count      | Purpose                    |
| -------------------------- | --------------- | -------------------------- |
| `aws_lambda_function`      | lex_fulfillment | Lex intent fulfillment     |
| `aws_lambda_permission`    | lex             | Allow Lex to invoke Lambda |
| `aws_cloudwatch_log_group` | lambda          | Lambda function logs       |

### Conversational AI (lex.tf)

| Resource                      | Name/Count | Purpose                  |
| ----------------------------- | ---------- | ------------------------ |
| `aws_lexv2models_bot`         | tutor      | Main chatbot             |
| `aws_lexv2models_bot_locale`  | en_us      | English locale config    |
| `aws_lexv2models_intent`      | 7 intents  | Conversation intents     |
| `aws_lexv2models_bot_version` | main       | Versioned bot deployment |

### Authentication (cognito.tf)

| Resource                                     | Name/Count | Purpose            |
| -------------------------------------------- | ---------- | ------------------ |
| `aws_cognito_identity_pool`                  | main       | Federated identity |
| `aws_cognito_identity_pool_roles_attachment` | main       | Role mapping       |

### Storage (s3.tf)

| Resource                                             | Name/Count | Purpose                 |
| ---------------------------------------------------- | ---------- | ----------------------- |
| `aws_s3_bucket`                                      | audio      | Audio file storage      |
| `aws_s3_bucket_public_access_block`                  | audio      | Block public access     |
| `aws_s3_bucket_versioning`                           | audio      | Enable versioning       |
| `aws_s3_bucket_lifecycle_configuration`              | audio      | 90-day expiration       |
| `aws_s3_bucket_cors_configuration`                   | audio      | CORS for browser access |
| `aws_s3_bucket_server_side_encryption_configuration` | audio      | AES-256 encryption      |

### Secrets (secrets.tf)

| Resource                            | Name/Count | Purpose                  |
| ----------------------------------- | ---------- | ------------------------ |
| `random_password`                   | postgres   | Generate secure password |
| `aws_secretsmanager_secret`         | postgres   | Store credentials        |
| `aws_secretsmanager_secret_version` | postgres   | Secret value             |

### Security (security_groups.tf, iam.tf)

| Resource                         | Name/Count       | Purpose                       |
| -------------------------------- | ---------------- | ----------------------------- |
| `aws_security_group`             | alb              | ALB inbound rules             |
| `aws_security_group`             | backend          | EC2 inbound rules             |
| `aws_security_group`             | lambda           | Lambda VPC access             |
| `aws_security_group`             | vpc_endpoints    | VPC endpoint access           |
| `aws_iam_role`                   | backend          | EC2 instance role             |
| `aws_iam_role`                   | lambda_execution | Lambda execution role         |
| `aws_iam_role`                   | cognito_unauth   | Cognito unauthenticated       |
| `aws_iam_role`                   | lex              | Lex service role              |
| `aws_iam_instance_profile`       | backend          | EC2 instance profile          |
| `aws_iam_role_policy`            | 8 policies       | Resource-specific permissions |
| `aws_iam_role_policy_attachment` | 3 attachments    | AWS managed policies          |

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

## Docker Container Stack

Each EC2 instance runs these containers via `docker-compose.yml`:

| Container  | Image                 | Port  | Purpose                 |
| ---------- | --------------------- | ----- | ----------------------- |
| frontend   | nginx:alpine (custom) | 80    | React app + API proxy   |
| backend    | python:3.11-slim      | 8000  | Flask API with Gunicorn |
| ollama     | ollama/ollama         | 11434 | Local LLM inference     |
| postgres   | postgres:15-alpine    | 5432  | PostgreSQL database     |
| model-init | ollama/ollama         | -     | One-time model pull     |

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

## Podcast Hosts

### Alex (Matthew Voice)

- **Role**: Senior Software Engineer (15 years experience)
- **Style**: Patient, uses analogies, explains concepts clearly
- **Voice**: AWS Polly Neural - Matthew (warm, confident)

### Sam (Joanna Voice)

- **Role**: Junior Developer (2 years experience)
- **Style**: Curious, asks clarifying questions, summarizes key points
- **Voice**: AWS Polly Neural - Joanna (friendly, enthusiastic)

## Security Architecture

### Secrets Management

- PostgreSQL credentials stored in **AWS Secrets Manager**
- 32-character randomly generated passwords
- EC2 fetches credentials at startup via IAM role
- No hardcoded passwords in code or docker-compose

### Network Security

- VPC isolation with public/private subnets
- Security groups enforce least-privilege access
- ALB only exposes ports 80/443
- Backend only accepts traffic from ALB
- Lambda runs in private subnets

### IAM Least Privilege

| Role           | Permissions                                        |
| -------------- | -------------------------------------------------- |
| Backend EC2    | S3, Polly, CloudWatch, Secrets Manager, SSM        |
| Lambda         | VPC access, ELB describe, CloudWatch logs          |
| Cognito Unauth | Lex text/utterance recognition, session management |
| Lex Service    | Runtime permissions only                           |

### Data Protection

- S3 server-side encryption (AES-256)
- Presigned URLs expire after 1 hour
- No public database access
- HTTPS recommended for production (ACM certificate)

## Scalability

| Component     | Scaling Method                       |
| ------------- | ------------------------------------ |
| EC2 Instances | Auto Scaling Group (1-3 instances)   |
| S3 Storage    | Unlimited, managed by AWS            |
| AWS Polly     | Fully managed, auto-scales           |
| Lex Bot       | Managed service, handles concurrency |
| Lambda        | Auto-scales with invocations         |
| PostgreSQL    | Per-instance (consider RDS for HA)   |
