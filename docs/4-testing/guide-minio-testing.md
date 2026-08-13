---
title: MinIO integration testing
doc_type: guide
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# MinIO Integration Testing

Use this guide for the four live S3 integration tests marked `minio`. Mocked
credential, backend-environment, and protocol-contract tests belong to the
normal CI profile and do not require a service.

## Requirements

- Python 3.12 with `pip install -e .[dev]`;
- Restic 0.18.0 or later;
- an isolated MinIO service and disposable bucket;
- non-production credentials supplied through environment variables.

Required variables:

```bash
export MINIO_ENDPOINT_URL=http://127.0.0.1:9000
export AWS_S3_ENDPOINT="$MINIO_ENDPOINT_URL"
export MINIO_ACCESS_KEY=timelocker-local
export MINIO_SECRET_KEY=timelocker-local-secret
export MINIO_BUCKET=timelocker-test
export MINIO_REGION=us-east-1
export MINIO_VERIFY_SSL=false
```

Use `MINIO_VERIFY_SSL=false` only for a trusted local HTTP service. Never use
production credentials or a production bucket.

## Run the Profile

Start a disposable service:

```bash
docker run --detach --rm \
  --name timelocker-minio \
  --publish 127.0.0.1:9000:9000 \
  --env MINIO_ROOT_USER="$MINIO_ACCESS_KEY" \
  --env MINIO_ROOT_PASSWORD="$MINIO_SECRET_KEY" \
  quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z \
  server /data --address :9000
```

Wait for the service and create the bucket before pytest:

```bash
curl --fail "$MINIO_ENDPOINT_URL/minio/health/live"
python - <<'PY'
import os

import boto3
from botocore.config import Config

client = boto3.client(
    "s3",
    endpoint_url=os.environ["MINIO_ENDPOINT_URL"],
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    region_name=os.environ["MINIO_REGION"],
    config=Config(s3={"addressing_style": "path"}),
)
bucket = os.environ["MINIO_BUCKET"]
existing = {item["Name"] for item in client.list_buckets()["Buckets"]}
if bucket not in existing:
    client.create_bucket(Bucket=bucket)
PY
python -m pytest -m minio --no-cov
```

Remove the disposable service:

```bash
docker rm --force timelocker-minio
```

The profile uses `--no-cov` because the normal correctness profile owns the
repository's 50 percent coverage gate.

## Failure Contract

Collection does not load MinIO configuration or contact the network. The live
profile loads its settings at runtime and fails with
`MinIO profile dependency error` when configuration is missing or the service
is unavailable. A missing service is not a skip.

If readiness fails:

1. confirm `curl --fail "$MINIO_ENDPOINT_URL/minio/health/live"` succeeds;
2. confirm all required variables are exported in the pytest process;
3. confirm the bucket exists and credentials can list it;
4. inspect `docker logs timelocker-minio` for service startup errors.

Do not print credential values while troubleshooting.

## GitHub Actions Ownership

The `minio-test` job in `.github/workflows/test-suite.yml` owns provisioning,
readiness, bucket creation, the live pytest selector, and container cleanup. The
normal job excludes `minio`, `performance`, and `stress`; the extended job
owns the latter two profiles.

## Related Commands

```bash
# Normal correctness and coverage
python -m pytest -m "not performance and not stress and not minio"

# Live service only
python -m pytest -m minio --no-cov

# Performance and stress
python -m pytest -m "performance or stress" --no-cov
```
