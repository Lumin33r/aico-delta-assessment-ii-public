# =============================================================================
# S3 Bucket for Audio Storage
# =============================================================================

resource "aws_s3_bucket" "audio" {
  # Ensure bucket name doesn't start with hyphen and is lowercase
  bucket = lower("${var.project_name}-audio-${var.environment}-${random_id.suffix.hex}")

  tags = {
    Name = "${local.name_prefix}-audio"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "audio" {
  bucket = aws_s3_bucket.audio.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning
resource "aws_s3_bucket_versioning" "audio" {
  bucket = aws_s3_bucket.audio.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle rules for cleanup
resource "aws_s3_bucket_lifecycle_configuration" "audio" {
  bucket = aws_s3_bucket.audio.id

  rule {
    id     = "cleanup-old-lessons"
    status = "Enabled"

    filter {
      prefix = "lessons/"
    }

    # Move to Glacier after 30 days
    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    # Delete after 90 days
    expiration {
      days = 90
    }
  }

  rule {
    id     = "cleanup-temp"
    status = "Enabled"

    filter {
      prefix = "temp/"
    }

    # Delete temp files after 1 day
    expiration {
      days = 1
    }
  }
}

# CORS configuration for frontend access
resource "aws_s3_bucket_cors_configuration" "audio" {
  bucket = aws_s3_bucket.audio.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"] # Restrict in production
    expose_headers  = ["ETag", "Content-Length"]
    max_age_seconds = 3000
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "audio" {
  bucket = aws_s3_bucket.audio.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
