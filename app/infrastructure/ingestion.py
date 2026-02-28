import docker
import uuid
import logging

logger = logging.getLogger(__name__)

class DockerClientSingleton:
    _instance = None
    
    @classmethod
    def get_client(cls):
        """Lazy-loads the Docker client."""
        if cls._instance is None:
            try:
                cls._instance = docker.from_env()
            except Exception as e:
                logger.error(f"Failed to initialize Docker client: {e}")
                raise RuntimeError("Docker daemon is not running or accessible")
        return cls._instance

def ingest_repository(repo_url: str) -> dict:
    """
    Clones a validated repository into an ephemeral Docker volume.
    Returns the volume name and the local path where it can be mounted.
    """
    client = DockerClientSingleton.get_client()

    # Generate unique identifiers
    scan_uuid = str(uuid.uuid4())
    volume_name = f"scan_volume_{scan_uuid}"
    
    logger.info(f"Creating isolated volume: {volume_name}")
    # Create the volume to store the code
    volume = client.volumes.create(name=volume_name)
    
    container_name = f"clone_{scan_uuid}"
    logger.info(f"Starting ephemeral clone container {container_name} for {repo_url}")
    
    try:
        # Run the container to clone with resource limits
        container = client.containers.run(
            image="alpine/git",
            command=["clone", repo_url, "/data/repo"],
            name=container_name,
            remove=True,
            volumes={
                volume_name: {'bind': '/data', 'mode': 'rw'}
            },
            mem_limit='512m',         # Restrict Memory to 512 Megabytes
            nano_cpus=500000000,      # Restrict CPU to 0.5 Cores
            detach=False              # Block until clone concludes
        )
        
        logger.info(f"Clone successful into volume {volume_name}")
        return {
            "volume_name": volume_name,
            "container_id": volume_name,
            "local_path": "/data/repo"
        }
    except docker.errors.ContainerError as e:
        # Extract the actual standard error from the container if available
        error_msg = e.stderr.decode('utf-8').strip() if e.stderr else str(e)
        logger.error(f"Clone failed: {error_msg}")
        # Clean up volume on failure
        volume.remove()
        raise RuntimeError(f"Failed to clone repository: {error_msg}")
    except Exception as e:
        logger.error(f"Unexpected error during ingestion: {e}")
        volume.remove()
        raise

def cleanup_volume(volume_name: str):
    """
    Removes the specified Docker volume to prevent storage bloat.
    """
    try:
        client = DockerClientSingleton.get_client()
        volume = client.volumes.get(volume_name)
        volume.remove()
        logger.info(f"Successfully cleaned up volume: {volume_name}")
    except docker.errors.NotFound:
        logger.warning(f"Volume {volume_name} not found for cleanup.")
    except Exception as e:
        logger.error(f"Failed to clean up volume {volume_name}: {e}")
