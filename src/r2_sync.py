import boto3
import os
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config import (
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_ENDPOINT_URL,
    ENABLE_R2_SYNC,
    DOWNLOAD_PATH
)
import src.rich_console as console


class R2Sync:
    def __init__(self):
        if not ENABLE_R2_SYNC:
            return
            
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            endpoint_url=R2_ENDPOINT_URL,
            region_name='auto'
        )
        self.bucket_name = R2_BUCKET_NAME
        
    def upload_file(self, local_file_path: str, s3_key: str) -> bool:
        """Upload a single file to R2"""
        try:
            self.s3_client.upload_file(local_file_path, self.bucket_name, s3_key)
            console.info(f"Uploaded: {s3_key}")
            return True
        except Exception as e:
            console.error(f"Failed to upload {s3_key}: {e}")
            return False
    
    def calculate_file_md5(self, file_path: str) -> str:
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_remote_file_info(self, s3_key: str) -> dict:
        """Get remote file information (ETag, LastModified, Size)"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return {
                'etag': response['ETag'].strip('"'),
                'last_modified': response['LastModified'],
                'size': response['ContentLength']
            }
        except Exception:
            return None
    
    def should_upload_file(self, local_file_path: str, s3_key: str) -> bool:
        """Check if file should be uploaded (new or modified)"""
        local_stat = os.stat(local_file_path)
        local_size = local_stat.st_size
        local_md5 = self.calculate_file_md5(local_file_path)
        
        remote_info = self.get_remote_file_info(s3_key)
        
        if remote_info is None:
            return True
        
        if local_size != remote_info['size']:
            return True
        
        if local_md5 != remote_info['etag']:
            return True
        
        return False
    
    def get_all_files(self, directory: str) -> list:
        """Get all files in directory"""
        files = []
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, directory)
                files.append((file_path, relative_path.replace(os.path.sep, '/')))
        return files
    
    def check_file_upload_needed(self, file_info: tuple, force_upload: bool) -> tuple:
        """Check if a single file needs to be uploaded (thread-safe)"""
        local_path, s3_key = file_info
        try:
            if force_upload or self.should_upload_file(local_path, s3_key):
                return (local_path, s3_key, True)
            else:
                return (local_path, s3_key, False)
        except Exception as e:
            console.error(f"Error checking file {s3_key}: {e}")
            return (local_path, s3_key, True)
    
    def get_files_to_upload(self, all_files: list, force_upload: bool = False, max_workers: int = 20) -> tuple:
        """Parallel check which files need to be uploaded"""
        files_to_upload = []
        skipped_files = []
        
        console.info(f"Checking {len(all_files)} files in parallel (max_workers={max_workers})...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.check_file_upload_needed, file_info, force_upload): file_info
                for file_info in all_files
            }
            
            for future in as_completed(future_to_file):
                try:
                    local_path, s3_key, needs_upload = future.result()
                    if needs_upload:
                        files_to_upload.append((local_path, s3_key))
                        console.info(f"Added to upload list: {s3_key}")
                    else:
                        skipped_files.append((local_path, s3_key))
                        console.info(f"Skipped (identical): {s3_key}")
                except Exception as e:
                    file_info = future_to_file[future]
                    local_path, s3_key = file_info
                    console.error(f"Exception checking {s3_key}: {e}")
                    files_to_upload.append((local_path, s3_key))
        
        return files_to_upload, len(skipped_files)

    def sync_directory(self, local_directory: str = DOWNLOAD_PATH, max_workers: int = 20, force_upload: bool = False) -> bool:
        """Sync entire directory to R2"""
        if not ENABLE_R2_SYNC:
            console.info("R2 sync is disabled in configuration.")
            return True
            
        console.info(f"Starting R2 sync for directory: {local_directory}")
        
        if not os.path.exists(local_directory):
            console.error(f"Directory {local_directory} does not exist.")
            return False
        
        all_files = self.get_all_files(local_directory)
        
        if not all_files:
            console.info("No files found in directory.")
            return True
        
        console.info(f"Found {len(all_files)} files.")
        
        files_to_upload, skipped_count = self.get_files_to_upload(all_files, force_upload, max_workers)
        
        if not files_to_upload:
            console.info(f"No files need to be uploaded. {skipped_count} files are already up to date.")
            return True
        
        console.info(f"Uploading {len(files_to_upload)} files, skipping {skipped_count} identical files.")
        
        success_count = 0
        failed_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.upload_file, local_path, s3_key): (local_path, s3_key)
                for local_path, s3_key in files_to_upload
            }
            
            for future in as_completed(future_to_file):
                local_path, s3_key = future_to_file[future]
                try:
                    if future.result():
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    console.error(f"Exception occurred while uploading {s3_key}: {e}")
                    failed_count += 1
        
        console.info(f"R2 sync completed: {success_count} uploaded, {failed_count} failed, {skipped_count} skipped")
        return failed_count == 0
    
    def delete_remote_file(self, s3_key: str) -> bool:
        """Delete file from R2"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            console.info(f"Deleted from R2: {s3_key}")
            return True
        except Exception as e:
            console.error(f"Failed to delete {s3_key} from R2: {e}")
            return False
    
    def list_remote_files(self, prefix: str = '') -> list:
        """List files in R2"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except Exception as e:
            console.error(f"Failed to list remote files: {e}")
            return []


def sync_to_r2(local_directory: str = DOWNLOAD_PATH, force_upload: bool = False) -> bool:
    """Convenient function to sync directory to R2"""
    if not ENABLE_R2_SYNC:
        return True
        
    r2_sync = R2Sync()
    return r2_sync.sync_directory(local_directory, force_upload=force_upload) 