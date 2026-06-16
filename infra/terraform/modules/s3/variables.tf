variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "autocode"
}

variable "kms_key_id" {
  description = "KMS key ID for SSE-KMS encryption"
  type        = string
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS on the exports bucket"
  type        = list(string)
  default     = ["*"]
}
