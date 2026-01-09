output "api_url" {
  description = "Sentiment Analysis API URL"
  value       = aws_api_gateway_stage.final_project.invoke_url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.final_project_predict.function_name
}

output "student_id" {
  description = "Student identifier for this deployment"
  value       = var.student_id
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.final_project.repository_url
}

output "api_gateway_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.final_project.id
}

output "health_check_url" {
  description = "Health check endpoint URL"
  value       = "${aws_api_gateway_stage.final_project.invoke_url}/health"
}

output "analyze_endpoint_url" {
  description = "Sentiment analysis endpoint URL"
  value       = "${aws_api_gateway_stage.final_project.invoke_url}/analyze"
}