# =============================================================================
# EC2 and Auto Scaling Configuration
# =============================================================================
# Backend compute resources with load balancing
# =============================================================================

# -----------------------------------------------------------------------------
# Launch Template: Backend
# -----------------------------------------------------------------------------

resource "aws_launch_template" "backend" {
  name          = "${var.project_name}-${var.environment}-backend-lt"
  description   = "Launch template for backend instances"
  image_id      = data.aws_ami.amazon_linux_2023.id
  instance_type = var.instance_type

  key_name = var.key_name != "" ? var.key_name : null

  iam_instance_profile {
    arn = aws_iam_instance_profile.backend.arn
  }

  vpc_security_group_ids = [aws_security_group.backend.id]

  user_data = base64encode(templatefile("${path.module}/templates/container_user_data.sh", {
    aws_region               = var.aws_region
    s3_bucket                = aws_s3_bucket.audio.id
    ollama_model             = var.ollama_model
    environment              = var.environment
    git_repo_url             = var.git_repo_url
    lex_bot_id               = var.create_lex_bot ? aws_lexv2models_bot.tutor[0].id : ""
    lex_bot_alias_id         = var.lex_bot_alias_id
    cognito_identity_pool_id = var.create_cognito ? aws_cognito_identity_pool.main[0].id : ""
  }))

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  monitoring {
    enabled = true
  }

  tag_specifications {
    resource_type = "instance"
    tags = merge(var.tags, {
      Name = "${var.project_name}-${var.environment}-backend"
    })
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-backend-lt"
  })
}

# -----------------------------------------------------------------------------
# Auto Scaling Group: Backend
# -----------------------------------------------------------------------------

resource "aws_autoscaling_group" "backend" {
  name                = "${var.project_name}-${var.environment}-backend-asg"
  vpc_zone_identifier = aws_subnet.public[*].id
  target_group_arns   = [aws_lb_target_group.frontend.arn]
  health_check_type   = "ELB"

  min_size         = var.min_instances
  max_size         = var.max_instances
  desired_capacity = var.desired_capacity

  launch_template {
    id      = aws_launch_template.backend.id
    version = "$Latest"
  }

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-${var.environment}-backend"
    propagate_at_launch = true
  }

  dynamic "tag" {
    for_each = var.tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }
}

# -----------------------------------------------------------------------------
# Auto Scaling Policies
# -----------------------------------------------------------------------------

resource "aws_autoscaling_policy" "scale_up" {
  name                   = "${var.project_name}-${var.environment}-scale-up"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.backend.name
}

resource "aws_autoscaling_policy" "scale_down" {
  name                   = "${var.project_name}-${var.environment}-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.backend.name
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms for Auto Scaling
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 70

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.backend.name
  }

  alarm_actions = [aws_autoscaling_policy.scale_up.arn]

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "low_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-low-cpu"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 30

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.backend.name
  }

  alarm_actions = [aws_autoscaling_policy.scale_down.arn]

  tags = var.tags
}
