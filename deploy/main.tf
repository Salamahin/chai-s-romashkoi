terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }

  # Remote state backend provisioned by deploy/bootstrap/.
  # The backend block does not support variable interpolation, so names are hardcoded.
  backend "s3" {
    bucket         = "chai-s-romashkoi-tf-state"
    key            = "prod/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "chai-s-romashkoi-tf-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

module "lambda" {
  source              = "./modules/lambda"
  project_name        = var.project_name
  layer_zip_path      = var.layer_zip_path
  auth_zip_path       = var.auth_zip_path
  app_zip_path        = var.app_zip_path
  profile_zip_path    = var.profile_zip_path
  relations_zip_path  = var.relations_zip_path
  log_zip_path        = var.log_zip_path
  google_client_id    = var.google_client_id
  session_secret      = var.session_secret
}

module "frontend" {
  source               = "./modules/frontend"
  project_name         = var.project_name
  dist_path            = "${path.module}/../frontend/dist"
  auth_function_url    = module.lambda.auth_function_url
  app_function_url     = module.lambda.app_function_url
  profile_function_url = module.lambda.profile_function_url
  relations_api_url    = module.lambda.relations_function_url
  log_api_url          = module.lambda.log_function_url
}
