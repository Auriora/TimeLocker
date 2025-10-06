# TimeLocker Testing Quick Start

Quick reference for setting up and running TimeLocker tests with the existing MinIO deployment at `minio.local` (proxied via Traefik).

## 🚀 Quick Setup (2 minutes)

### 1. Verify MinIO Access

```bash
# One-command verification
./scripts/setup_minio_test.sh
```

This will:

- ✅ Verify MinIO at `minio.local` (port 80, proxied via Traefik) is accessible
- ✅ Check `/etc/hosts` configuration
- ✅ Install boto3 if needed
- ✅ Create `.env.test` configuration

### 2. Run S3 Integration Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Load test environment
source .env.test

# Run S3/MinIO tests
pytest tests/TimeLocker/integration/test_s3_minio.py -v
```

## 📋 Test Commands

### Run All Tests

```bash
pytest
```

### Run by Category

```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Network tests (includes S3/MinIO)
pytest -m "integration and network"

# Exclude slow tests
pytest -m "not slow"
```

### Run Specific Tests

```bash
# Single test file
pytest tests/TimeLocker/integration/test_s3_minio.py -v

# Single test function
pytest tests/TimeLocker/integration/test_s3_minio.py::test_s3_backup_and_restore -v

# Pattern matching
pytest -k "s3" -v
```

### With Coverage

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## 🔧 Configuration Files

### Test Configuration

```bash
# Copy example config
cp test-config.example.json test-config.json

# Use test config
export TIMELOCKER_CONFIG_FILE=./test-config.json
```

### Environment Variables

```bash
# Copy example environment
cp .env.test.example .env.test

# Load environment
source .env.test

# Or use direnv
echo "source .env.test" > .envrc
direnv allow
```

## 🐳 MinIO Access

### Access MinIO Console

```
URL: http://minio-console.local
Username: minioadmin (or your configured credentials)
Password: minioadmin (or your configured credentials)
```

Note: Proxied through Traefik on port 80, no port number needed.

### Verify MinIO Access

```bash
# Test API connection (proxied via Traefik on port 80)
curl http://minio.local/minio/health/live

# Test DNS resolution
ping minio.local

# Check /etc/hosts
grep minio /etc/hosts
```

### Using Existing MinIO Deployment

The project is configured to use the existing MinIO deployment (proxied via Traefik) at:

- **API**: `minio.local` (port 80)
- **Console**: `minio-console.local` (port 80)

### Optional: Local MinIO Instance

If you need your own local MinIO:

```bash
# Start local MinIO
docker-compose -f docker-compose.local.yml up -d

# Update .env.test to use localhost
export MINIO_ENDPOINT="localhost:9000"
export AWS_S3_ENDPOINT="http://localhost:9000"
```

## 🧪 Manual Testing with CLI

### Setup Test Repository

```bash
# Load environment
source .env.test

# Add repository
tl repos add minio-test "s3:http://minio.local/timelocker-test/my-repo" \
  --description "MinIO test repository"

# Initialize repository
tl repos init minio-test --password "test-password-123"
```

### Create Test Backup

```bash
# Create test data
mkdir -p /tmp/test-backup-source
echo "Test file 1" > /tmp/test-backup-source/file1.txt
echo "Test file 2" > /tmp/test-backup-source/file2.txt

# Add target
tl targets add test-backup /tmp/test-backup-source

# Run backup
tl backup create test-backup --repository minio-test
```

### List and Restore

```bash
# List snapshots
tl snapshots list --repository minio-test

# Restore
mkdir -p /tmp/test-restore
tl snapshot <snapshot-id> restore /tmp/test-restore

# Verify
ls -la /tmp/test-restore
```

## 🐛 Troubleshooting

### Cannot Access minio.local

```bash
# Check /etc/hosts
grep minio /etc/hosts

# Test DNS resolution
ping minio.local

# Test connection (proxied via Traefik)
curl http://minio.local/minio/health/live
```

**Solution**: Ensure `/etc/hosts` has the correct entry for minio.local

### Tests Skipped

```bash
# Install boto3
pip install boto3

# Verify MinIO is accessible
curl http://minio.local/minio/health/live

# Check environment
env | grep -E "(MINIO|AWS)"

# Load environment
source .env.test
```

### Connection Errors

```bash
# Check MinIO is accessible
curl -v http://minio.local:9000

# Check firewall (on MinIO server)
sudo ufw status

# Verify /etc/hosts
cat /etc/hosts | grep minio
```

### Bucket Not Found

```bash
# Check if bucket exists via console
# Open http://minio-console.local

# Or use MinIO client (mc)
mc alias set myminio http://minio.local minioadmin minioadmin
mc ls myminio

# Create bucket if needed
mc mb myminio/timelocker-test
```

## 📚 Documentation

- **Full MinIO Guide**: [docs/MINIO_TESTING.md](docs/MINIO_TESTING.md)
- **Test Suite Overview**: [tests/README.md](tests/README.md)
- **Repository Guide**: [docs/repository_management_guide.md](docs/repository_management_guide.md)

## 🎯 Common Test Scenarios

### Test S3 Backup and Restore

```bash
pytest tests/TimeLocker/integration/test_s3_minio.py::test_s3_backup_and_restore -v -s
```

### Test Multiple Backups

```bash
pytest tests/TimeLocker/integration/test_s3_minio.py::test_s3_multiple_backups -v
```

### Test Error Handling

```bash
pytest tests/TimeLocker/integration/test_s3_minio.py::test_s3_missing_credentials_error -v
```

### Run All S3 Tests

```bash
pytest tests/TimeLocker/integration/test_s3_minio.py -v
```

## 🔄 Cleanup

### Remove Test Data

```bash
# Remove test directories
rm -rf /tmp/test-backup-source /tmp/test-restore

# Remove test config (if needed - be careful!)
rm test-config.json .env.test

# Note: MinIO data persists on the server
# Contact your administrator to clean up test data in MinIO
```

### Clean Up Local MinIO (if using docker-compose.local.yml)

```bash
# Stop local MinIO
docker-compose -f docker-compose.local.yml down

# Remove volumes (all data)
docker-compose -f docker-compose.local.yml down -v
```

## 💡 Tips

1. **Use test config**: Keep test configuration separate from production
2. **Check MinIO console**: Visual interface helps debug issues
3. **Watch logs**: `docker-compose logs -f` shows real-time activity
4. **Parallel tests**: Use `pytest -n auto` for faster execution
5. **Debug mode**: Use `pytest -vv -s` for detailed output
6. **Markers**: Use markers to run specific test categories

## 🚦 CI/CD

Tests run automatically on:

- Pull requests
- Pushes to main
- Scheduled runs

MinIO is started as a service in GitHub Actions.

## ✅ Verification Checklist

- [ ] MinIO is accessible (`curl http://minio.local/minio/health/live`)
- [ ] `/etc/hosts` has minio.local entry (`grep minio /etc/hosts`)
- [ ] boto3 is installed (`python -c "import boto3"`)
- [ ] Virtual environment is activated (`which python`)
- [ ] Environment variables are set (`source .env.test && env | grep AWS`)
- [ ] Test config exists (`ls test-config.json`)
- [ ] Can access MinIO console (`curl http://minio-console.local`)

## 🎓 Next Steps

1. Read [docs/MINIO_TESTING.md](docs/MINIO_TESTING.md) for detailed setup
2. Explore [tests/README.md](tests/README.md) for test organization
3. Check [docs/repository_management_guide.md](docs/repository_management_guide.md) for CLI usage
4. Review test examples in `tests/TimeLocker/integration/`

---

**Need Help?** Check the troubleshooting section or open an issue on GitHub.

