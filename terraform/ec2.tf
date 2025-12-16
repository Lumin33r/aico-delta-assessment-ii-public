# =============================================================================
# EC2 Instances and Auto Scaling Groups
# =============================================================================

# -----------------------------------------------------------------------------
# Backend Launch Template
# -----------------------------------------------------------------------------

resource "aws_launch_template" "backend" {
  name_prefix   = "${local.name_prefix}-backend-"
  image_id      = data.aws_ami.amazon_linux_2023.id
  instance_type = var.instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.backend.name
  }

  vpc_security_group_ids = [aws_security_group.backend.id]

  key_name = var.key_name != "" ? var.key_name : null

  user_data = base64encode(templatefile("${path.module}/templates/backend_user_data.sh", {
    aws_region   = var.aws_region
    s3_bucket    = aws_s3_bucket.audio.bucket
    ollama_model = var.ollama_model
    environment  = var.environment
  }))

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${local.name_prefix}-backend"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# -----------------------------------------------------------------------------
# Backend Auto Scaling Group
# -----------------------------------------------------------------------------

resource "aws_autoscaling_group" "backend" {
  name                = "${local.name_prefix}-backend-asg"
  vpc_zone_identifier = aws_subnet.public[*].id
  target_group_arns   = [aws_lb_target_group.backend.arn]

  min_size         = 1
  max_size         = 3
  desired_capacity = 1

  health_check_type         = "ELB"
  health_check_grace_period = 300

  launch_template {
    id      = aws_launch_template.backend.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${local.name_prefix}-backend"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
  }
}

# -----------------------------------------------------------------------------
# Frontend Launch Template
# -----------------------------------------------------------------------------

resource "aws_launch_template" "frontend" {
  name_prefix   = "${local.name_prefix}-frontend-"
  image_id      = data.aws_ami.amazon_linux_2023.id
  instance_type = "t3.micro"

  vpc_security_group_ids = [aws_security_group.frontend.id]

  key_name = var.key_name != "" ? var.key_name : null

  user_data = base64encode(templatefile("${path.module}/templates/frontend_user_data.sh", {
    aws_region            = var.aws_region
    cognito_identity_pool = var.create_cognito ? aws_cognito_identity_pool.main[0].id : ""
    lex_bot_id            = var.create_lex_bot ? aws_lexv2models_bot.tutor[0].id : ""
    lex_bot_alias_id      = var.create_lex_bot ? aws_lexv2models_bot_alias.main[0].bot_alias_id : ""
    api_url               = "http://${aws_lb.main.dns_name}"
    environment           = var.environment
  }))

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${local.name_prefix}-frontend"
    }
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_cognito_identity_pool.main,
    aws_lexv2models_bot_alias.main
  ]
}

# -----------------------------------------------------------------------------
# Frontend Auto Scaling Group
# -----------------------------------------------------------------------------

resource "aws_autoscaling_group" "frontend" {
  name                = "${local.name_prefix}-frontend-asg"
  vpc_zone_identifier = aws_subnet.public[*].id
  target_group_arns   = [aws_lb_target_group.frontend.arn]

  min_size         = 1
  max_size         = 2
  desired_capacity = 1

  health_check_type         = "ELB"
  health_check_grace_period = 300

  launch_template {
    id      = aws_launch_template.frontend.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${local.name_prefix}-frontend"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
  }
}
