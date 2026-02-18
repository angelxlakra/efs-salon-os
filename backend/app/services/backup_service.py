from app.utils import IST
from pathlib import Path
from app.config import settings
from datetime import timedelta
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class BackupService:
    """Handles backup uploads and metrics push to S3-compatible cloudstorage."""

    def __init__(self):
        self._s3_client = None
    
    @property
    def cloud_enabled(self) -> bool:
        """Check if S3 credentials are configured."""
        return bool(
            settings.backup_s3_endpoint
            and settings.backup_s3_bucket
            and settings.backup_s3_access_key
            and settings.backup_s3_secret_key
        )


    def _get_s3_client(self):
        """Get or create S3 client (lazy initialization)."""
        if self._s3_client is None:
            import boto3

            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.backup_s3_endpoint,
                aws_access_key_id=settings.backup_s3_access_key,
                aws_secret_access_key=settings.backup_s3_secret_key,
                region_name=settings.backup_s3_region,
            )

        return self._s3_client

    def upload_to_cloud(self, local_path: Path) -> bool:
        """
            Upload files to S3 compatible storage
            Args:
                local_path: Path to the local file to upload
            
            Returns:
                True if upload succeeded, else False
                Never raises - errors are logged
        """
        if not self.cloud_enabled:
            logger.debug("Cloud upload skipped - S3 not configured")
            return False
        
        try:
            s3 = self._get_s3_client()

            # Build the S3 key (path inside the bucket)
            s3_key = f"{settings.branch_id}/backups/{local_path.name}"

            logger.info(f"Uploading {local_path.name} to s3://{settings.backup_s3_bucket}/{s3_key}...")

            s3.upload_file(
                Filename=str(local_path),
                Bucket=settings.backup_s3_bucket,
                Key=s3_key
            )
        
            logger.info(f"Upload complete: {s3_key}")

            return True
        
        except Exception as e:
            logger.error(f"Cloud upload failed: {e}")
            return False


    def push_daily_metrics(self, summary) -> bool:
        """Serialize a DaySummary and upload as JSON to cloud storage.
            Args:
                summary: DaySummary model instance

            Returns:
                True if upload succeeded, False otherwise.
        """

        if not self.cloud_enabled:
            return False

        try:
            s3 = self._get_s3_client()

            #Build the metrics JSON
            metrics = {
              "schema_version": 1,
              "branch_id": settings.branch_id,
              "branch_name": settings.salon_name,
              "summary_date": str(summary.summary_date),
              "generated_at": datetime.now(IST).isoformat(),
              "is_final": summary.is_final,
              "currency": "INR",
              # Revenue
              "total_bills": summary.total_bills,
              "refund_count": summary.refund_count,
              "gross_revenue": summary.gross_revenue,
              "discount_amount": summary.discount_amount,
              "refund_amount": summary.refund_amount,
              "net_revenue": summary.net_revenue,
              # Tax
              "cgst_collected": summary.cgst_collected,
              "sgst_collected": summary.sgst_collected,
              "total_tax": summary.total_tax,
              # Payments
              "cash_collected": summary.cash_collected,
              "digital_collected": summary.digital_collected,
              # COGS & Profit
              "actual_service_cogs": summary.actual_service_cogs,
              "actual_product_cogs": summary.actual_product_cogs,
              "total_cogs": summary.total_cogs,
              "total_expenses": summary.total_expenses,
              "gross_profit": summary.gross_profit,
              "net_profit": summary.net_profit,
              "total_tips": summary.total_tips,
            }

            # Upload as JSON
            s3_key = f"{settings.branch_id}/metrics/{summary.summary_date}.json"
            json_bytes = json.dumps(metrics, indent=2).encode("utf-8")

            s3.put_object(
                Bucket=settings.backup_s3_bucket,
                Key=s3_key,
                Body=json_bytes,
                ContentType="application/json",
            )

            logger.info(f"Metrics pushed: {s3_key}")
            return True

        except Exception as e:
            logger.error(f"Metrics push failed: {e}")
            return False

    def cleanup_cloud(self, retention_days: int) -> None:
        """Delete cloud backup objects older than retention_days."""
        if not self.cloud_enabled:
            return

        try:
            s3 = self._get_s3_client()
            prefix = f"{settings.branch_id}/backups/"
            cutoff = datetime.now(IST) - timedelta(days=retention_days)
            deleted = 0

            # Use paginator to handle >1000 objects
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(
                Bucket=settings.backup_s3_bucket, Prefix=prefix
            ):
                for obj in page.get("Contents", []):
                    if obj["LastModified"] < cutoff:
                        s3.delete_object(
                            Bucket=settings.backup_s3_bucket,
                            Key=obj["Key"],
                        )
                        deleted += 1
                        logger.info(f"Deleted old cloud backup: {obj['Key']}")

            if deleted:
                logger.info(f"Cloud cleanup: removed {deleted} old backup(s)")

        except Exception as e:
            logger.error(f"Cloud cleanup failed: {e}")
