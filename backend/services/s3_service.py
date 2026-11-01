"""
services/s3_service.py - Amazon S3 integration for the College Management System.

All file uploads are stored in S3; only the S3 object key is persisted to the
MySQL database. Presigned URLs are generated on demand for secure, time-limited
access.
"""

import logging
import mimetypes
import os
import uuid
from typing import BinaryIO, Optional
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class S3Service:
    """
    Service layer for all Amazon S3 file operations.

    Instantiate once and reuse; the boto3 client is created lazily so that
    unit tests can patch ``boto3.client`` without importing Flask.
    """

    _client = None  # Shared boto3 client (thread-safe for read operations)

    # ---------------------------------------------------------------------- #
    # Boto3 client
    # ---------------------------------------------------------------------- #

    @property
    def client(self):
        """Return a cached (or freshly created) boto3 S3 client."""
        if self._client is None:
            region = current_app.config.get("AWS_REGION", "ap-south-1")
            kwargs = {"region_name": region}
            # If explicit keys are configured (non-IAM-role environments)
            access_key = current_app.config.get("AWS_ACCESS_KEY_ID")
            secret_key = current_app.config.get("AWS_SECRET_ACCESS_KEY")
            if access_key and secret_key:
                kwargs["aws_access_key_id"] = access_key
                kwargs["aws_secret_access_key"] = secret_key
            self._client = boto3.client("s3", **kwargs)
        return self._client

    @property
    def bucket(self) -> str:
        return current_app.config["S3_BUCKET_NAME"]

    # ---------------------------------------------------------------------- #
    # Core upload / delete
    # ---------------------------------------------------------------------- #

    def upload_file(
        self,
        file_object: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        extra_metadata: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Upload a file-like object to S3.

        Args:
            file_object: An open binary file or BytesIO object.
            key: The S3 object key (path within the bucket).
            content_type: MIME type. Auto-detected from *key* if not supplied.
            extra_metadata: Optional dict of S3 object metadata.

        Returns:
            The S3 key string on success, or None on failure.
        """
        if content_type is None:
            content_type, _ = mimetypes.guess_type(key)
            content_type = content_type or "application/octet-stream"

        extra_args: dict = {
            "ContentType": content_type,
            "ServerSideEncryption": "AES256",
        }
        if extra_metadata:
            extra_args["Metadata"] = extra_metadata

        try:
            self.client.upload_fileobj(file_object, self.bucket, key, ExtraArgs=extra_args)
            logger.info("Uploaded file to S3: s3://%s/%s", self.bucket, key)
            return key
        except (BotoCoreError, ClientError) as exc:
            logger.exception("S3 upload failed for key '%s': %s", key, exc)
            return None

    def delete_file(self, key: str) -> bool:
        """
        Delete an object from S3.

        Args:
            key: The S3 object key to delete.

        Returns:
            True on success, False on failure.
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("Deleted S3 object: s3://%s/%s", self.bucket, key)
            return True
        except (BotoCoreError, ClientError) as exc:
            logger.exception("S3 delete failed for key '%s': %s", key, exc)
            return False

    # ---------------------------------------------------------------------- #
    # URL helpers
    # ---------------------------------------------------------------------- #

    def generate_presigned_url(self, key: str, expiry: int = 3600) -> Optional[str]:
        """
        Generate a pre-signed URL that grants temporary GET access to an object.

        Args:
            key: The S3 object key.
            expiry: URL lifetime in seconds (default 1 hour).

        Returns:
            A pre-signed URL string, or None on failure.
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiry,
            )
            return url
        except (BotoCoreError, ClientError) as exc:
            logger.exception("Could not generate presigned URL for key '%s': %s", key, exc)
            return None

    def get_file_url(self, key: str) -> str:
        """
        Return the public HTTPS URL for an object (assumes bucket has public read
        or a CDN is configured).

        For private buckets, prefer ``generate_presigned_url`` instead.

        Args:
            key: The S3 object key.

        Returns:
            A fully-qualified HTTPS URL.
        """
        region = current_app.config.get("AWS_REGION", "ap-south-1")
        return f"https://{self.bucket}.s3.{region}.amazonaws.com/{key}"

    # ---------------------------------------------------------------------- #
    # Domain-specific upload methods
    # ---------------------------------------------------------------------- #

    def upload_student_photo(self, file_object: BinaryIO, student_id: int) -> Optional[str]:
        """
        Upload a student's profile photograph.

        Key format: ``students/photos/<student_id>/<uuid>.ext``

        Args:
            file_object: Open image file (JPEG/PNG).
            student_id: The student's primary key.

        Returns:
            S3 key on success, None on failure.
        """
        ext = self._get_extension(file_object)
        key = f"students/photos/{student_id}/{uuid.uuid4().hex}{ext}"
        return self.upload_file(file_object, key, content_type=f"image/{ext.lstrip('.')}")

    def upload_faculty_photo(self, file_object: BinaryIO, faculty_id: int) -> Optional[str]:
        """
        Upload a faculty member's profile photograph.

        Key format: ``faculty/photos/<faculty_id>/<uuid>.ext``
        """
        ext = self._get_extension(file_object)
        key = f"faculty/photos/{faculty_id}/{uuid.uuid4().hex}{ext}"
        return self.upload_file(file_object, key, content_type=f"image/{ext.lstrip('.')}")

    def upload_assignment(
        self,
        file_object: BinaryIO,
        assignment_id: int,
        filename: str,
    ) -> Optional[str]:
        """
        Upload an assignment document (question paper or submission).

        Key format: ``assignments/<assignment_id>/<safe_filename>``
        """
        safe = secure_filename(filename)
        key = f"assignments/{assignment_id}/{uuid.uuid4().hex}_{safe}"
        return self.upload_file(file_object, key)

    def upload_assignment_submission(
        self,
        file_object: BinaryIO,
        assignment_id: int,
        student_id: int,
        filename: str,
    ) -> Optional[str]:
        """
        Upload a student's assignment submission.

        Key format: ``assignments/<assignment_id>/submissions/<student_id>/<safe_filename>``
        """
        safe = secure_filename(filename)
        key = f"assignments/{assignment_id}/submissions/{student_id}/{uuid.uuid4().hex}_{safe}"
        return self.upload_file(file_object, key)

    def upload_study_material(
        self,
        file_object: BinaryIO,
        material_id: int,
        filename: str,
    ) -> Optional[str]:
        """
        Upload a study material resource (PDF, slides, etc.).

        Key format: ``study_materials/<material_id>/<safe_filename>``
        """
        safe = secure_filename(filename)
        key = f"study_materials/{material_id}/{uuid.uuid4().hex}_{safe}"
        return self.upload_file(file_object, key)

    def upload_student_document(
        self,
        file_object: BinaryIO,
        student_id: int,
        doc_type: str,
        filename: str,
    ) -> Optional[str]:
        """
        Upload a student's official document (ID proof, certificates, etc.).

        Args:
            file_object: Open file object.
            student_id: The student's primary key.
            doc_type: Logical document category, e.g. ``'id_proof'``, ``'certificate'``.
            filename: Original filename (will be sanitised).

        Key format: ``students/documents/<student_id>/<doc_type>/<uuid>_<safe_filename>``
        """
        safe_doc_type = secure_filename(doc_type)
        safe_filename_str = secure_filename(filename)
        key = f"students/documents/{student_id}/{safe_doc_type}/{uuid.uuid4().hex}_{safe_filename_str}"
        return self.upload_file(file_object, key)

    def upload_exam_question_paper(
        self,
        file_object: BinaryIO,
        exam_id: int,
        filename: str,
    ) -> Optional[str]:
        """
        Upload an exam question paper PDF.

        Key format: ``exams/<exam_id>/question_papers/<uuid>_<safe_filename>``
        """
        safe = secure_filename(filename)
        key = f"exams/{exam_id}/question_papers/{uuid.uuid4().hex}_{safe}"
        return self.upload_file(file_object, key, content_type="application/pdf")

    # ---------------------------------------------------------------------- #
    # Validation
    # ---------------------------------------------------------------------- #

    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
        """
        Check that *filename* has an extension present in *allowed_extensions*.

        Comparison is case-insensitive. The dot is not required in the set.

        Args:
            filename: The original filename including extension.
            allowed_extensions: A set of extension strings, e.g. ``{'pdf', 'jpg'}``.

        Returns:
            True if the extension is allowed, False otherwise.

        Example::

            S3Service.validate_file_extension('report.PDF', {'pdf', 'docx'})
            # True
        """
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[-1].lower()
        return ext in {e.lower().lstrip(".") for e in allowed_extensions}

    # ---------------------------------------------------------------------- #
    # Private helpers
    # ---------------------------------------------------------------------- #

    @staticmethod
    def _get_extension(file_object: BinaryIO) -> str:
        """
        Attempt to extract the file extension from the file object's ``filename``
        attribute (as set by Werkzeug's FileStorage).
        """
        filename = getattr(file_object, "filename", "") or ""
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ".bin"


# --------------------------------------------------------------------------- #
# Module-level singleton – import and use directly
# --------------------------------------------------------------------------- #

s3_service = S3Service()
