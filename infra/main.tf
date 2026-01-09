# Data sources
data "aws_caller_identity" "current" {}

data "aws_ecr_authorization_token" "token" {}

# Data source for lambda source hash
data "archive_file" "lambda_source" {
  type        = "zip"
  source_dir  = "../src"
  output_path = "/tmp/lambda-${var.student_id}.zip"
}

# S3 bucket para logs da aplicação
resource "aws_s3_bucket" "logs" {
  bucket = "final-project-logs-${var.student_id}-${var.environment}"

  tags = {
    Name        = "final-project-logs-${var.student_id}-${var.environment}"
    Environment = var.environment
    StudentId   = var.student_id
  }
}

# Create ECR repository for Lambda container image
resource "aws_ecr_repository" "final_project" {
  name                 = "final_project_${var.student_id}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  lifecycle {
    prevent_destroy = false
  }
}

# ECR repository policy
resource "aws_ecr_repository_policy" "final_project_policy" {
  repository = aws_ecr_repository.final_project.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaECRImageRetrievalPolicy"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
      }
    ]
  })
}

# Build and push Docker image
resource "docker_image" "final_project" {
  name = "${aws_ecr_repository.final_project.repository_url}:${substr(data.archive_file.lambda_source.output_sha, 0, 8)}"

  build {
    context    = "../src"
    dockerfile = "Dockerfile"
    platform   = "linux/amd64"
  }

  depends_on = [aws_ecr_repository.final_project]
}

resource "docker_registry_image" "final_project" {
  name = docker_image.final_project.name

  depends_on = [docker_image.final_project]
}

# Import existing IAM role (mantido, embora não esteja sendo usado diretamente)
data "aws_iam_role" "lambda_execution_role" {
  name = split("/", var.lambda_execution_role_arn)[1]
}

# Lambda function
resource "aws_lambda_function" "final_project_predict" {
  function_name = "final_project_predict_${var.student_id}"
  role          = var.lambda_execution_role_arn

  package_type = "Image"
  image_uri    = docker_image.final_project.name

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  environment {
    variables = {
      LOG_LEVEL       = "INFO"
      STUDENT_ID      = var.student_id
      LOG_BUCKET_NAME = aws_s3_bucket.logs.bucket
    }
  }

  depends_on = [
    docker_registry_image.final_project,
    aws_ecr_repository.final_project
  ]

  description = "Titanic prediction model for ${var.student_id}"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "final_project" {
  name              = "/aws/lambda/${aws_lambda_function.final_project_predict.function_name}"
  retention_in_days = 7

  depends_on = [aws_lambda_function.final_project_predict]
}

# API Gateway
resource "aws_api_gateway_rest_api" "final_project" {
  name        = "final_project-api-iac-${var.student_id}"
  description = "API for ML Prediction - ${var.student_id}"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# API Gateway CORS configuration
resource "aws_api_gateway_method" "options" {
  rest_api_id   = aws_api_gateway_rest_api.final_project.id
  resource_id   = aws_api_gateway_rest_api.final_project.root_resource_id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "options" {
  rest_api_id = aws_api_gateway_rest_api.final_project.id
  resource_id = aws_api_gateway_rest_api.final_project.root_resource_id
  http_method = aws_api_gateway_method.options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration" "options" {
  rest_api_id = aws_api_gateway_rest_api.final_project.id
  resource_id = aws_api_gateway_rest_api.final_project.root_resource_id
  http_method = aws_api_gateway_method.options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_integration_response" "options" {
  rest_api_id = aws_api_gateway_rest_api.final_project.id
  resource_id = aws_api_gateway_rest_api.final_project.root_resource_id
  http_method = aws_api_gateway_method.options.http_method
  status_code = aws_api_gateway_method_response.options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# API Gateway resources and methods for /analyze endpoint
resource "aws_api_gateway_resource" "analyze" {
  rest_api_id = aws_api_gateway_rest_api.final_project.id
  parent_id   = aws_api_gateway_rest_api.final_project.root_resource_id
  path_part   = "analyze"
}

resource "aws_api_gateway_method" "analyze_post" {
  rest_api_id   = aws_api_gateway_rest_api.final_project.id
  resource_id   = aws_api_gateway_resource.analyze.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "analyze_lambda" {
  rest_api_id = aws_api_gateway_rest_api.final_project.id
  resource_id = aws_api_gateway_resource.analyze.id
  http_method = aws_api_gateway_method.analyze_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.final_project_predict.invoke_arn
}

# API Gateway resources and methods for /health endpoint
resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.final_project.id
  parent_id   = aws_api_gateway_rest_api.final_project.root_resource_id
  path_part   = "health"
}

resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.final_project.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "health_mock" {
  rest_api_id = aws_api_gateway_rest_api.final_project.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "health_get" {
  rest_api_id = aws_api_gateway_rest_api.final_project.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_integration_response" "health_mock" {
  rest_api_id = aws_api_gateway_rest_api.final_project.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  status_code = aws_api_gateway_method_response.health_get.status_code

  response_templates = {
    "application/json" = jsonencode({
      status     = "healthy"
      service    = "final_project"
      student_id = var.student_id
    })
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.final_project_predict.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.final_project.execution_arn}/*/*"
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "final_project" {
  depends_on = [
    aws_api_gateway_method.analyze_post,
    aws_api_gateway_integration.analyze_lambda,
    aws_api_gateway_method.health_get,
    aws_api_gateway_integration.health_mock,
    aws_api_gateway_method.options,
    aws_api_gateway_integration.options,
  ]

  rest_api_id = aws_api_gateway_rest_api.final_project.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.analyze.id,
      aws_api_gateway_method.analyze_post.id,
      aws_api_gateway_integration.analyze_lambda.id,
      aws_api_gateway_resource.health.id,
      aws_api_gateway_method.health_get.id,
      aws_api_gateway_integration.health_mock.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "final_project" {
  deployment_id = aws_api_gateway_deployment.final_project.id
  rest_api_id   = aws_api_gateway_rest_api.final_project.id
  stage_name    = var.environment
}
