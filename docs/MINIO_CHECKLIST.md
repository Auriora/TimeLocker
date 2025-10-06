# MinIO Testing Setup Checklist

Quick checklist to verify your MinIO testing environment is ready.

## ✅ Pre-Flight Checklist

### 1. Network Configuration
- [ ] `/etc/hosts` contains entry for `minio.local`
- [ ] `/etc/hosts` contains entry for `minio-console.local`
- [ ] Can ping `minio.local`
- [ ] Can access MinIO API (proxied via Traefik): `curl http://minio.local/minio/health/live`

**Verify:**
```bash
grep minio /etc/hosts
ping -c 1 minio.local
curl http://minio.local/minio/health/live
```

### 2. Python Environment
- [ ] Virtual environment exists (`.venv`)
- [ ] Virtual environment is activated
- [ ] boto3 is installed
- [ ] TimeLocker dependencies are installed

**Verify:**
```bash
which python  # Should show .venv path
python -c "import boto3; print('boto3 OK')"
pip list | grep boto3
```

### 3. Configuration Files
- [ ] `.env.test` exists
- [ ] `.env.test` has correct MinIO endpoint (`minio.local` - no port, proxied via Traefik)
- [ ] `test-config.json` exists (optional)
- [ ] Environment variables are loaded

**Verify:**
```bash
ls -la .env.test
grep MINIO_ENDPOINT .env.test
source .env.test
env | grep MINIO
```

### 4. MinIO Access
- [ ] Can access MinIO console in browser
- [ ] Know MinIO credentials
- [ ] `timelocker-test` bucket exists
- [ ] Can list buckets via API

**Verify:**
```bash
# Open in browser
echo "Open: http://minio-console.local"

# Test with boto3
python -c "
import boto3
s3 = boto3.client('s3',
    endpoint_url='http://minio.local',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin')
print(s3.list_buckets())
"
```

## 🚀 Setup Steps

### Step 1: Run Setup Script
```bash
./scripts/setup_minio_test.sh
```

**Expected Output:**
- ✅ minio.local found in /etc/hosts
- ✅ MinIO API is accessible
- ✅ .env.test created
- ✅ boto3 is installed

### Step 2: Load Environment
```bash
source .env.test
```

**Verify:**
```bash
echo $MINIO_ENDPOINT  # Should show: minio.local
echo $AWS_S3_ENDPOINT  # Should show: http://minio.local
```

### Step 3: Run Tests
```bash
source .venv/bin/activate
pytest tests/TimeLocker/integration/test_s3_minio.py -v
```

**Expected Output:**
- Tests should run (not skip)
- Tests should pass
- No connection errors

## 🔍 Verification Commands

### Quick Verification
```bash
# All-in-one verification
./scripts/setup_minio_test.sh && \
source .env.test && \
pytest tests/TimeLocker/integration/test_s3_minio.py::test_s3_repository_initialization -v
```

### Individual Checks

#### Check 1: DNS Resolution
```bash
ping -c 1 minio.local
# Expected: Reply from minio.local
```

#### Check 2: MinIO Health
```bash
curl http://minio.local/minio/health/live
# Expected: Empty response with 200 OK
```

#### Check 3: MinIO Console
```bash
curl -I http://minio-console.local
# Expected: HTTP 200 or 302
```

#### Check 4: boto3 Connection
```bash
python -c "
import boto3
from botocore.exceptions import ClientError
try:
    s3 = boto3.client('s3',
        endpoint_url='http://minio.local',
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin')
    buckets = s3.list_buckets()
    print('✅ boto3 connection successful')
    print(f'Buckets: {[b[\"Name\"] for b in buckets[\"Buckets\"]]}')
except Exception as e:
    print(f'❌ boto3 connection failed: {e}')
"
```

#### Check 5: Test Configuration
```bash
python -c "
import json
with open('test-config.json') as f:
    config = json.load(f)
    repo = config['repositories'][0]
    print(f'Repository: {repo[\"name\"]}')
    print(f'URI: {repo[\"uri\"]}')
    assert 'minio.local' in repo['uri'], 'Config should use minio.local'
    print('✅ Configuration correct')
"
```

## 🐛 Troubleshooting Checklist

### Problem: Cannot resolve minio.local

**Checks:**
- [ ] `/etc/hosts` has entry for minio.local
- [ ] Entry format is correct: `<ip> minio.local`
- [ ] No typos in hostname
- [ ] DNS cache cleared (if applicable)

**Fix:**
```bash
# Add to /etc/hosts
echo "<minio-ip> minio.local minio-console.local" | sudo tee -a /etc/hosts

# Verify
grep minio /etc/hosts
ping minio.local
```

### Problem: Connection refused

**Checks:**
- [ ] MinIO is running on the server
- [ ] Traefik proxy is running
- [ ] Port 80 is accessible
- [ ] Firewall allows connection
- [ ] Network route to MinIO server exists

**Fix:**
```bash
# Test connection (port 80 via Traefik)
curl -v http://minio.local/minio/health/live

# Check from MinIO server
curl http://localhost/minio/health/live
```

### Problem: Tests skipped

**Checks:**
- [ ] boto3 is installed
- [ ] Environment variables are set
- [ ] MinIO is accessible
- [ ] Virtual environment is activated

**Fix:**
```bash
# Install boto3
pip install boto3

# Load environment
source .env.test

# Verify
env | grep -E "(MINIO|AWS)"
```

### Problem: Authentication failed

**Checks:**
- [ ] Credentials are correct
- [ ] Environment variables are set
- [ ] `.env.test` has correct credentials

**Fix:**
```bash
# Check credentials
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY

# Update .env.test if needed
nano .env.test
source .env.test
```

## 📊 Success Criteria

You're ready to test when:

- ✅ `./scripts/setup_minio_test.sh` completes without errors
- ✅ `curl http://minio.local/minio/health/live` returns 200 OK
- ✅ Can access http://minio-console.local in browser
- ✅ `source .env.test && env | grep MINIO` shows correct values
- ✅ `pytest tests/TimeLocker/integration/test_s3_minio.py::test_s3_repository_initialization -v` passes

## 🎯 Quick Test

Run this one-liner to verify everything:

```bash
./scripts/setup_minio_test.sh && \
source .venv/bin/activate && \
source .env.test && \
pytest tests/TimeLocker/integration/test_s3_minio.py::test_s3_repository_initialization -v && \
echo "✅ All checks passed! Ready to test."
```

## 📚 Next Steps

Once all checks pass:

1. Read `MINIO_SETUP_SUMMARY.md` for overview
2. Review `docs/MINIO_TESTING.md` for detailed guide
3. Check `TESTING_QUICKSTART.md` for common commands
4. Run full test suite: `pytest tests/TimeLocker/integration/test_s3_minio.py -v`

## 🆘 Getting Help

If you're stuck:

1. Review this checklist
2. Check `MINIO_SETUP_SUMMARY.md`
3. Read troubleshooting in `docs/MINIO_TESTING.md`
4. Verify MinIO server is running (contact admin if needed)
5. Check network connectivity to MinIO server

