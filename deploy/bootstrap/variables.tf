variable "aws_region" {
  description = "AWS region where the state bucket and lock table are created"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name prefix used for all resource names"
  type        = string
  default     = "chai-s-romashkoi"
}
