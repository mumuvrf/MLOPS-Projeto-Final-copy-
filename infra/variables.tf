variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "aws_profile" {
  description = "AWS profile to use"
  type        = string
  default     = "mlops"
}

variable "student_id" {
  description = "Unique student identifier"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.student_id))
    error_message = "Student ID must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "lambda_execution_role_arn" {
  description = "ARN of existing Lambda execution role"
  type        = string
  validation {
    condition     = can(regex("^arn:aws:iam::", var.lambda_execution_role_arn))
    error_message = "Lambda execution role ARN must be a valid IAM role ARN."
  }
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}