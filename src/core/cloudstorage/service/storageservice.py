import os
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from azure.storage.blob import BlobServiceClient, ContentSettings

logger = logging.getLogger(__name__)


class StorageService:
    """Azure Blob Storage implementation used by the app.

    It reads configuration from environment variables:
      - AZURE_STORAGE_CONNECTION_STRING
      - AZURE_STORAGE_CONTAINER

    If Azure credentials are not configured, storage operations will be disabled
    and return None/empty strings gracefully.

    Methods:
      - upload_file(file_obj, file_name, content_type=None) -> str (blob url) or None
      - download_file(file_name, destination_path) -> str or None
    """

    def __init__(self, connection_string: str | None = None, container_name: str | None = None):
        connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = container_name or os.getenv("AZURE_STORAGE_CONTAINER")

        self.enabled = False
        self.blob_service_client = None
        self.container_client = None

        if connection_string and container_name:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                self.container_client = self.blob_service_client.get_container_client(container_name)
                # Ensure container exists (create if not). If it already exists, ignore the error.
                try:
                    self.container_client.create_container()
                except Exception:
                    # Container likely already exists or creation not permitted; continue.
                    pass
                self.enabled = True
                logger.info("Azure Blob Storage enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Blob Storage: {e}. Storage operations will be disabled.")
                self.enabled = False
        else:
            logger.info("Azure Storage credentials not configured. Storage operations will be disabled.")

    def upload_file(self, file_obj, file_name: str, content_type: str | None = None, timeout_seconds: int = 30) -> str | None:
        """Upload a file-like object to Azure Blob Storage and return the blob URL.

        file_obj must be a readable file-like object (e.g. UploadFile.file from FastAPI).

        Args:
            file_obj: File-like object to upload
            file_name: Name/path for the blob
            content_type: MIME type for the blob
            timeout_seconds: Maximum seconds to wait for upload (default: 30)

        Returns:
            str: URL of the uploaded blob, or None if storage is disabled

        Raises:
            TimeoutError: If upload takes longer than timeout_seconds
            Exception: Other Azure storage exceptions (only if enabled)
        """
        if not self.enabled:
            logger.warning(f"Storage upload requested for {file_name}, but Azure Blob Storage is not enabled. Skipping upload.")
            return None

        blob_client = self.container_client.get_blob_client(file_name)
        content_settings = ContentSettings(content_type=content_type) if content_type else None

        # Make sure we start reading from beginning
        try:
            file_obj.seek(0)
        except Exception:
            pass

        # Define upload function to run in thread
        def _upload():
            try:
                blob_client.upload_blob(file_obj, overwrite=True, content_settings=content_settings, timeout=timeout_seconds)
                return blob_client.url
            except Exception as e:
                logger.error(f"Azure upload error: {str(e)}")
                raise

        # Execute upload with hard timeout using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_upload)
            try:
                # Wait for result with timeout
                result = future.result(timeout=timeout_seconds)
                logger.info(f"Successfully uploaded {file_name} to Azure Blob Storage")
                return result
            except FuturesTimeoutError:
                logger.error(f"Upload timeout after {timeout_seconds}s for {file_name}")
                # Cancel the future (though the upload might still continue in background)
                future.cancel()
                raise TimeoutError(f"Azure blob upload timed out after {timeout_seconds} seconds")
            except Exception as e:
                logger.error(f"Upload failed for {file_name}: {str(e)}")
                raise

    def download_file(self, file_name: str, destination_path: str) -> str | None:
        """Download blob to local file path.

        Args:
            file_name: Name of the blob to download
            destination_path: Local path to save the file

        Returns:
            str: Success message, or None if storage is disabled

        Raises:
            Exceptions from Azure SDK if blob not found (only if enabled)
        """
        if not self.enabled:
            logger.warning(f"Storage download requested for {file_name}, but Azure Blob Storage is not enabled. Skipping download.")
            return None

        blob_client = self.container_client.get_blob_client(file_name)
        downloader = blob_client.download_blob()

        # Write bytes to the destination file
        with open(destination_path, "wb") as f:
            downloader.readinto(f)

        return f"Downloaded {file_name} to {destination_path}"
