# Per-Repository Backend Credentials Implementation Summary

## Overview

Successfully implemented per-repository backend credential storage for TimeLocker, enabling users to configure multiple S3 or B2 repositories with different credentials. This resolves the limitation where all S3 repositories had to share the same AWS credentials from environment variables.

## Implementation Status

✅ **All tasks completed successfully**

### Changes Made

#### 1. Extended RepositoryConfig Schema
**File:** `src/TimeLocker/config/configuration_schema.py`

- Added `has_backend_credentials: bool = False` field to `RepositoryConfig` dataclass
- This flag indicates whether backend credentials are stored in the credential manager (not the credentials themselves)

#### 2. Extended CredentialManager
**File:** `src/TimeLocker/security/credential_manager.py`

Added four new methods for per-repository backend credential management:

- `store_repository_backend_credentials(repository_id, backend_type, credentials_dict)` - Store credentials for a specific repository
- `get_repository_backend_credentials(repository_id, backend_type)` - Retrieve credentials for a specific repository
- `remove_repository_backend_credentials(repository_id, backend_type)` - Remove credentials for a specific repository
- `has_repository_backend_credentials(repository_id, backend_type)` - Check if credentials exist

**Storage Structure:**
```python
credentials["repository_backends"][repository_id][backend_type] = {
    "credentials": {...},
    "created_at": "...",
    "last_accessed": "...",
    "access_count": 0
}
```

#### 3. Updated S3ResticRepository
**File:** `src/TimeLocker/restic/Repositories/s3.py`

- Added `repository_name` parameter to `__init__`
- Implemented credential resolution chain:
  1. Check credential manager for per-repository credentials (if `repository_name` provided)
  2. Fall back to constructor parameters
  3. Fall back to environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`)

#### 4. Updated B2ResticRepository
**File:** `src/TimeLocker/restic/Repositories/b2.py`

- Added `repository_name` and `credential_manager` parameters to `__init__`
- Implemented same credential resolution chain as S3:
  1. Check credential manager for per-repository credentials
  2. Fall back to constructor parameters
  3. Fall back to environment variables (`B2_ACCOUNT_ID`, `B2_ACCOUNT_KEY`)

#### 5. Updated RepositoryFactory
**File:** `src/TimeLocker/services/repository_factory.py`

- Modified `create_repository` to accept and pass through `repository_name` parameter
- Added documentation for the new parameter

#### 6. Updated BackupManager
**File:** `src/TimeLocker/backup_manager.py`

- Updated `from_uri` class method to accept `repository_name` parameter
- Updated `create_repository` method to accept and pass through `repository_name`

#### 7. Enhanced CLI - repos add Command
**File:** `src/TimeLocker/cli.py`

Extended the `repos add` command to:
- Detect S3/B2 repositories from URI
- Prompt user if they want to store backend credentials
- For S3: Prompt for AWS Access Key ID, Secret Access Key, and Region
- For B2: Prompt for B2 Account ID and Account Key
- Store credentials securely in credential manager
- Update repository config with `has_backend_credentials` flag
- Display credential storage status in success message

#### 8. Added New CLI Commands
**File:** `src/TimeLocker/cli.py`

Three new commands for managing backend credentials:

**`tl repos credentials-set <repo-name>`**
- Set or update backend credentials for a repository
- Detects repository type (S3/B2) from URI
- Prompts for appropriate credentials
- Stores credentials in credential manager

**`tl repos credentials-remove <repo-name>`**
- Remove backend credentials for a repository
- Supports `--yes` flag to skip confirmation
- Updates repository config

**`tl repos credentials-show <repo-name>`**
- Show whether backend credentials are configured
- Does not display actual credential values (security)
- Provides helpful guidance if credentials are missing

## Security Features

1. **Encrypted Storage**: All credentials stored using CredentialManager's encryption
2. **No Plain Text**: Credentials never stored in `config.json`
3. **Audit Logging**: All credential operations logged for security monitoring
4. **Access Tracking**: Tracks when credentials are accessed and how many times
5. **Secure Prompts**: Uses `password=True` for all credential input prompts

## Backward Compatibility

✅ **Fully backward compatible**

- Existing repositories without stored credentials continue to work
- Environment variables still work as fallback
- No breaking changes to existing APIs
- Credential resolution chain ensures smooth migration

## Testing

Created comprehensive test suite (`test_per_repo_credentials.py`) covering:

1. ✅ RepositoryConfig schema with `has_backend_credentials` field
2. ✅ CredentialManager per-repository methods
3. ✅ Credential isolation between repositories
4. ✅ S3ResticRepository credential resolution
5. ✅ Fallback to environment variables
6. ✅ RepositoryFactory integration
7. ✅ B2 credentials support

**All tests passed successfully.**

## Usage Examples

### Adding S3 Repository with Credentials

```bash
# Interactive prompts
tl repos add minio1 "s3://minio1.local/bucket1"
# Prompts for:
# - Repository password (optional)
# - AWS credentials (optional)
#   - AWS Access Key ID
#   - AWS Secret Access Key
#   - AWS Region
```

### Managing Credentials

```bash
# Set/update credentials
tl repos credentials-set minio1

# Check credential status
tl repos credentials-show minio1

# Remove credentials
tl repos credentials-remove minio1
```

### Multiple Repositories with Different Credentials

```bash
# Add first MinIO repository
tl repos add minio1 "s3://minio1.local/bucket1"
# Enter credentials for minio1

# Add second MinIO repository with different credentials
tl repos add minio2 "s3://minio2.local/bucket2"
# Enter different credentials for minio2

# Each repository now uses its own credentials
tl backup -r minio1 /data  # Uses minio1 credentials
tl backup -r minio2 /data  # Uses minio2 credentials
```

## Files Modified

1. `src/TimeLocker/config/configuration_schema.py` - Added `has_backend_credentials` field
2. `src/TimeLocker/security/credential_manager.py` - Added per-repository credential methods
3. `src/TimeLocker/restic/Repositories/s3.py` - Updated credential resolution
4. `src/TimeLocker/restic/Repositories/b2.py` - Updated credential resolution
5. `src/TimeLocker/services/repository_factory.py` - Pass repository_name parameter
6. `src/TimeLocker/backup_manager.py` - Accept and pass repository_name parameter
7. `src/TimeLocker/cli.py` - Enhanced repos add command and added credential management commands

## Next Steps

### Recommended Follow-up Tasks

1. **Update Documentation**
   - Add user guide for per-repository credentials
   - Update README with new CLI commands
   - Add examples to documentation

2. **Additional Testing**
   - Integration tests with actual MinIO instance
   - Test credential rotation workflows
   - Test migration from environment variables to stored credentials

3. **Enhancements** (Optional)
   - Add credential validation during storage (test S3/B2 connection)
   - Support for credential rotation/expiration
   - Support for AWS profiles
   - Migration tool to move query-parameter credentials to credential manager

4. **Code Review**
   - Review for SOLID and DRY principles
   - Consider refactoring common credential handling code
   - Add type hints where missing

## Questions Answered

From the original requirements:

1. **Should we validate credentials when storing them?**
   - Not implemented in initial version to avoid requiring network access during configuration
   - Can be added as optional enhancement

2. **Should we support credential rotation/expiration?**
   - Not implemented in initial version
   - Infrastructure is in place (metadata tracking)
   - Can be added as enhancement

3. **Should we support AWS profiles?**
   - Not implemented in initial version
   - Current implementation uses access keys
   - Can be added as enhancement

4. **Should we migrate existing query-parameter credentials?**
   - Not implemented in initial version
   - Can be added as migration tool

## Conclusion

The per-repository backend credentials feature has been successfully implemented with:
- ✅ Full functionality for S3 and B2 repositories
- ✅ Secure encrypted storage
- ✅ User-friendly CLI interface
- ✅ Backward compatibility
- ✅ Comprehensive testing
- ✅ Proper error handling and logging

The implementation follows TimeLocker's existing patterns and conventions, maintains security best practices, and provides a solid foundation for future enhancements.

