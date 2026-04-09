terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "lambda" {
  source       = "./modules/lambda"
  project_name = var.project_name
  zip_path     = "${path.module}/../backend/dist/function.zip"
}

module "frontend" {
  source            = "./modules/frontend"
  project_name      = var.project_name
  dist_path         = "${path.module}/../frontend/dist"
  lambda_invoke_arn = module.lambda.function_arn
}
