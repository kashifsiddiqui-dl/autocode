variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "autocode"
}

variable "instance_id" {
  description = "EC2 instance ID for metric dimensions"
  type        = string
}

variable "alb_arn" {
  description = "ALB ARN for metric dimensions"
  type        = string
}

variable "alarm_email" {
  description = "Email address for alarm notifications"
  type        = string
  default     = null
}

variable "kms_key_arn" {
  description = "KMS key ARN for encrypting log groups and SNS topic"
  type        = string
  default     = null
}
