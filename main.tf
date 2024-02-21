provider "aws" {
  region = "us-east-1"  
}

# Terraform code to create CloudWatch alarm
resource "aws_cloudwatch_metric_alarm" "scale_up_alarm" {
  alarm_name          = "scale-up-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "CPUUtilization"
  namespace           = "AWS/OpenSearch"
  period              = 60
  statistic           = "Average"
  threshold           = 20.0
  alarm_description = "This metric monitors OpenSearch CPU utilization"
}

# Terraform code to create EventBridge rule directly triggering Lambda
resource "aws_cloudwatch_event_rule" "scaleup" {
  name        = "scaleup-rule"
  description = "This is an example scale-up rule"

  event_pattern = <<PATTERN
{
  "source": ["cloudwatch"],
  "account": ["143173744693"],
  "detail": {
    "scale-type": ["scale_up"]
  }
}
PATTERN
}

# Terraform code to create EventBridge target for Lambda function
resource "aws_cloudwatch_event_target" "scaleup_lambda_target" {
  rule      = aws_cloudwatch_event_rule.scaleup.name
  target_id = "scaleup-lambda-target"
  arn       = aws_lambda_function.scaleup.arn
}

# Terraform code to create Lambda function
resource "aws_lambda_function" "scaleup" {
  filename      = "scaleup.zip"
  function_name = "scaleup"
  role          = aws_iam_role.scaleup.arn
  handler       = "scaleup.lambda_handler"
  runtime       = "python3.10"

  layers = [aws_lambda_layer_version.lambda_layer.arn] # Add this line to include the Lambda layer
}


# Terraform code to create Lambda Layer
resource "aws_lambda_layer_version" "lambda_layer" {
  layer_name         = "LambdaLayer"
  source_code_hash   = filebase64("python.zip") # Updated to reference the zip file in the same directory

  compatible_runtimes = ["python3.10"]
}

# IAM Role for Lambda function
resource "aws_iam_role" "scaleup" {
  name = "scaleup-lambda-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

# Attach policies to the Lambda IAM role
resource "aws_iam_role_policy_attachment" "scaleup_lambda_permissions" {
  policy_arn = "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
  role       = aws_iam_role.scaleup.name
}

# IAM Role for OpenSearch
resource "aws_iam_role" "opensearch_role" {
  name = "opensearch-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "es.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

# Attach policies to the OpenSearch IAM role
resource "aws_iam_role_policy_attachment" "opensearch_permissions" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonESFullAccess"
  role       = aws_iam_role.opensearch_role.name
}
