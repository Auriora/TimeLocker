#!/usr/bin/env python3
"""
Test script to verify the pickle error fix for repository initialization.

This script tests that the repository initialization no longer raises
"cannot pickle '_thread.RLock' object" errors.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from TimeLocker.restic.Repositories.local import LocalResticRepository


def test_repository_initialization():
    """Test that repository initialization works without pickle errors"""
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = os.path.join(temp_dir, "test-repo")
        test_password = "test123"
        
        print(f"Testing repository initialization at: {repo_path}")
        print(f"Using password: {test_password}")
        
        try:
            # Create repository instance
            print("\n1. Creating LocalResticRepository instance...")
            repo = LocalResticRepository(repo_path, password=test_password)
            print("   ✓ Repository instance created")
            
            # Try to initialize the repository
            print("\n2. Initializing repository...")
            result = repo.initialize_repository(test_password)
            
            if result:
                print("   ✓ Repository initialized successfully!")
                print(f"   Repository ID: {repo.repository_id()}")
                
                # Verify it was actually created
                config_file = os.path.join(repo_path, "config")
                if os.path.exists(config_file):
                    print(f"   ✓ Repository config file exists: {config_file}")
                else:
                    print(f"   ✗ Repository config file NOT found: {config_file}")
                    return False
                
                # Try to check if it's initialized
                print("\n3. Checking if repository is initialized...")
                is_init = repo.is_repository_initialized()
                print(f"   Repository initialized: {is_init}")
                
                if is_init:
                    print("\n✓ ALL TESTS PASSED!")
                    return True
                else:
                    print("\n✗ Repository not detected as initialized")
                    return False
            else:
                print("   ✗ Repository initialization returned False")
                return False
                
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            print(f"   Error type: {type(e).__name__}")
            
            # Check if it's the pickle error
            error_str = str(e)
            if "pickle" in error_str.lower() and "rlock" in error_str.lower():
                print("\n✗ PICKLE ERROR STILL PRESENT!")
                print("   The fix did not work correctly.")
            else:
                print("\n   This is a different error (not the pickle issue)")
            
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            return False


def test_error_handling():
    """Test that errors are properly converted to strings"""
    
    print("\n" + "="*60)
    print("Testing error handling with invalid repository...")
    print("="*60)
    
    # Try to initialize in a location that will fail
    invalid_path = "/root/cannot-write-here-test"
    test_password = "test123"
    
    try:
        print(f"\nAttempting to create repository at: {invalid_path}")
        repo = LocalResticRepository(invalid_path, password=test_password)
        result = repo.initialize_repository(test_password)
        print(f"Unexpected success: {result}")
        return False
    except Exception as e:
        error_str = str(e)
        print(f"\n✓ Exception caught as expected")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {error_str}")
        
        # Verify it's a string and doesn't contain pickle references
        if "pickle" in error_str.lower() and "rlock" in error_str.lower():
            print("\n✗ PICKLE ERROR IN EXCEPTION!")
            return False
        else:
            print("\n✓ Error properly converted to string (no pickle issues)")
            return True


if __name__ == "__main__":
    print("="*60)
    print("Repository Initialization Pickle Error Fix Test")
    print("="*60)
    
    # Test 1: Normal initialization
    test1_passed = test_repository_initialization()
    
    # Test 2: Error handling
    test2_passed = test_error_handling()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Test 1 (Normal initialization): {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Test 2 (Error handling):        {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n✓ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n✗ SOME TESTS FAILED")
        sys.exit(1)
