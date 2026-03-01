terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable the Cloud Run API
resource "google_project_service" "cloud_run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

# The Cloud Run Service
resource "google_cloud_run_v2_service" "fastapi_backend" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.container_image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      # Example environment variables
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      
      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }
    }
  }

  depends_on = [google_project_service.cloud_run]
}

# Allow unauthenticated access (public API)
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.fastapi_backend.location
  project  = google_cloud_run_v2_service.fastapi_backend.project
  service  = google_cloud_run_v2_service.fastapi_backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
