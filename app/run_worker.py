import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from celery.bin.celery import main as celery_main


class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"OK")


def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    print(f"Starting dummy web server on port {port}...")
    server.serve_forever()


if __name__ == "__main__":
    # Start the dummy web server in a separate thread
    thread = threading.Thread(target=run_dummy_server, daemon=True)
    thread.start()

    import subprocess
    import sys
    
    # We use subprocess to run the Celery worker directly, which avoids 
    # the TypeError: main() takes 0 positional arguments but 1 was given
    print("Executing celery worker command...")
    
    # The 'worker' command starts the worker. '-A app.worker.celery_app' points to our app.
    # '--loglevel=info' sets the log level.
    try:
        subprocess.run(["celery", "-A", "app.worker.celery_app", "worker", "--loglevel=info"], check=True)
    except Exception as e:
        print(f"Error starting celery: {e}")
        sys.exit(1)
