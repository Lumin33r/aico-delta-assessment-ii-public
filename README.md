Assessment II

# App Deployment using Terraform & AWS AI Services

---

## Overview

This assessment evaluates your understanding of the Infrastructure as Code concepts and AWS AI services covered these past several weeks. Automation of application deployment and integration of AI capabilities is critical to designing reliable, reusable and scalable architecture.

Using Terraform to provision resources, and AWS AI services to enhance your application, you will deploy a React frontend utilizing API endpoints to interact with a database and AWS AI services.  

We've provided a React frontend in the resources directory that is ready for integration AWS AI services (Lex, Polly, Comprehend, and Rekognition).  We've also provided a starter template for a Flask backend, which you can disregard if you decide to use API gateway.

You're welcome to use any resources we've created up til now (Flask apps, React apps, terraform files, etc).  The goal of this assessment is to test your ability to connect everything you've learned so far and to establish a foundation for building out the rest of an automated application deployment infrastructure by the end of this cohort.

---

## Objectives

The core goal is to automate the deployment of a Flask application with a React frontend and integrate AWS AI services using Terraform. To do this, you must meet these objectives:

1. Use Terraform to provision a cloud infrastructure for your application
2. Build a React frontend that consumes your Flask API
3. Integrate at least two AWS AI services (Lex, Polly, Comprehend, or Rekognition) into your application

We can outline these objectives to give you an idea of what will be scored.

## Exam Outline

**1. Terraform Configuration (20%)**
   - Set up and utilize a remote backend with DynamoDB & S3 (you can add and leave this commented out to keep state local)
   - Write necessary terraform configurations for allowing public access (Security Groups, VPC components, etc.)
   - Include appropriate outputs and validation
   - Resources can cleanly be destroyed with `terraform destroy` and recreated with `terraform apply`

**2. AWS AI Services Integration (25%)**

   - Integrate any of the following AWS AI services into your application:
      - Amazon Lex with intents & fallback intent: Chatbot interface for user interactions
      - Amazon Polly & Amazon Transcribe: Text-to-speech and speech-to-text
      - Amazon Comprehend & Rekognition: Sentiment & Image analysis
   - Configure proper IAM roles and permissions for AI services

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
   - React frontend is built and served (can be hosted on S3 bucket, or served from EC2)
   - Application demonstrates successful integration with AWS AI services

**5. Documentation & Presentation (20%)**

   - Clear documentation written
   - Architecture diagram provided showing application flow and AI service integration
   - Ability to present and talk through application deployment, AI service integration, and answer questions
   - All deliverables organized in a Github repository

**6. Stretch Goals (Bonus Points)**

   - Up to 2 additional points for integrating second and third set of AWS AI services
   - Serve Flask on a separate private EC2 with Gunicorn for a more secure deployment
   - Implement CI/CD pipeline by automating deployment with a single action and adding clear logging & tests
   - Implement Cloudfront with S3 bucket deployment
   - Use either modules or meta arguments in your Terraform files
   - Present early (1 additional point per # days early)

---

## Deliverables

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

## Timeline

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

## Hints

- Time management is key.  Go for the implementations that you're most comfortable or familiar with.  You can always add on later
- You don't necessarily need to create all resources.  Working resources like VPCs, security groups, roles/policies, can be shared and imported.
- A working demo is live, tagged with 'aico-aii-demo'.  You can view resources tagged with this in AWS console to inspect details like what VPC it's using
- Ask questions and help one another out as needed.  This *isn't* cheating.  Technical abilities aren't the only skills that matter.  Collaboration and communication are also crucial skills for employment.

---

## Troubleshooting

### API Gateway URL not found

If you get an error about API Gateway URL:
1. Check that Terraform deployment completed successfully
2. Verify `outputs.json` exists and contains `api_gateway_url`
3. Manually get the URL: `cd terraform && terraform output api_gateway_url`

### CORS errors in browser

- Verify API Gateway has OPTIONS methods configured
- Check that Lambda functions return CORS headers
- Ensure frontend is using the correct API Gateway URL

### Lambda function errors

- Check CloudWatch Logs for the specific Lambda function
- Verify IAM permissions for DynamoDB and AI services
- Ensure Lambda environment variables are set correctly

### Frontend not loading

- Verify S3 bucket has static website hosting enabled
- Check S3 bucket policy allows public read access
- Ensure frontend build completed successfully

---

[Getting Started](./getting_started.md)
