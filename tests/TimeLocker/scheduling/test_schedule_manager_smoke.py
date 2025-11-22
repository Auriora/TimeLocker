import asyncio
from datetime import datetime
from typing import Any, Callable, List, Optional

import pytest

from TimeLocker.scheduling.schedule_manager import ScheduleManager
from TimeLocker.scheduling.scheduling_configuration import SchedulingConfiguration
from TimeLocker.scheduling.scheduling_models import (
    ScheduleConfig,
    SchedulePattern,
    SchedulePatternType,
    ValidationResult,
)
from TimeLocker.scheduling.platform_adapter import PlatformAdapter
from TimeLocker.scheduling.schedule_validator import ScheduleValidator
from TimeLocker.scheduling.schedule_testing import ScheduleTester


class FakePlatformAdapter(PlatformAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.validate_called = False
        self.create_called = False

    async def create_schedule(self, config: ScheduleConfig):
        self.create_called = True
        return None  # pragma: no cover

    async def update_schedule(self, schedule_id: str, config: ScheduleConfig):
        return None  # pragma: no cover

    async def delete_schedule(self, schedule_id: str):
        return True  # pragma: no cover

    async def get_schedule_status(self, schedule_id: str):
        return None  # pragma: no cover

    async def list_schedules(self):
        return []  # pragma: no cover

    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        self.validate_called = True
        return ValidationResult(is_valid=True)

    def get_platform_name(self) -> str:
        return "fake-platform"


class FakePolicy:
    def __init__(self, data_refs: List[str], repos: List[str]) -> None:
        self.data_selection_refs = data_refs
        self.target_repositories = repos


class FakePolicyClient:
    def __init__(self, policy: FakePolicy) -> None:
        self.policy = policy

    def register_policy_update_callback(self, cb: Callable):
        # No-op for tests
        return None

    def validate_policy_for_scheduling(self, policy_id: str):
        return True, []

    def get_backup_policy(self, policy_id: str):
        return self.policy


class FakeDataSelectionClient:
    def __init__(self, template: Any) -> None:
        self.template = template

    def validate_selection_for_scheduling(self, template_id: str):
        return True, []

    def get_selection_template(self, template_id: str):
        return self.template


class FakeRepositoryClient:
    def validate_repository_for_scheduling(self, repo_id: str):
        return True, []

    def get_repository_config(self, repo_id: str):
        return {"id": repo_id}


@pytest.mark.asyncio
async def test_schedule_manager_dry_run_smoke(tmp_path) -> None:
    include_dir = tmp_path / "include"
    include_dir.mkdir()
    template = type("Template", (), {"include_paths": [str(include_dir)]})

    adapter = FakePlatformAdapter()
    policy = FakePolicy(data_refs=["sel-1"], repos=["repo-1"])
    policy_client = FakePolicyClient(policy)
    selection_client = FakeDataSelectionClient(template)
    repo_client = FakeRepositoryClient()

    manager = ScheduleManager(
            config=SchedulingConfiguration(),
            adapter=adapter,
            config_dir=tmp_path / "scheduling",
    )

    # Inject fakes into manager and rebuild validator/tester to use them
    manager.policy_client = policy_client
    manager.data_selection_client = selection_client
    manager.repository_client = repo_client
    manager.validator = ScheduleValidator(
            platform_adapter=adapter,
            policy_client=policy_client,
            data_selection_client=selection_client,
            repository_client=repo_client,
    )
    manager.tester = ScheduleTester(
            platform_adapter=adapter,
            validator=manager.validator,
            policy_client=policy_client,
            data_selection_client=selection_client,
            repository_client=repo_client,
    )

    pattern = SchedulePattern(
            pattern_type=SchedulePatternType.CRON,
            cron_expression="*/15 * * * *",
            randomize_delay_minutes=5,
    )
    config = ScheduleConfig(
            schedule_id="sched-1",
            name="smoke",
            description="smoke test schedule",
            policy_id="policy-1",
            schedule_pattern=pattern,
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by="tester",
    )

    manager._schedules[config.schedule_id] = config

    result = await manager.test_schedule_execution(config.schedule_id, dry_run=True)

    assert result.success is True
    assert adapter.validate_called is True
    assert adapter.create_called is False  # dry-run should not write to scheduler
    assert "policy_retrieval" in result.simulation_result["steps_completed"]
