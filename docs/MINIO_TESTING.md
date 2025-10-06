# MinIO Testing Setup for TimeLocker

This guide explains how to use the existing MinIO deployment at `minio.local` for S3 integration testing with TimeLocker.

## Overview

MinIO is an S3-compatible object storage server that allows you to test S3 functionality without needing AWS credentials or incurring cloud costs.

**This project uses an existing MinIO deployment (proxied behind Traefik) at:**
- **API**: `minio.local` (port 80, proxied via Traefik)
- **Console**: `minio-console.local` (port 80, proxied via Traefik)

## Prerequisites

- Access to MinIO deployment at `minio.local`
- Python 3.11+ with TimeLocker development dependencies
- boto3 installed (`pip install boto3`)
- `/etc/hosts` configured with MinIO hostnames

## Quick Start

### 1. Verify MinIO Access

```bash
# Run the setup script to verify access
./scripts/setup_minio_test.sh
```

This will:
- ✅ Check `/etc/hosts` for `minio.local` entry
- ✅ Verify MinIO API is accessible
- ✅ Create `.env.test` configuration file
- ✅ Install boto3 if needed

### 2. Verify /etc/hosts Configuration

Ensure your `/etc/hosts` file contains entries for MinIO:

```bash
# Check current entries
grep minio /etc/hosts
```

You should see something like:
```
<minio-ip> minio.local minio-console.local
```

If not present, contact your system administrator or add them if you have access.

### 3. Access MinIO Console

Open your browser and navigate to:
- **Console URL**: http://minio-console.local
- **Username**: minioadmin (or your configured credentials)
- **Password**: minioadmin (or your configured credentials)

Note: The console is proxied through Traefik on port 80, so no port number is needed.

### 4. Create Test Bucket (if needed)

If the `timelocker-test` bucket doesn't exist, create it via the console or CLI.

### 5. Run Integration Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run S3/MinIO integration tests
pytest tests/TimeLocker/integration/test_s3_minio.py -v -m "integration and network"

# Run all integration tests
pytest tests/TimeLocker/integration/ -v -m integration
```

## Configuration

### Environment Variables

You can customize MinIO settings using environment variables:

```bash
export MINIO_ENDPOINT="minio.local"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
export MINIO_BUCKET="timelocker-test"
export MINIO_REGION="us-east-1"
```

Note: No port number needed - MinIO is proxied through Traefik on port 80.

Or use the `.env.test` file:

```bash
# Copy and customize
cp .env.test.example .env.test

# Load environment
source .env.test
```

### Test Configuration File

A sample test configuration is provided in `test-config.json`:

```bash
# Use test configuration
export TIMELOCKER_CONFIG_FILE="./test-config.json"

# Run TimeLocker CLI with test config
tl repos list
```

## Testing Workflow

### 1. Initialize Test Repository

```bash
# Load environment variables
source .env.test

# Using TimeLocker CLI
tl repos add minio-test "s3:http://minio.local/timelocker-test/my-repo" \
  --description "MinIO test repository"

# Initialize repository
tl repos init minio-test --password "test-password-123"
```

### 2. Create Test Backup

```bash
# Create test data
mkdir -p /tmp/test-backup-source
echo "Test file 1" > /tmp/test-backup-source/file1.txt
echo "Test file 2" > /tmp/test-backup-source/file2.txt

# Add backup target
tl targets add test-backup /tmp/test-backup-source \
  --description "Test backup target"

# Run backup
tl backup create test-backup --repository minio-test
```

### 3. List Snapshots

```bash
# List all snapshots
tl snapshots list --repository minio-test

# Get snapshot details
tl snapshot <snapshot-id> show
```

### 4. Restore from Backup

```bash
# Restore to directory
mkdir -p /tmp/test-restore
tl snapshot <snapshot-id> restore /tmp/test-restore

# Verify restored files
ls -la /tmp/test-restore
```

## Integration Test Details

The integration tests in `tests/TimeLocker/integration/test_s3_minio.py` cover:

1. **Repository Initialization**: Creating and initializing S3 repositories
2. **Backup Operations**: Creating backups with real data
3. **Restore Operations**: Restoring files from snapshots
4. **Snapshot Management**: Listing and managing snapshots
5. **Incremental Backups**: Testing deduplication and incremental changes
6. **Error Handling**: Testing credential errors and edge cases

### Test Markers

Tests are marked with:
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.network` - Tests requiring network access

### Running Specific Tests

```bash
# Run only S3/MinIO tests
pytest tests/TimeLocker/integration/test_s3_minio.py -v

# Run specific test
pytest tests/TimeLocker/integration/test_s3_minio.py::test_s3_backup_and_restore -v

# Skip integration tests
pytest -m "not integration"
```

## Optional: Local MinIO Deployment

If you need to run your own local MinIO instance instead of using the shared deployment:

```bash
# Start local MinIO using Docker Compose
docker-compose -f docker-compose.local.yml up -d

# This will start MinIO on localhost:9000
# Update your .env.test to use localhost instead of minio.local
export MINIO_ENDPOINT="localhost:9000"
export AWS_S3_ENDPOINT="http://localhost:9000"
```

## Troubleshooting

### Cannot Access minio.local

```bash
# Check /etc/hosts
grep minio /etc/hosts

# Test DNS resolution
ping minio.local

# Test connection
curl http://minio.local/minio/health/live
```

If you get "Could not resolve host", add to `/etc/hosts`:
```bash
<minio-server-ip> minio.local minio-console.local
```

### Connection Refused

Ensure MinIO is running and accessible:

```bash
# Test connection (Traefik proxy on port 80)
curl http://minio.local/minio/health/live

# Check if Traefik is accessible
curl -I http://minio.local

# Check firewall
sudo ufw status
```

### Bucket Not Found

The bucket should be created automatically. If not:

```bash
# Use MinIO client to create bucket
docker run --rm --network timelocker-test \
  minio/mc alias set myminio http://minio:9000 minioadmin minioadmin

docker run --rm --network timelocker-test \
  minio/mc mb myminio/timelocker-test
```

### Tests Skipped

If tests are skipped with "MinIO not available":

1. Verify MinIO is running: `docker-compose ps`
2. Check boto3 is installed: `pip install boto3`
3. Verify network connectivity: `curl http://localhost:9000`

## Cleanup

### Remove Test Data

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (deletes all data)
docker-compose down -v

# Remove test directories
rm -rf /tmp/test-backup-source /tmp/test-restore
```

### Reset MinIO

```bash
# Complete reset
docker-compose down -v
docker volume rm timelocker_minio-data
docker-compose up -d
```

## Advanced Usage

### Custom MinIO Configuration

Edit `docker-compose.yml` to customize:

```yaml
environment:
  MINIO_ROOT_USER: custom-user
  MINIO_ROOT_PASSWORD: custom-password
  MINIO_REGION: eu-west-1
```

### Multiple Buckets

```bash
# Create additional buckets
docker run --rm --network timelocker-test \
  minio/mc mb myminio/another-bucket
```

### TLS/HTTPS Setup

For testing with HTTPS, you'll need to:

1. Generate certificates
2. Mount certificates in docker-compose.yml
3. Update MinIO command to use certificates
4. Update test configuration to use https://

See MinIO documentation for detailed TLS setup.

## CI/CD Integration

For GitHub Actions or other CI systems:

```yaml
# .github/workflows/test.yml
services:
  minio:
    image: minio/minio
    ports:
      - 9000:9000
    env:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    options: >-
      --health-cmd "curl -f http://localhost:9000/minio/health/live"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

## Resources

- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [MinIO Docker Hub](https://hub.docker.com/r/minio/minio)
- [Restic S3 Backend](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html#amazon-s3)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

