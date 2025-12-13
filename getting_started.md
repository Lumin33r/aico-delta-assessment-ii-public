# Assessment II - Starter Project

## Getting Started

### Prerequisites
- AWS Account with appropriate permissions
- Terraform installed
- Node.js and npm installed
- Python 3.8+ installed
- AWS CLI configured

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd aico-delta-assessment-ii
   ```

2. **Confirm AWS credential configuration**
   ```bash
   aws configure
   ```

3. **Deploy infrastructure with Terraform**
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

4. **Set up Flask backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   # TODO: Set environment variables
   python app.py
   ```

5. **Set up React frontend**
   ```bash
   cd frontend
   npm install
   # TODO: Configure API endpoint in .env
   npm start
   ```

## TODO List

### Terraform
- [ ] Configure VPC and networking
- [ ] Create EC2 instance with user data (for Flask backend)
- [ ] Set up security groups
- [ ] Create IAM roles for AI services and Lambda functions
- [ ] Configure database (choose one):
  - [ ] RDS (PostgreSQL or MySQL) - recommended for production
  - [ ] PostgreSQL on EC2 - good for learning and experimentation
  - [ ] DynamoDB - for serverless/NoSQL experimentation
- [ ] Create Lambda functions for CRUD operations (alternative to Flask)
- [ ] Create Lambda functions for AI services (alternative to Flask)
- [ ] Configure API Gateway with Lambda integrations
- [ ] Set up Terraform remote backend with S3 and DynamoDB (stretch goal)
- [ ] Add appropriate outputs

### Backend - Choose Flask OR API Gateway + Lambda
**Option 1: Flask Backend (EC2)**
- [ ] Implement Lex chatbot integration
- [ ] Implement Polly text-to-speech
- [ ] Implement Comprehend sentiment analysis (bonus)
- [ ] Implement Rekognition image analysis (bonus)
- [ ] Configure database connection (RDS, PostgreSQL on EC2, or DynamoDB)
- [ ] Add error handling

**Option 2: API Gateway + Lambda (Serverless)**
- [ ] Create Lambda functions for CRUD operations (create, read, update, delete users)
- [ ] Create Lambda functions for AI services (Lex, Polly, Comprehend)
- [ ] Configure API Gateway routes and integrations
- [ ] Test Lambda functions independently
- [ ] Add error handling and logging

### Frontend
- [ ] Build chat UI for Lex
- [ ] Add text-to-speech controls
- [ ] Display sentiment analysis results
- [ ] Add image upload and analysis
- [ ] Style the application

### Documentation
- [ ] Create architecture diagram
- [ ] Document deployment steps
- [ ] Document AI service configurations
- [ ] Add testing instructions

## Database Options

### Option 1: RDS (Recommended for Production)
- Managed database service with automatic backups and scaling
- Supports PostgreSQL and MySQL
- Configure via Terraform using `aws_db_instance` resource

### Option 2: PostgreSQL on EC2 (Good for Learning)
- Install PostgreSQL directly on an EC2 instance
- Full control over database configuration
- Good for understanding database administration
- Configure via user_data script or Ansible

### Option 3: DynamoDB (For Experimentation)
- NoSQL database for serverless architectures
- Great for experimenting with serverless patterns
- Integrates well with Lambda functions
- Configure via Terraform using `aws_dynamodb_table` resource

## Architecture Options

You have two main architecture options:

### Option 1: Flask Backend on EC2
- Traditional server-based architecture
- Flask handles all API endpoints and AI service integrations
- Database connections from EC2 instance
- Good for learning and full control

### Option 2: API Gateway + Lambda (Serverless)
- Serverless architecture with Lambda functions
- API Gateway routes requests to appropriate Lambda functions
- Lambda functions handle CRUD operations and AI services independently
- No EC2 instance needed for API (can still use EC2 for database if needed)
- Better scalability and cost efficiency

**Note:** These are independent implementations. You can implement both to demonstrate flexibility, but they should work independently.

## Resources
- [AWS Lex Documentation](https://docs.aws.amazon.com/lex/)
- [AWS Polly Documentation](https://docs.aws.amazon.com/polly/)
- [AWS Comprehend Documentation](https://docs.aws.amazon.com/comprehend/)
- [AWS Rekognition Documentation](https://docs.aws.amazon.com/rekognition/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [AWS DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)