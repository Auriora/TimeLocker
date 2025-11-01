---
title: "User Guide: S3-Compatible Services"
id: "user-guide-s3-compatible"
type: [ guide ]
status: [ approved ]
owner: "Documentation Team"
last_reviewed: "01-11-2025"
tags: [guide, user, s3]
links:
  tooling: []
---

# User Guide: S3-Compatible Services

- **Owner**: Documentation Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: End Users integrating S3-compatible storage

## 1. Purpose

Show how to configure TimeLocker with S3-compatible services such as MinIO, Wasabi, Backblaze B2 (S3 API), and DigitalOcean Spaces using per-repository
credentials.

## 2. Goal

After following this guide you can add repositories pointing to non-AWS S3 endpoints, store credentials securely, and troubleshoot connectivity issues.

## 3. Prerequisites

- TimeLocker CLI installed.
- Credential manager ready (or environment variables for legacy flows).
- Endpoint, bucket, and credential information for your S3-compatible provider.

## 4. Step-by-Step Instructions

### 4.1 Use Correct URI Formats

Always include protocol in URIs:

- ✅ `s3:https://s3.wasabisys.com/my-bucket`
- ✅ `s3:https://minio.lan:9000/my-bucket`
- ❌ `s3:s3.wasabisys.com/my-bucket`
- ❌ `s3:minio.lan/my-bucket`

### 4.2 Configure MinIO

```bash
tl repos add my-minio-repo s3:https://minio.lan:9000/my-bucket
```

When prompted, store password and AWS credentials (key `minioadmin`, secret `minioadmin`, optional region). For self-signed certificates answer `y` to skip TLS
verification.

### 4.3 Configure Wasabi

```bash
tl repos add my-wasabi-repo s3:https://s3.wasabisys.com/my-bucket
```

Provide Wasabi access key, secret, and region (e.g., `us-east-1`).

### 4.4 Configure Backblaze B2 (S3 API)

```bash
tl repos add my-b2-s3-repo s3:https://s3.us-west-002.backblazeb2.com/my-bucket
```

Enter B2 key ID, application key, and region `us-west-002`.

### 4.5 Configure DigitalOcean Spaces

```bash
tl repos add my-do-spaces-repo s3:https://nyc3.digitaloceanspaces.com/my-space
```

Provide Spaces access key, secret key, and region (e.g., `nyc3`).

### 4.6 Quick Start (Generic)

1. Add repository: `tl repos add <name> s3:https://endpoint/bucket`
2. Initialise repository: `tl repos init <name>`
3. Use repository:
   ```bash
   tl targets add my-docs ~/Documents
   tl backup my-docs -r <name>
   tl snapshots list -r <name>
   ```

### 4.7 Update Credentials

```bash
tl repos credentials-set <name>
```

Follow prompts to update access key, secret, region, or endpoint.

### 4.8 Legacy Environment Variables (Optional)

```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_S3_ENDPOINT=https://minio.lan:9000
export AWS_DEFAULT_REGION=us-east-1
```

Per-repository credentials still take precedence.

## 5. Troubleshooting

- **Connection issues**: `curl -I https://your-endpoint:port` to verify endpoint availability.
- **Invalid credentials**: Re-run `tl repos credentials-set` and confirm access key/secret pairs.
- **Bucket missing**: Create the bucket via provider console or CLI before running `tl repos init`.
- **TLS errors**: Use `https://` with valid certificates; for labs use `http://` or skip verification when prompted.
- **AWS SSO interference**: Temporarily `unset AWS_PROFILE`; TimeLocker’s stored credentials take precedence.

## 6. Frequently Asked Questions (FAQ)

- **Do I need to specify an endpoint separately?** No. Include the protocol and host directly in the repository URI.
- **Can I mix AWS S3 and MinIO repositories?** Yes; store unique credentials for each repository to switch seamlessly.
- **How do I rotate credentials?** Run `tl repos credentials-set <name>`; old credentials are overwritten, and audit logs record the change.

# References

- Credential guide: `docs/guides/user/per-repo-credentials.md`
- Repository management: `docs/guides/user/repository-management-guide.md`
- Provider documentation (MinIO, Wasabi, Backblaze B2, DigitalOcean Spaces)
