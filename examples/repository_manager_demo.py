#!/usr/bin/env python3
"""
Repository Manager Demo

This script demonstrates the core functionality of the Repository Manager
including CRUD operations, state management, and existing repository handling.
"""

import asyncio
import logging
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from TimeLocker.interfaces.repository_management_models import (
    RepositoryConfig, BackupEngine, RepositoryType, RepositoryStatus,
    RepositoryCreationOptions, ExistingRepositoryInfo
)
from TimeLocker.services.repository_manager import RepositoryManager
from TimeLocker.services.repository_state_manager import RepositoryStateManager
from TimeLocker.interfaces.integration_data_models import ServiceContext

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_repository_manager():
    """Demonstrate Repository Manager functionality"""
    
    print("=== Repository Manager Demo ===\n")
    
    # Create repository manager
    manager = RepositoryManager()
    
    # Create mock service context
    from unittest.mock import Mock
    
    mock_config_manager = Mock()
    mock_event_bus = Mock()
    mock_service_registry = Mock()
    
    context = ServiceContext(
        config_manager=mock_config_manager,
        event_bus=mock_event_bus,
        service_registry=mock_service_registry,
        operation_id="demo-001"
    )
    
    # Initialize manager
    print("1. Initializing Repository Manager...")
    success = manager.initialize(context)
    print(f"   Initialization: {'Success' if success else 'Failed'}")
    print(f"   Health Check: {'Healthy' if manager.health_check() else 'Unhealthy'}")
    print(f"   Capabilities: {', '.join(manager.get_capabilities())}")
    print()
    
    # Create repository configurations
    print("2. Creating Repository Configurations...")
    
    local_config = RepositoryConfig(
        name="local-backup",
        uri="file:///tmp/local-backup-repo",
        engine=BackupEngine.RESTIC,
        type=RepositoryType.LOCAL,
        description="Local filesystem backup repository"
    )
    
    s3_config = RepositoryConfig(
        name="cloud-backup",
        uri="s3:s3.amazonaws.com/my-backup-bucket/repo",
        engine=BackupEngine.RESTIC,
        type=RepositoryType.S3,
        description="S3 cloud backup repository"
    )
    
    print(f"   Local Repository: {local_config.name} -> {local_config.uri}")
    print(f"   Cloud Repository: {s3_config.name} -> {s3_config.uri}")
    print()
    
    # Demonstrate existing repository detection
    print("3. Testing Existing Repository Detection...")
    
    existing_info = await manager.detect_existing_repository(local_config.uri)
    if existing_info:
        print(f"   Found existing repository at {existing_info.uri}")
        print(f"   Engine: {existing_info.engine_type.value}")
        print(f"   Requires credentials: {existing_info.requires_credentials}")
    else:
        print(f"   No existing repository found at {local_config.uri}")
    print()
    
    # Demonstrate repository creation (simulated)
    print("4. Simulating Repository Creation...")
    
    try:
        # This would normally create a real repository
        # For demo purposes, we'll just show the configuration
        print(f"   Would create repository: {local_config.name}")
        print(f"   Configuration: {local_config.to_dict()}")
        
        # Manually add to manager for demo
        from TimeLocker.interfaces.repository_management_models import Repository
        repository = Repository(
            config=local_config,
            status=RepositoryStatus.ACTIVE
        )
        manager._repositories[local_config.name] = repository
        
        print(f"   Repository created successfully: {repository.name}")
        print(f"   Status: {repository.status.value}")
        
    except Exception as e:
        print(f"   Repository creation failed: {e}")
    print()
    
    # Demonstrate repository listing
    print("5. Listing Repositories...")
    
    repositories = await manager.list_repositories()
    print(f"   Total repositories: {len(repositories)}")
    
    for repo in repositories:
        print(f"   - {repo.name}: {repo.status.value} ({repo.config.type.value})")
    print()
    
    # Demonstrate state management
    print("6. Testing State Management...")
    
    if repositories:
        repo = repositories[0]
        print(f"   Current state: {repo.status.value}")
        
        # Get state history
        history = manager.get_state_history(repo.name)
        print(f"   State history entries: {len(history)}")
        
        for transition in history[-3:]:  # Show last 3 transitions
            print(f"   - {transition.from_state.value} -> {transition.to_state.value} "
                  f"at {transition.timestamp.strftime('%H:%M:%S')}")
    print()
    
    # Demonstrate repository statistics
    print("7. Repository Statistics...")
    
    stats = manager.get_repository_statistics()
    print(f"   Total repositories: {stats['total_repositories']}")
    print(f"   Status distribution: {stats['status_distribution']}")
    print(f"   Performance thresholds: {stats['performance_thresholds']}")
    print()
    
    # Demonstrate repository updates
    print("8. Testing Repository Updates...")
    
    if repositories:
        repo_name = repositories[0].name
        try:
            # Mock the validation and backup methods for demo
            manager._validate_configuration = lambda config: type('Result', (), {'is_valid': True, 'errors': []})()
            manager._backup_configuration = lambda name: f"backup-{name}-{datetime.now().isoformat()}"
            manager._save_repositories = lambda: None
            
            updated_repo = await manager.update_repository(
                repo_name, 
                {'description': 'Updated description for demo'}
            )
            print(f"   Updated repository: {updated_repo.name}")
            print(f"   New description: {updated_repo.config.description}")
            
        except Exception as e:
            print(f"   Update failed: {e}")
    print()
    
    # Demonstrate default repository management
    print("9. Testing Default Repository Management...")
    
    if repositories:
        repo_name = repositories[0].name
        try:
            success = await manager.set_default_repository(repo_name)
            print(f"   Set default repository: {repo_name} ({'Success' if success else 'Failed'})")
            
            # Check if it's marked as default
            repo = await manager.get_repository(repo_name)
            print(f"   Is default: {repo.config.is_default}")
            
        except Exception as e:
            print(f"   Default repository setting failed: {e}")
    print()
    
    print("=== Demo Complete ===")


def demo_state_manager():
    """Demonstrate Repository State Manager functionality"""
    
    print("\n=== Repository State Manager Demo ===\n")
    
    # Create state manager
    state_manager = RepositoryStateManager()
    
    print("1. State Manager Capabilities...")
    print("   - Controlled state transitions")
    print("   - Audit logging with correlation IDs")
    print("   - State history tracking")
    print("   - Transition rule validation")
    print()
    
    # Create test repository
    config = RepositoryConfig(
        name="state-test-repo",
        uri="file:///tmp/state-test",
        engine=BackupEngine.RESTIC,
        type=RepositoryType.LOCAL
    )
    
    from TimeLocker.interfaces.repository_management_models import Repository
    repository = Repository(config=config, status=RepositoryStatus.INACTIVE)
    
    print("2. Repository State Transitions...")
    print(f"   Initial state: {repository.status.value}")
    
    # Demonstrate valid transitions
    async def test_transitions():
        # INACTIVE -> VALIDATING
        await state_manager.transition_state(repository, RepositoryStatus.VALIDATING)
        print(f"   After validation start: {repository.status.value}")
        
        # VALIDATING -> ACTIVE (simulate successful validation)
        from TimeLocker.interfaces.repository_management_models import ValidationResult, ConnectivityStatus, IntegrityStatus
        repository.validation_result = ValidationResult(
            success=True,
            timestamp=datetime.utcnow(),
            connectivity_status=ConnectivityStatus.CONNECTED,
            integrity_status=IntegrityStatus.VALID
        )
        
        await state_manager.transition_state(repository, RepositoryStatus.ACTIVE)
        print(f"   After successful validation: {repository.status.value}")
        
        # Show state history
        history = state_manager.get_state_history(repository.name)
        print(f"\n   State history ({len(history)} transitions):")
        for transition in history:
            print(f"   - {transition.from_state.value} -> {transition.to_state.value} "
                  f"(ID: {transition.correlation_id[:8]})")
    
    asyncio.run(test_transitions())
    
    print("\n3. State Manager Statistics...")
    stats = state_manager.get_statistics()
    print(f"   Total transitions: {stats['total_transitions']}")
    print(f"   Repositories with history: {stats['repositories_with_history']}")
    print(f"   Transition rules: {stats['transition_rules_count']}")
    
    print("\n=== State Manager Demo Complete ===")


if __name__ == "__main__":
    # Run the demos
    asyncio.run(demo_repository_manager())
    demo_state_manager()