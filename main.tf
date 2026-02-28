variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "us-central1"
}

variable "image_url" {
  description = "Docker Image URL in Artifact Registry"
  type        = string
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Auto-scaling Cloud Run Service for Vibe-Audit API
resource "google_cloud_run_v2_service" "hackx_api" {
  name     = "vibe-audit-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    containers {
      image = var.image_url
      
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
      
      ports {
        container_port = 8080
      }
      
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      # Real secrets should ideally use Google Secret Manager references here
    }
  }
}

# Make the service publicly accessible
resource "google_cloud_run_service_iam_member" "public_invoker" {
  location = google_cloud_run_v2_service.hackx_api.location
  project  = google_cloud_run_v2_service.hackx_api.project
  service  = google_cloud_run_v2_service.hackx_api.name

  role   = "roles/run.invoker"
  member = "allUsers"
}

output "service_url" {
  description = "The public URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.hackx_api.uri
}
