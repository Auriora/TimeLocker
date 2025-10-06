# MinIO Testing Setup Summary

## Overview

TimeLocker is now configured to use your existing MinIO deployment (proxied via Traefik) for S3 integration testing.

**MinIO Endpoints:**
- **API**: `minio.local` (port 80, proxied via Traefik)
- **Console**: `minio-console.local` (port 80, proxied via Traefik)

## Quick Start

```bash
# 1. Verify MinIO access
./scripts/setup_minio_test.sh

# 2. Load environment
source .env.test

# 3. Run tests
pytest tests/TimeLocker/integration/test_s3_minio.py -v
```

## Configuration Files

All configuration files have been updated to use `minio.local`:

### Updated Files
- ✅ `test-config.json` - Uses `minio.local:9000`
- ✅ `test-config.example.json` - Uses `minio.local:9000`
- ✅ `.env.test.example` - Uses `minio.local:9000`
- ✅ `tests/TimeLocker/integration/test_s3_minio.py` - Defaults to `minio.local:9000`
- ✅ `scripts/setup_minio_test.sh` - Verifies access to `minio.local`
- ✅ `docs/MINIO_TESTING.md` - Updated for existing deployment
- ✅ `TESTING_QUICKSTART.md` - Updated for existing deployment

### New Files
- ✅ `docker-compose.local.yml` - Optional local MinIO (renamed from docker-compose.yml)
- ✅ `docker-compose.local.yml.README.md` - Instructions for local MinIO

## What Changed

### Before
- Configuration used `localhost:9000`
- Required starting local MinIO with docker-compose
- Setup script started MinIO containers

### After
- Configuration uses `minio.local` (port 80, proxied via Traefik)
- Uses existing MinIO deployment
- Setup script verifies access to existing MinIO
- Optional local MinIO available via `docker-compose.local.yml`

## Prerequisites

Ensure your `/etc/hosts` file contains:
```
<minio-ip> minio.local minio-console.local
```

If not, contact your system administrator or add them if you have access.

## Testing Workflow

### 1. First Time Setup
```bash
# Run setup script
./scripts/setup_minio_test.sh

# This will:
# - Check /etc/hosts for minio.local
# - Verify MinIO API is accessible
# - Create .env.test configuration
# - Install boto3 if needed
```

### 2. Run Tests
```bash
# Activate virtual environment
source .venv/bin/activate

# Load environment
source .env.test

# Run S3 integration tests
pytest tests/TimeLocker/integration/test_s3_minio.py -v
```

### 3. Manual Testing
```bash
# Load environment
source .env.test

# Add repository
tl repos add minio-test "s3:http://minio.local/timelocker-test/my-repo"

# Initialize
tl repos init minio-test --password "test-password-123"

# Create test data
mkdir -p /tmp/test-backup-source
echo "Test file" > /tmp/test-backup-source/test.txt

# Add target
tl targets add test-backup /tmp/test-backup-source

# Run backup
tl backup create test-backup --repository minio-test

# List snapshots
tl snapshots list --repository minio-test
```

## Access MinIO Console

Open your browser:
```
http://minio-console.local
```

Note: Proxied through Traefik on port 80.

Default credentials (may be different in your deployment):
- Username: `minioadmin`
- Password: `minioadmin`

## Troubleshooting

### Cannot Access minio.local

**Problem**: `curl: (6) Could not resolve host: minio.local`

**Solution**: Add to `/etc/hosts`:
```bash
<minio-server-ip> minio.local minio-console.local
```

### Connection Refused

**Problem**: `curl: (7) Failed to connect to minio.local port 9000`

**Solutions**:
1. Verify MinIO is running on the server
2. Check firewall allows port 9000
3. Verify network connectivity to MinIO server

### Tests Skipped

**Problem**: Tests show "MinIO not available"

**Solutions**:
1. Install boto3: `pip install boto3`
2. Load environment: `source .env.test`
3. Verify MinIO access: `curl http://minio.local:9000/minio/health/live`

## Optional: Local MinIO

If you need to run your own local MinIO instance:

```bash
# Start local MinIO
docker-compose -f docker-compose.local.yml up -d

# Update .env.test
export MINIO_ENDPOINT="localhost:9000"
export AWS_S3_ENDPOINT="http://localhost:9000"

# Run tests
pytest tests/TimeLocker/integration/test_s3_minio.py -v
```

See `docker-compose.local.yml.README.md` for details.

## Environment Variables

The `.env.test` file contains:

```bash
# MinIO Configuration (proxied via Traefik on port 80)
MINIO_ENDPOINT=minio.local
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=timelocker-test
MINIO_REGION=us-east-1

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_DEFAULT_REGION=us-east-1
AWS_S3_ENDPOINT=http://minio.local

# TimeLocker Configuration
TIMELOCKER_CONFIG_FILE=./test-config.json
TIMELOCKER_PASSWORD=test-password-123
```

## Integration Tests

The test suite includes:

- ✅ Repository initialization
- ✅ Backend environment configuration
- ✅ Backup operations
- ✅ Restore operations
- ✅ Snapshot listing
- ✅ Multiple backups (incremental)
- ✅ Repository statistics
- ✅ Error handling

Run specific tests:
```bash
# All S3 tests
pytest tests/TimeLocker/integration/test_s3_minio.py -v

# Specific test
pytest tests/TimeLocker/integration/test_s3_minio.py::test_s3_backup_and_restore -v

# With markers
pytest -m "integration and network" -v
```

## Documentation

- **Quick Start**: `TESTING_QUICKSTART.md`
- **Full Guide**: `docs/MINIO_TESTING.md`
- **Test Suite**: `tests/README.md`
- **Local MinIO**: `docker-compose.local.yml.README.md`

## Next Steps

1. ✅ Run setup script: `./scripts/setup_minio_test.sh`
2. ✅ Verify access to MinIO console: http://minio-console.local
3. ✅ Run integration tests: `pytest tests/TimeLocker/integration/test_s3_minio.py -v`
4. ✅ Read full documentation: `docs/MINIO_TESTING.md`

## Support

If you encounter issues:
1. Check troubleshooting section above
2. Review `docs/MINIO_TESTING.md`
3. Verify `/etc/hosts` configuration
4. Contact your system administrator for MinIO access issues

