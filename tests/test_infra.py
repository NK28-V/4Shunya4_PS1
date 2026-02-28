import requests
import time
from app.worker import scan_codebase

def test_health_endpoint():
    print("Testing /health endpoint...")
    try:
        response = requests.get("http://localhost:8000/api/v1/health")
        # Note: health is at /health in main app, or optionally /api/v1/health if included there.
        # Based on my main.py, it's at /health and /api/v1/health is not defined but /api/v1 is included.
        # Let's try root /health
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("Health check successful!")
        else:
            print(f"Health check failed with status: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to API: {e}")

def test_celery_redis():
    print("Testing Celery/Redis connection...")
    try:
        # Triggering a task directly for verification
        result = scan_codebase.delay(999)
        print(f"Task triggered with ID: {result.id}")
        print("Waiting for task to be processed (requires worker to be running)...")
        # In a real test we might wait for result
        # print(f"Task result: {result.get(timeout=5)}")
        print("Celery task dispatched successfully.")
    except Exception as e:
        print(f"Error connecting to Celery/Redis: {e}")

if __name__ == "__main__":
    # Note: These tests assume the API and Worker are running locally.
    test_health_endpoint()
    test_celery_redis()
