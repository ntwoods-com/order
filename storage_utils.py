"""
Supabase Storage Utility Module

Provides functions to upload, download, and manage files in Supabase Storage.
Automatically detects whether to use local storage or Supabase based on configuration.
"""
import os
import logging
from typing import Optional, Tuple
from io import BytesIO

logger = logging.getLogger(__name__)


def _is_cloud_storage() -> bool:
    """Check if Supabase cloud storage is configured."""
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))


def _get_supabase_client():
    """Get Supabase client instance."""
    try:
        from supabase import create_client, Client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        return create_client(url, key)
    except ImportError:
        raise ImportError("supabase package not installed. Run: pip install supabase")


def _get_bucket_name() -> str:
    """Get Supabase storage bucket name from environment."""
    return os.getenv("SUPABASE_STORAGE_BUCKET", "sale-orders")


def upload_file(file_data: bytes, remote_path: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload a file to Supabase Storage or local filesystem.
    
    Args:
        file_data: File content as bytes
        remote_path: Path within the storage bucket (e.g., "uploads/file.xlsx")
        content_type: MIME type of the file
    
    Returns:
        str: Full path or URL to the uploaded file
    
    Raises:
        Exception: If upload fails
    """
    if _is_cloud_storage():
        try:
            client = _get_supabase_client()
            bucket = _get_bucket_name()
            
            logger.info(f"Uploading to Supabase bucket '{bucket}' at path '{remote_path}'")
            
            # Upload to Supabase Storage
            response = client.storage.from_(bucket).upload(
                path=remote_path,
                file=file_data,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            
            logger.info(f"Successfully uploaded file to Supabase Storage: {bucket}/{remote_path}")
            return remote_path
        except Exception as e:
            logger.error(f"Failed to upload to Supabase bucket '{bucket}' at '{remote_path}': {e}")
            raise Exception(f"Supabase upload failed: {str(e)}")
    else:
        # Fallback to local filesystem
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, remote_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"Saved file locally: {full_path}")
        return full_path


def download_file(remote_path: str) -> Tuple[bytes, str]:
    """
    Download a file from Supabase Storage or local filesystem.
    
    Args:
        remote_path: Path within the storage bucket or local path
    
    Returns:
        Tuple[bytes, str]: (file_data, filename)
    
    Raises:
        FileNotFoundError: If file doesn't exist
        Exception: If download fails
    """
    if _is_cloud_storage():
        try:
            client = _get_supabase_client()
            bucket = _get_bucket_name()
            
            logger.info(f"Downloading from Supabase bucket '{bucket}' at path '{remote_path}'")
            
            # Download from Supabase Storage
            file_data = client.storage.from_(bucket).download(remote_path)
            filename = os.path.basename(remote_path)
            
            logger.info(f"Successfully downloaded file from Supabase Storage: {bucket}/{remote_path} ({len(file_data)} bytes)")
            return (file_data, filename)
        except Exception as e:
            logger.error(f"Failed to download from Supabase bucket '{bucket}' at '{remote_path}': {e}")
            raise FileNotFoundError(f"File not found in Supabase bucket '{bucket}': {remote_path} - {str(e)}")
    else:
        # Fallback to local filesystem
        if not os.path.exists(remote_path):
            raise FileNotFoundError(f"File not found: {remote_path}")
        
        with open(remote_path, 'rb') as f:
            file_data = f.read()
        
        filename = os.path.basename(remote_path)
        logger.info(f"Read file locally: {remote_path}")
        return (file_data, filename)


def delete_file(remote_path: str) -> bool:
    """
    Delete a file from Supabase Storage or local filesystem.
    
    Args:
        remote_path: Path within the storage bucket or local path
    
    Returns:
        bool: True if successful, False otherwise
    """
    if _is_cloud_storage():
        try:
            client = _get_supabase_client()
            bucket = _get_bucket_name()
            
            logger.info(f"Deleting from Supabase bucket '{bucket}' at path '{remote_path}'")
            
            # Delete from Supabase Storage
            client.storage.from_(bucket).remove([remote_path])
            logger.info(f"Successfully deleted file from Supabase Storage: {bucket}/{remote_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete from Supabase bucket '{bucket}' at '{remote_path}': {e}")
            return False
    else:
        # Fallback to local filesystem
        try:
            if os.path.exists(remote_path):
                os.remove(remote_path)
                logger.info(f"Deleted local file: {remote_path}")
                return True
        except Exception as e:
            logger.warning(f"Failed to delete local file: {e}")
        return False


def get_public_url(remote_path: str) -> Optional[str]:
    """
    Get public URL for a file in Supabase Storage.
    
    Args:
        remote_path: Path within the storage bucket
    
    Returns:
        Optional[str]: Public URL or None if not using cloud storage
    """
    if _is_cloud_storage():
        try:
            client = _get_supabase_client()
            bucket = _get_bucket_name()
            
            # Get public URL
            url = client.storage.from_(bucket).get_public_url(remote_path)
            return url
        except Exception as e:
            logger.error(f"Failed to get public URL: {e}")
            return None
    return None


def file_exists(remote_path: str) -> bool:
    """
    Check if a file exists in Supabase Storage or local filesystem.
    
    Args:
        remote_path: Path within the storage bucket or local path
    
    Returns:
        bool: True if file exists, False otherwise
    """
    if _is_cloud_storage():
        try:
            client = _get_supabase_client()
            bucket = _get_bucket_name()
            
            # List files and check if path exists
            files = client.storage.from_(bucket).list(os.path.dirname(remote_path) or ".")
            filename = os.path.basename(remote_path)
            return any(f.get("name") == filename for f in files)
        except Exception as e:
            logger.warning(f"Error checking file existence in Supabase: {e}")
            return False
    else:
        return os.path.exists(remote_path)
