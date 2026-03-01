project_id      = "nth-setup-288510"
region          = "us-central1"
service_name    = "vibe-audit-backend"
container_image = "gcr.io/nth-setup-288510/vibe-audit-backend:latest"

# MUST use the postgresql+asyncpg:// driver for the async engine
database_url    = "postgresql+asyncpg://postgres.knuiqqlxqnywngffoyal:J2QDXHiF63gPbmeL@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres"

# MUST point to a live cloud Redis for the Celery worker
redis_url       = "rediss://default:Afu7AAIncDE2NjRiZDhkZjk2YTk0ZThkYmU0NjY4MTJmNWQ5ZjdkOXAxNjQ0NDM@perfect-cobra-64443.upstash.io:6379"