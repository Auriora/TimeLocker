# Using S3-Compatible Services with TimeLocker

TimeLocker supports S3-compatible storage services like MinIO, Wasabi, Backblaze B2 (via S3 API), and others through comprehensive AWS S3 endpoint configuration.

## Overview

As of the latest version, TimeLocker stores AWS credentials and S3 endpoint configuration per-repository in the credential manager. This means:

- ✅ No manual environment variable setup required
- ✅ Endpoint stored securely per-repository
- ✅ Automatic environment configuration for restic operations
- ✅ Easy switching between different S3-compatible services

## Supported Services

### MinIO
Self-hosted S3-compatible object storage.

**Example Configuration:**
```bash
tl repos add my-minio-repo
# When prompted:
Repository URI: s3:minio.local/my-bucket
Store password: yes
Store AWS credentials: yes
AWS Access Key ID: minioadmin
AWS Secret Access Key: minioadmin
AWS Region: us-east-1
AWS S3 Endpoint: http://minio.local:9000
```

### Wasabi
Cloud storage service with S3-compatible API.

**Example Configuration:**
```bash
tl repos add my-wasabi-repo
# When prompted:
Repository URI: s3:s3.wasabisys.com/my-bucket
Store password: yes
Store AWS credentials: yes
AWS Access Key ID: <your-wasabi-access-key>
AWS Secret Access Key: <your-wasabi-secret-key>
AWS Region: us-east-1
AWS S3 Endpoint: https://s3.wasabisys.com
```

### Backblaze B2 (S3 API)
Backblaze B2 with S3-compatible API.

**Example Configuration:**
```bash
tl repos add my-b2-s3-repo
# When prompted:
Repository URI: s3:s3.us-west-002.backblazeb2.com/my-bucket
Store password: yes
Store AWS credentials: yes
AWS Access Key ID: <your-b2-keyID>
AWS Secret Access Key: <your-b2-applicationKey>
AWS Region: us-west-002
AWS S3 Endpoint: https://s3.us-west-002.backblazeb2.com
```

### DigitalOcean Spaces
DigitalOcean's S3-compatible object storage.

**Example Configuration:**
```bash
tl repos add my-do-spaces-repo
# When prompted:
Repository URI: s3:nyc3.digitaloceanspaces.com/my-space
Store password: yes
Store AWS credentials: yes
AWS Access Key ID: <your-spaces-access-key>
AWS Secret Access Key: <your-spaces-secret-key>
AWS Region: nyc3
AWS S3 Endpoint: https://nyc3.digitaloceanspaces.com
```

## Quick Start Guide

### 1. Add Repository

```bash
tl repos add <repository-name>
```

You'll be prompted for:
- **Repository URI**: Format is `s3:hostname/bucket/path`
- **Password**: Repository encryption password
- **AWS Credentials**: Access key ID and secret access key
- **AWS Region**: Region for the service (optional but recommended)
- **AWS S3 Endpoint**: Full endpoint URL (e.g., `http://minio.local:9000`)

### 2. Initialize Repository

```bash
tl repos init <repository-name>
```

This creates the restic repository structure in your S3-compatible storage.

### 3. Use Repository

```bash
# Add backup target
tl targets add my-docs ~/Documents

# Run backup
tl backup my-docs -r <repository-name>

# List snapshots
tl snapshots list -r <repository-name>
```

## Updating Credentials

If you need to update the S3 endpoint or credentials for an existing repository:

```bash
tl repos credentials set <repository-name>
```

This will prompt you for new credentials and endpoint configuration.

## Troubleshooting

### Connection Issues

If you're having trouble connecting to your S3-compatible service:

1. **Verify endpoint is accessible:**
   ```bash
   curl -I http://your-endpoint:9000
   ```

2. **Check credentials are correct:**
   - Access Key ID
   - Secret Access Key
   - Endpoint URL (including protocol: http:// or https://)

3. **Verify bucket exists:**
   Use the service's web console or CLI to confirm the bucket is created

### SSL/TLS Issues

For self-signed certificates or local development:

- Use `http://` instead of `https://` for the endpoint
- For production, ensure proper SSL certificates are configured

### AWS SSO Interference

If you have AWS SSO configured in `~/.aws/config`, it might interfere with S3-compatible services:

**Solution:** TimeLocker's per-repository credentials take precedence, so this should not be an issue. However, if you encounter problems:

```bash
# Temporarily disable AWS profile
unset AWS_PROFILE
tl repos init <repository-name>
```

## Advanced Configuration

### Using Environment Variables (Legacy)

While TimeLocker now stores credentials per-repository, you can still use environment variables for testing or automation:

```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_S3_ENDPOINT=http://minio.local:9000
export AWS_DEFAULT_REGION=us-east-1

tl repos add test-repo s3:minio.local/bucket
```

**Note:** Per-repository credentials stored via `tl repos add` take precedence over environment variables.

### Multiple Repositories

You can configure multiple repositories with different S3-compatible services:

```bash
# MinIO repository
tl repos add minio-backup s3:minio.local/backups

# Wasabi repository
tl repos add wasabi-backup s3:s3.wasabisys.com/backups

# Each repository stores its own credentials and endpoint
```

## Security Best Practices

1. **Use strong passwords** for repository encryption
2. **Rotate credentials** regularly
3. **Use HTTPS endpoints** in production
4. **Limit access key permissions** to only what's needed
5. **Enable MFA** on your S3-compatible service if supported
6. **Use credential manager** instead of environment variables

## Testing Your Setup

Use the provided test script to verify your S3-compatible service configuration:

```bash
python test_minio_connection.py
```

This will test:
1. Direct boto3 connection to your endpoint
2. TimeLocker credential storage
3. S3ResticRepository initialization

## Common Endpoint URLs

| Service | Endpoint Format | Example |
|---------|----------------|---------|
| MinIO (local) | `http://hostname:port` | `http://minio.local:9000` |
| MinIO (TLS) | `https://hostname:port` | `https://minio.example.com:9000` |
| Wasabi | `https://s3.region.wasabisys.com` | `https://s3.us-east-1.wasabisys.com` |
| Backblaze B2 | `https://s3.region.backblazeb2.com` | `https://s3.us-west-002.backblazeb2.com` |
| DigitalOcean Spaces | `https://region.digitaloceanspaces.com` | `https://nyc3.digitaloceanspaces.com` |
| Linode Object Storage | `https://region.linodeobjects.com` | `https://us-east-1.linodeobjects.com` |

## Migration from Environment Variables

If you were previously using environment variables for S3 configuration:

1. **Add repository with credentials:**
   ```bash
   tl repos add <repo-name>
   # Provide credentials and endpoint when prompted
   ```

2. **Remove environment variables:**
   ```bash
   # Remove from ~/.bashrc or ~/.zshrc:
   # export AWS_S3_ENDPOINT=...
   # export AWS_ACCESS_KEY_ID=...
   # export AWS_SECRET_ACCESS_KEY=...
   ```

3. **Verify it works:**
   ```bash
   tl repos list
   tl snapshots list -r <repo-name>
   ```

## Support

For issues specific to S3-compatible services:

1. Check service documentation for correct endpoint format
2. Verify credentials have appropriate permissions
3. Test connection with service's native CLI tools
4. Review TimeLocker logs for detailed error messages

For MinIO-specific setup, see [MINIO_SETUP_SUMMARY.md](MINIO_SETUP_SUMMARY.md).

