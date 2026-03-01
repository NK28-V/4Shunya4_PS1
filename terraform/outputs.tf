output "service_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.fastapi_backend.uri
}

output "service_name" {
  description = "The name of the deployed service"
  value       = google_cloud_run_v2_service.fastapi_backend.name
}

output "location" {
  description = "The location of the deployed service"
  value       = google_cloud_run_v2_service.fastapi_backend.location
}
