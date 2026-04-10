#!/usr/bin/env python3
"""
OneQueue Database Backup Script

Backs up SQLite database to timestamped backup files with optional cloud storage upload.
Supports local and VPS execution via environment variables.

Usage:
    python -m app.scripts.backup                    # Local backup
    python -m app.scripts.backup --upload-cloud      # Backup and upload to cloud
    python -m app.scripts.backup --dry-run           # Test without making changes

Environment Variables:
    BACKUP_DIR          - Local backup directory (default: ./backups)
    DATABASE_PATH       - Path to SQLite database (default: ./data/onequeue.db)
    CLOUD_PROVIDER      - Cloud provider: s3, gcs, azure, or local
    CLOUD_BUCKET        - Cloud storage bucket name
    CLOUD_PREFIX        - Prefix for backup files in cloud
    AWS_ACCESS_KEY_ID   - AWS credentials (for S3)
    AWS_SECRET_ACCESS_KEY
    AWS_REGION
    GCP_SERVICE_ACCOUNT - GCP credentials JSON (for GCS)
    AZURE_STORAGE_ACCOUNT
    AZURE_STORAGE_KEY
"""

import argparse
import os
import shutil
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import boto3
except ImportError:
    boto3 = None

try:
    from google.cloud import storage as gcs
except ImportError:
    gcs = None

try:
    from azure.storage.blob import BlobServiceClient
except ImportError:
    BlobServiceClient = None


class BackupConfig:
    def __init__(self):
        self.backup_dir = os.environ.get("BACKUP_DIR", "./backups")
        self.db_path = os.environ.get("DATABASE_PATH", "./data/onequeue.db")
        self.cloud_provider = os.environ.get("CLOUD_PROVIDER", "local").lower()
        self.cloud_bucket = os.environ.get("CLOUD_BUCKET", "")
        self.cloud_prefix = os.environ.get("CLOUD_PREFIX", "backups")
        self.aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
        self.aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        self.aws_region = os.environ.get("AWS_REGION", "us-east-1")
        self.gcp_creds = os.environ.get("GCP_SERVICE_ACCOUNT", "")
        self.azure_account = os.environ.get("AZURE_STORAGE_ACCOUNT", "")
        self.azure_key = os.environ.get("AZURE_STORAGE_KEY", "")


class BackupManager:
    def __init__(self, config: BackupConfig):
        self.config = config

    def get_timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def get_backup_filename(self) -> str:
        return f"onequeue_backup_{self.get_timestamp()}.db"

    def get_db_path(self) -> Path:
        return Path(self.config.db_path)

    def get_backup_path(self) -> Path:
        backup_dir = Path(self.config.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir / self.get_backup_filename()

    def create_local_backup(self, dry_run: bool = False) -> Optional[Path]:
        db_path = self.get_db_path()
        if not db_path.exists():
            print(f"Database not found at {db_path}")
            return None

        backup_path = self.get_backup_path()
        if dry_run:
            print(f"[DRY RUN] Would create backup: {backup_path}")
            return backup_path

        print(f"Creating backup: {backup_path}")
        shutil.copy2(db_path, backup_path)
        print(f"Backup created successfully: {backup_path} ({backup_path.stat().st_size} bytes)")
        return backup_path

    def upload_to_s3(self, local_path: Path) -> bool:
        if boto3 is None:
            print("boto3 not installed. Run: pip install boto3")
            return False

        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.config.aws_access_key,
                aws_secret_access_key=self.config.aws_secret_key,
                region_name=self.config.aws_region,
            )
            key = f"{self.config.cloud_prefix}/{local_path.name}"
            s3_client.upload_file(str(local_path), self.config.cloud_bucket, key)
            print(f"Uploaded to s3://{self.config.cloud_bucket}/{key}")
            return True
        except Exception as e:
            print(f"S3 upload failed: {e}")
            return False

    def upload_to_gcs(self, local_path: Path) -> bool:
        if gcs is None:
            print("google-cloud-storage not installed. Run: pip install google-cloud-storage")
            return False

        try:
            creds_dict = json.loads(self.config.gcp_creds) if self.config.gcp_creds else None
            client = gcs.Client.from_service_account_info(creds_dict) if creds_dict else gcs.Client()
            bucket = client.bucket(self.config.cloud_bucket)
            blob = bucket.blob(f"{self.config.cloud_prefix}/{local_path.name}")
            blob.upload_from_filename(str(local_path))
            print(f"Uploaded to gs://{self.config.cloud_bucket}/{self.config.cloud_prefix}/{local_path.name}")
            return True
        except Exception as e:
            print(f"GCS upload failed: {e}")
            return False

    def upload_to_azure(self, local_path: Path) -> bool:
        if BlobServiceClient is None:
            print("azure-storage-blob not installed. Run: pip install azure-storage-blob")
            return False

        try:
            conn_str = (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={self.config.azure_account};"
                f"AccountKey={self.config.azure_key}"
            )
            blob_client = BlobServiceClient.from_connection_string(conn_str)
            container = blob_client.get_container_client(self.config.cloud_bucket)
            blob = container.get_blob_client(f"{self.config.cloud_prefix}/{local_path.name}")
            with open(local_path, "rb") as data:
                blob.upload_blob(data, overwrite=True)
            print(f"Uploaded to azure://{self.config.cloud_bucket}/{self.config.cloud_prefix}/{local_path.name}")
            return True
        except Exception as e:
            print(f"Azure upload failed: {e}")
            return False

    def upload_to_cloud(self, local_path: Path, dry_run: bool = False) -> bool:
        if dry_run:
            print(f"[DRY RUN] Would upload to {self.config.cloud_provider}")
            return True

        if self.config.cloud_provider == "s3":
            return self.upload_to_s3(local_path)
        elif self.config.cloud_provider == "gcs":
            return self.upload_to_gcs(local_path)
        elif self.config.cloud_provider == "azure":
            return self.upload_to_azure(local_path)
        elif self.config.cloud_provider == "local":
            dest = Path(self.config.cloud_bucket) / local_path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, dest)
            print(f"Copied to local: {dest}")
            return True
        else:
            print(f"Unknown cloud provider: {self.config.cloud_provider}")
            return False


def main():
    parser = argparse.ArgumentParser(description="OneQueue Database Backup Script")
    parser.add_argument("--upload-cloud", action="store_true", help="Upload backup to cloud storage")
    parser.add_argument("--dry-run", action="store_true", help="Test without making changes")
    parser.add_argument("--keep-local", action="store_true", default=True, help="Keep local backup file")
    args = parser.parse_args()

    config = BackupConfig()
    manager = BackupManager(config)

    print(f"=== OneQueue Backup ===")
    print(f"Database: {config.db_path}")
    print(f"Backup dir: {config.backup_dir}")
    print(f"Cloud provider: {config.cloud_provider}")
    print()

    backup_path = manager.create_local_backup(dry_run=args.dry_run)
    if not backup_path:
        sys.exit(1)

    if args.upload_cloud:
        success = manager.upload_to_cloud(backup_path, dry_run=args.dry_run)
        if not success:
            sys.exit(1)
        if not args.keep_local and not args.dry_run:
            backup_path.unlink()
            print(f"Removed local backup: {backup_path}")

    print("\nBackup completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())