import functools
import io
import json
import mimetypes
from datetime import UTC, datetime
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.types import FileMetadata
from app.types.formatting import humanize_bytes


def _guess_content_type(key: str) -> str:
    mime, _ = mimetypes.guess_type(key)
    return mime or "application/octet-stream"


def _split_key(key: str) -> tuple[str, str]:
    """Return (folder, filename) from an object key."""
    parts = key.rsplit("/", 1)
    if len(parts) == 2:
        return parts[0] + "/", parts[1]
    return "", parts[0]


def _public_url(key: str) -> str | None:
    """Build a public URL for an object key, percent-encoding the path."""
    if not settings.b2_public_url_base:
        return None
    return f"{settings.b2_public_url_base}/{quote(key, safe='/')}"


@functools.lru_cache(maxsize=1)
def get_s3_client():
    # Single S3 client for the whole app. Every B2 byte — source audio,
    # per-track feature JSON, and the vector index synced under index/ —
    # flows through this client, so the custom user agent always holds.
    # Region is read from settings (never hardcoded).
    return boto3.client(
        "s3",
        endpoint_url=settings.b2_endpoint,
        region_name=settings.b2_region or None,
        aws_access_key_id=settings.b2_application_key_id,
        aws_secret_access_key=settings.b2_application_key,
        config=Config(
            signature_version="s3v4",
            user_agent_extra="b2ai-music-tagging-search",
        ),
    )


def check_connectivity() -> bool:
    try:
        client = get_s3_client()
        client.head_bucket(Bucket=settings.b2_bucket_name)
        return True
    except Exception:
        return False


def upload_file(
    file_data: bytes, key: str, content_type: str
) -> FileMetadata:
    """Upload file to B2. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(file_data),
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 upload failed for '{key}': {e}") from e
    folder, filename = _split_key(key)
    size = len(file_data)
    return FileMetadata(
        key=key,
        filename=filename,
        folder=folder,
        size_bytes=size,
        size_human=humanize_bytes(size),
        content_type=content_type,
        uploaded_at=datetime.now(UTC),
        url=_public_url(key),
    )


def list_files(prefix: str = "", max_keys: int = 1000) -> list[FileMetadata]:
    """List files from B2. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        response = client.list_objects_v2(
            Bucket=settings.b2_bucket_name,
            Prefix=prefix,
            MaxKeys=max_keys,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 list failed: {e}") from e
    files: list[FileMetadata] = []
    for obj in response.get("Contents", []):
        folder, filename = _split_key(obj["Key"])
        files.append(
            FileMetadata(
                key=obj["Key"],
                filename=filename,
                folder=folder,
                size_bytes=obj["Size"],
                size_human=humanize_bytes(obj["Size"]),
                content_type=_guess_content_type(obj["Key"]),
                uploaded_at=obj["LastModified"],
                url=_public_url(obj["Key"]),
            )
        )
    files.sort(key=lambda f: f.uploaded_at, reverse=True)
    return files


def get_file_metadata(key: str) -> FileMetadata | None:
    client = get_s3_client()
    try:
        response = client.head_object(
            Bucket=settings.b2_bucket_name, Key=key
        )
    except ClientError as e:
        # Only treat 404/NoSuchKey as "not found"; re-raise other errors
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise

    folder, filename = _split_key(key)
    return FileMetadata(
        key=key,
        filename=filename,
        folder=folder,
        size_bytes=response["ContentLength"],
        size_human=humanize_bytes(response["ContentLength"]),
        content_type=response.get("ContentType", _guess_content_type(key)),
        uploaded_at=response["LastModified"],
        url=_public_url(key),
    )


def delete_file(key: str) -> None:
    """Delete an object from B2. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        raise RuntimeError(f"B2 delete failed for '{key}': {e}") from e


def get_presigned_url(
    key: str, filename: str | None = None, expires_in: int = 600
) -> str:
    """Generate a presigned download URL. Raises RuntimeError on failure."""
    client = get_s3_client()
    params: dict = {"Bucket": settings.b2_bucket_name, "Key": key}
    if filename:
        # RFC 5987 encoding for non-ASCII filenames
        encoded = quote(filename, safe="")
        params["ResponseContentDisposition"] = (
            f"attachment; filename=\"{encoded}\"; filename*=UTF-8''{encoded}"
        )
    else:
        params["ResponseContentDisposition"] = "attachment"
    try:
        return client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


def get_stream_url(key: str, expires_in: int = 600) -> str:
    """Generate a presigned URL for inline playback (no attachment header).

    Used by the HTML5 audio player in the Library / Search pages so the
    browser streams the track instead of forcing a download.
    """
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.b2_bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 stream presign failed for '{key}': {e}") from e


def get_upload_stats() -> dict:
    """Paginate through all objects and return aggregate stats.

    Raises RuntimeError on S3 failure.
    """
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 stats query failed: {e}") from e

    total_size = sum(obj["Size"] for obj in contents)
    today = datetime.now(UTC).date()
    uploads_today = sum(
        1 for obj in contents if obj["LastModified"].date() == today
    )
    return {
        "total_files": len(contents),
        "total_size_bytes": total_size,
        "total_size_human": humanize_bytes(total_size),
        "uploads_today": uploads_today,
    }


# --- Raw byte / JSON helpers used by the audio analysis pipeline ---
# These keep all B2 I/O inside repo/ so the custom user agent on the single
# S3 client always holds. Essentia, CLAP, and LanceDB only ever see local
# bytes / local dirs — they never talk to B2 directly.


def download_file(key: str) -> bytes:
    """Fetch an object's bytes from B2. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return response["Body"].read()
    except ClientError as e:
        raise RuntimeError(f"B2 download failed for '{key}': {e}") from e


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    """Write raw bytes to B2. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e


def put_json(key: str, obj: dict) -> None:
    """Serialize and write a JSON object to B2."""
    put_bytes(key, json.dumps(obj).encode("utf-8"), "application/json")


def get_json(key: str) -> dict | None:
    """Read and parse a JSON object from B2. Returns None if it doesn't exist."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get_json failed for '{key}': {e}") from e
    return json.loads(response["Body"].read())


def list_keys(prefix: str = "") -> list[str]:
    """Return every object key under a prefix (paginated). Raises on failure."""
    client = get_s3_client()
    keys: list[str] = []
    kwargs: dict = {
        "Bucket": settings.b2_bucket_name,
        "Prefix": prefix,
        "MaxKeys": 1000,
    }
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            keys.extend(obj["Key"] for obj in response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list_keys failed for '{prefix}': {e}") from e
    return keys
