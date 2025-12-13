terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Create additional TF files for:

# vpc.tfå
#   - Create new OR import/reuse existing:
#     - VPC
#     - Subnets
#     - Internet Gateway
#     - Route Tables

# ec2.tf
#   - Create EC2 instances with appropriate AMI
#   - Create security group allowing HTTP (80), HTTPS (443), SSH (22)
#     - Also allow for any additional use cases such as Flask (5000)

# rds.tf
#   - Create RDS instance for PostgreSQL or MySQL

# iam.tf
#   - Public front end access (via EC2 or S3)
#   - Database access (RDS, DynamoDB, or EC2 PostgreSQL)
#   - AI Services (Lex, Polly, Comprehend, Rekognition)
#   - CloudWatch Logs


# lambda.tf
#   - Create/Read/Update/Delete functions if using API gateway
#   - Lex chatbot integration
#   - Polly text-to-speech
#   - Comprehend sentiment analysis
#   - Package Lambda code and deploy

# api-gateway.tf
#   - Create API Gateway REST API
#   - Create API Gateway resources and methods for:
#     - /users (GET, POST)
#     - /users/{id} (GET, PUT, DELETE)
#     - /api/chat (POST) - for Lex
#     - /api/text-to-speech (POST) - for Polly
#     - /api/analyze-sentiment (POST) - for Comprehend
#   - Configure API Gateway integration with Lambda functions
#   - Deploy API Gateway stage

# s3.tf
#   - Create S3 bucket for Terraform state
#   - Create S3 bucket and configure for static website hosting (if using)

# dynamodb.tf
#   - Create DynamoDB table for state locking
#   - Also for DynamoDB data store if using this instead of PSQL/RDS

# lex.tf, comprehend.tf, polly.tf
#   - Lex bot resource
#   - Lex bot intents
#   - Comprehend entity recognizer
#   - Comprehend document classifier
#   - Polly voices

# outputs.tf
#   - Front End public IP (either via EC2 or S3+Cloudfront)
#   - EC2 public IP (if using Flask)
#   - API Gateway endpoint URL (if using API Gateway)
#   - Lambda function ARNs
#   - S3 bucket URLs
#   - Add other useful outputs

# variables.tf
#   - Any variables required