Assessment II

# App Deployment using Terraform & AWS AI Services

---

## Overview

This assessment evaluates your understanding of the Infrastructure as Code concepts and AWS AI services covered these past several weeks. Automation of application deployment and integration of AI capabilities is critical to designing reliable, reusable and scalable architecture.

Using Terraform to provision resources, and AWS AI services to enhance your application, you will deploy a Flask backend with a React frontend of your choosing, between the Todo-List application which uses MySQL and the User DB application which uses PSQL.

- https://github.com/codeplatoon-devops/todolist-flask
- https://github.com/codeplatoon-devops/user-db-flask.git

Both Flask applications are simple applications with basic logic built in. Your goal is to provision the infrastructure to support it, build a React frontend, and integrate AWS AI services (Lex, Polly, Comprehend, and Rekognition) to enhance the user experience.

---

## Objectives

The core goal is to automate the deployment of a Flask application with a React frontend and integrate AWS AI services using Terraform. To do this, you must meet these objectives:

1. Use Terraform to provision a cloud infrastructure for your application
2. Build a React frontend that consumes your Flask API
3. Integrate at least two AWS AI services (Lex, Polly, Comprehend, or Rekognition) into your application

We can outline these objectives to give you an idea of what will be scored.

## Exam Outline

**1. Terraform Configuration (20%)**
   - Set up and utilize a remote backend with DynamoDB & S3 
   - Write a terraform configuration to create at least one EC2 instance
   - Write terraform configurations for other resources necessary for allowing public access to the application (Security Groups, VPC components, etc.)
   - Include appropriate outputs and validation

**2. AWS AI Services Integration (25%)**

   - Integrate at least two of the following AWS AI services into your application:
      - Amazon Lex: Chatbot interface for user interactions
      - Amazon Polly: Text-to-speech for audio responses
      - Amazon Comprehend: Sentiment analysis or entity recognition on user input
      - Amazon Rekognition: Image analysis (labels, faces, text detection)
   - Integrate at least two AWS Lambda functions for serverless processing, API integration, or event-driven workflows
   - Configure proper IAM roles and permissions for AI services and Lambda functions

**3. Database Configuration (15%)**

   - Database can be configured using one of the following options:
      - RDS (PostgreSQL or MySQL): Managed database service
      - PostgreSQL on EC2: Self-managed database running on an EC2 instance
      - DynamoDB: NoSQL database 
   - Database being updated by the application via API is verifiable
   - Appropriate security groups and network configurations for database access

**4. Application Deployment (20%)**

   - Deployed API endpoints for CRUD'ing DB and invoking AWS AI services either via Flask or API Gateway
      - Flask backend is deployed to EC2 and configured to be accessible via API (if using Flask)
      - API Gateway deployment is configured via Terraform (if using Lambdas + API Gateway)
   - React frontend is built and served (can be hosted on S3 with CloudFront, or served from EC2)
   - Application demonstrates successful integration with at least two AWS AI services and at least two Lambdas
   - EC2 instance can be SSHed onto, and CLI commands can be used to confirm services & dependencies

**5. Documentation & Presentation (20%)**

   - Clear documentation written
   - Architecture diagram provided showing application flow and AI service integration
   - Ability to present and talk through application deployment, AI service integration, and answer questions
   - All deliverables organized in a Github repository

**6. Stretch Goals (Bonus Points)**

   - Additional points for integrating third and fourth AWS services
   - Use Gunicorn for a more secure Flask deployment
   - Implement CI/CD pipeline for automated deployments
   - Create a serverless architecture using Lambda for API endpoints or processing
   - Present early (1 additional point per # days early)

---

# Deliverables

Systems and applications are only as effective as their ease of use. All of the following should be provided in a way that a team member or colleague can repeat your entire flow.

1. Github Repository with documentation & architecture diagram of your system showing AI service integration
2. All necessary terraform configurations
3. React frontend source code with AI service integration
4. API endpoints for CRUD & AI features either via Flask Backend or Lambdas & API Gateway
5. Documentation including:
   - Project overview & description
   - Architecture diagram & description
   - Set up steps, terminal commands & additional instructions
   - Documentation for configuration and best practices (masked Env variables, IAM policies, API keys)

Remember, deliverables should not only be created with functionality and performance in mind, but also for replicability and clarity. Capability draws attention; measurable results create value.

---

# Timeline

You'll have one week to complete the assessment. Points will be docked for every additional class day the assessment is not completed and presented. Here are some **pro tips** to help keep you moving:

- One high value advantage of IaC is reusability. Don't be afraid to reuse the terraform code you've already written, even if just as a foundation or starting point
- Terraform outputs can be used to log convenient data to your console
- AWS SDK for JavaScript (in React) and Boto3 (in Flask) simplify AI service integration
- Lambda functions can be used to offload processing, integrate services, or create event-driven workflows
- Start with one AI service integration and add more incrementally
- Test AI services and Lambda functions independently before full integration
- Consider using Lambda for AI service calls to reduce EC2 load and improve scalability
- Remember, you have flexibility not only in how you implement requirements, but how you present as well. For example, when demonstrating Lex integration, you can show chat interactions in the UI or use AWS Console to verify bot configurations.

Good luck!

---

[Getting Started](./getting_started.md)