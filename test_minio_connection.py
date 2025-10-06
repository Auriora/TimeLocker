#!/usr/bin/env python3
"""
Test script to verify MinIO connection and credentials.

This script helps diagnose MinIO connectivity issues by testing:
1. Direct boto3 connection to MinIO
2. TimeLocker credential storage and retrieval
3. S3ResticRepository initialization with stored credentials
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_boto3_direct():
    """Test direct boto3 connection to MinIO"""
    print("\n" + "="*70)
    print("TEST 1: Direct boto3 connection to MinIO")
    print("="*70)
    
    try:
        import boto3
        from botocore.client import Config
        
        # MinIO endpoint
        endpoint = input("Enter MinIO endpoint (e.g., http://minio.local:9000): ").strip()
        if not endpoint:
            endpoint = "http://minio.local:9000"
        
        # Get credentials
        access_key = input("Enter MinIO Access Key (or press Enter to skip): ").strip()
        secret_key = input("Enter MinIO Secret Key (or press Enter to skip): ").strip()
        
        if not access_key or not secret_key:
            print("\n⚠️  No credentials provided. Testing anonymous access...")
            s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                config=Config(signature_version='s3v4')
            )
        else:
            print(f"\n✓ Testing with credentials: {access_key[:4]}...{access_key[-4:]}")
            s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4')
            )
        
        # Try to list buckets
        print(f"✓ Connecting to {endpoint}...")
        response = s3_client.list_buckets()
        
        print(f"\n✅ SUCCESS! Connected to MinIO")
        print(f"   Found {len(response['Buckets'])} bucket(s):")
        for bucket in response['Buckets']:
            print(f"   - {bucket['Name']}")
        
        return True, access_key, secret_key, endpoint
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        print("\nPossible issues:")
        print("  1. MinIO is not running or not accessible at the endpoint")
        print("  2. Credentials are incorrect")
        print("  3. Network/firewall blocking connection")
        print("  4. AWS SSO configuration interfering (check ~/.aws/config)")
        return False, None, None, None


def test_timelocker_credentials(access_key, secret_key):
    """Test TimeLocker credential storage and retrieval"""
    print("\n" + "="*70)
    print("TEST 2: TimeLocker credential storage")
    print("="*70)
    
    try:
        from TimeLocker.security.credential_manager import CredentialManager
        import tempfile
        import shutil
        
        # Create temporary credential directory
        temp_dir = tempfile.mkdtemp()
        print(f"✓ Using temporary directory: {temp_dir}")
        
        try:
            cred_manager = CredentialManager(config_dir=Path(temp_dir))
            
            # Unlock
            if not cred_manager.auto_unlock():
                cred_manager.unlock("test-password-123")
            
            if cred_manager.is_locked():
                print("❌ Failed to unlock credential manager")
                return False
            
            print("✓ Credential manager unlocked")
            
            # Store credentials
            repo_name = "minio-test"
            s3_creds = {
                "access_key_id": access_key,
                "secret_access_key": secret_key,
            }
            
            cred_manager.store_repository_backend_credentials(repo_name, "s3", s3_creds)
            print(f"✓ Stored credentials for repository '{repo_name}'")
            
            # Retrieve credentials
            retrieved = cred_manager.get_repository_backend_credentials(repo_name, "s3")
            
            if retrieved and retrieved.get("access_key_id") == access_key:
                print(f"✅ SUCCESS! Credentials stored and retrieved correctly")
                return True
            else:
                print(f"❌ FAILED: Retrieved credentials don't match")
                return False
                
        finally:
            shutil.rmtree(temp_dir)
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_s3_repository(access_key, secret_key, endpoint):
    """Test S3ResticRepository with MinIO"""
    print("\n" + "="*70)
    print("TEST 3: S3ResticRepository with MinIO")
    print("="*70)
    
    try:
        from TimeLocker.restic.Repositories.s3 import S3ResticRepository
        
        # Parse endpoint to get host
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        host = parsed.netloc or parsed.path
        
        # Create S3 repository
        bucket = input("\nEnter bucket name to test (e.g., timelock-test): ").strip()
        if not bucket:
            bucket = "timelock-test"
        
        location = f"s3:{host}/{bucket}"
        print(f"\n✓ Creating repository with location: {location}")
        
        # Set MinIO endpoint in environment
        os.environ['AWS_S3_ENDPOINT'] = endpoint
        print(f"✓ Set AWS_S3_ENDPOINT={endpoint}")
        
        repo = S3ResticRepository(
            location=location,
            password="test-password-123",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        
        print("✓ S3ResticRepository created")
        
        # Get backend environment
        env = repo.backend_env()
        print(f"✓ Backend environment configured:")
        print(f"   AWS_ACCESS_KEY_ID: {env.get('AWS_ACCESS_KEY_ID', 'NOT SET')[:4]}...")
        print(f"   AWS_SECRET_ACCESS_KEY: {'***' if env.get('AWS_SECRET_ACCESS_KEY') else 'NOT SET'}")
        print(f"   AWS_S3_ENDPOINT: {os.environ.get('AWS_S3_ENDPOINT', 'NOT SET')}")
        
        print(f"\n✅ SUCCESS! S3ResticRepository configured correctly")
        print(f"\nTo use with TimeLocker, ensure:")
        print(f"  1. Set environment variable: export AWS_S3_ENDPOINT={endpoint}")
        print(f"  2. Use URI format: s3:{host}/{bucket}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("MinIO Connection Test for TimeLocker")
    print("="*70)
    print("\nThis script will test your MinIO setup in 3 stages:")
    print("  1. Direct boto3 connection")
    print("  2. TimeLocker credential storage")
    print("  3. S3ResticRepository initialization")
    print("\n" + "="*70)
    
    # Test 1: Direct connection
    success, access_key, secret_key, endpoint = test_boto3_direct()
    if not success:
        print("\n⚠️  Cannot proceed without successful MinIO connection")
        return 1
    
    # Test 2: Credential storage (if credentials provided)
    if access_key and secret_key:
        if not test_timelocker_credentials(access_key, secret_key):
            print("\n⚠️  Credential storage test failed")
            return 1
        
        # Test 3: S3 Repository
        if not test_s3_repository(access_key, secret_key, endpoint):
            print("\n⚠️  S3 Repository test failed")
            return 1
    else:
        print("\n⚠️  Skipping credential tests (no credentials provided)")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("\nYour MinIO setup is working correctly with TimeLocker.")
    print("\nNext steps:")
    print(f"  1. Set environment: export AWS_S3_ENDPOINT={endpoint}")
    print("  2. Add repository: tl repos add")
    print("  3. Initialize: tl repos init <repo-name>")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

