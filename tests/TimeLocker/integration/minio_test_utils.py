"""Shared helpers for MinIO integration tests."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import urlparse

DEFAULT_BUCKET = "timelocker-test"
DEFAULT_REGION = "us-east-1"


def _normalize_endpoint(value: str) -> Tuple[str, str]:
    parsed = urlparse(value)
    if parsed.scheme:
        url = value
        host = parsed.netloc or parsed.path
    else:
        host = value
        url = f"http://{value}"
    return url, host


def _extract_host_bucket_from_s3_uri(uri: str) -> Tuple[str | None, str | None]:
    if not uri.startswith("s3:"):
        return None, None

    remainder = uri[3:]
    if remainder.startswith("//"):
        remainder = remainder[2:]

    if remainder.startswith(("http://", "https://")):
        parsed = urlparse(remainder)
        host = parsed.netloc or parsed.path
        path_part = parsed.path.lstrip("/")
    else:
        parts = remainder.split("/", 1)
        host = parts[0]
        path_part = parts[1] if len(parts) > 1 else ""

    bucket = path_part.split("/", 1)[0] if path_part else None
    return host, bucket


def load_minio_settings(require_credentials: bool = True) -> Tuple[Dict[str, str], Tuple[str, ...]]:
    """Gather MinIO connection settings from environment or config files."""
    settings: Dict[str, str] = {}

    endpoint_value = (
            os.getenv("MINIO_ENDPOINT_URL")
            or os.getenv("AWS_S3_ENDPOINT")
            or os.getenv("MINIO_ENDPOINT")
    )
    if endpoint_value:
        url, host = _normalize_endpoint(endpoint_value)
        settings["MINIO_ENDPOINT_URL"] = url
        settings["MINIO_ENDPOINT_HOST"] = host
        settings.setdefault("AWS_S3_ENDPOINT", url)
        settings.setdefault("MINIO_URI_PREFIX", f"s3:{host}")

    for env_key in ("MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_BUCKET", "MINIO_REGION", "MINIO_VERIFY_SSL"):
        value = os.getenv(env_key)
        if value:
            settings[env_key] = value

    config_candidates = []
    env_config = os.getenv("TIMELOCKER_CONFIG_FILE")
    if env_config:
        config_candidates.append(Path(env_config))
    config_candidates.append(Path("test-config.json"))
    config_candidates.append(Path("test-config.example.json"))

    for config_path in config_candidates:
        if not config_path.is_file():
            continue
        try:
            config_data = json.loads(config_path.read_text())
        except Exception:
            continue

        for repo in config_data.get("repositories", []):
            uri = repo.get("uri") or repo.get("location")
            if not uri or not str(uri).startswith("s3"):
                continue

            host, bucket = _extract_host_bucket_from_s3_uri(str(uri))
            if host and "MINIO_ENDPOINT_HOST" not in settings:
                _, normalized_host = _normalize_endpoint(host)
                settings["MINIO_ENDPOINT_HOST"] = normalized_host
                settings["MINIO_ENDPOINT_URL"] = settings.get("MINIO_ENDPOINT_URL", f"http://{normalized_host}")
                settings.setdefault("AWS_S3_ENDPOINT", settings["MINIO_ENDPOINT_URL"])
                settings.setdefault("MINIO_URI_PREFIX", f"s3:{normalized_host}")
            if bucket and "MINIO_BUCKET" not in settings:
                settings["MINIO_BUCKET"] = bucket

            creds = repo.get("credentials", {})
            if isinstance(creds, dict):
                settings.setdefault("MINIO_ACCESS_KEY", creds.get("aws_access_key_id", ""))
                settings.setdefault("MINIO_SECRET_KEY", creds.get("aws_secret_access_key", ""))
                settings.setdefault("MINIO_REGION", creds.get("aws_default_region", ""))
            break

        missing_core = [key for key in ("MINIO_ENDPOINT_HOST", "MINIO_BUCKET") if not settings.get(key)]
        if not missing_core:
            break

    settings.setdefault("MINIO_BUCKET", DEFAULT_BUCKET)
    settings.setdefault("MINIO_REGION", os.getenv("AWS_DEFAULT_REGION", DEFAULT_REGION))
    settings.setdefault("MINIO_VERIFY_SSL", os.getenv("MINIO_VERIFY_SSL", settings.get("MINIO_VERIFY_SSL", "true")))
    if "MINIO_ENDPOINT_URL" not in settings and "MINIO_ENDPOINT_HOST" in settings:
        settings["MINIO_ENDPOINT_URL"] = f"http://{settings['MINIO_ENDPOINT_HOST']}"
    if "MINIO_URI_PREFIX" not in settings and "MINIO_ENDPOINT_HOST" in settings:
        settings["MINIO_URI_PREFIX"] = f"s3:{settings['MINIO_ENDPOINT_HOST']}"

    required = ["MINIO_ENDPOINT_URL", "MINIO_BUCKET", "MINIO_REGION"]
    if require_credentials:
        required.extend(["MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"])
    missing = tuple(key for key in required if not settings.get(key))

    return settings, missing


def ensure_minio_reachable(endpoint: str, access_key: str, secret_key: str, region: str, verify_ssl: bool = True):
    """Return a boto3 client if the MinIO endpoint is reachable."""
    import boto3
    from botocore.config import Config
    from botocore.exceptions import (
        ClientError,
        EndpointConnectionError,
    )
    from botocore.parsers import ResponseParserError
    from urllib.error import HTTPError
    import urllib.request

    tried_endpoints = set()
    candidates = [endpoint]
    if endpoint.startswith("http://"):
        candidates.append("https://" + endpoint[len("http://"):])

    last_error: Exception | None = None
    for candidate in candidates:
        if candidate in tried_endpoints:
            continue
        tried_endpoints.add(candidate)

        client = boto3.client(
                "s3",
                endpoint_url=candidate,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
                config=Config(s3={"addressing_style": "path"}),
                verify=verify_ssl,
        )

        try:
            client.list_buckets()
            return client
        except (ResponseParserError, TypeError) as exc:
            # Some proxies return an HTML redirect for http endpoints; retry with https
            last_error = exc
            continue
        except (EndpointConnectionError, ClientError) as exc:
            last_error = exc
        except Exception as exc:
            last_error = exc

    # Perform a lightweight HTTP check to surface clearer diagnostics
    try:
        with urllib.request.urlopen(endpoint, timeout=5) as response:
            if response.status >= 500:
                raise RuntimeError(f"MinIO endpoint responded with status {response.status}")
    except HTTPError as exc:
        if exc.code >= 500:
            raise RuntimeError(f"MinIO endpoint responded with status {exc.code}")
    except Exception as exc:
        raise RuntimeError(f"MinIO not reachable: {exc}")

    if last_error:
        raise RuntimeError(f"Unable to reach MinIO endpoint '{endpoint}': {last_error}") from last_error
    raise RuntimeError(f"Unable to reach MinIO endpoint '{endpoint}'")
