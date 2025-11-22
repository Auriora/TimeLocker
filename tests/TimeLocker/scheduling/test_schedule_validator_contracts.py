import asyncio
from datetime import datetime, time
from typing import Any, List, Optional

import pytest

from TimeLocker.scheduling.platform_adapter import PlatformAdapter
from TimeLocker.scheduling.schedule_testing import ScheduleTester
from TimeLocker.scheduling.schedule_validator import ScheduleValidator
from TimeLocker.scheduling.scheduling_models import (
    CalendarConfig,
    ScheduleConfig,
    SchedulePattern,
    SchedulePatternType,
    ValidationResult,
)
from TimeLocker.scheduling.scheduling_models import PlatformScheduleInfo, PlatformScheduleResult, PlatformScheduleStatus


class FakePlatformAdapter(PlatformAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.validate_called = False
        self.create_called = False
        self.update_called = False
        self.delete_called = False
        self.list_called = False
        self.status_called = False

    async def create_schedule(self, config: ScheduleConfig) -> PlatformScheduleResult:  # pragma: no cover - not used in dry-run
        self.create_called = True
        return PlatformScheduleResult(success=True, platform_id="fake")

    async def update_schedule(self, schedule_id: str, config: ScheduleConfig) -> PlatformScheduleResult:  # pragma: no cover
        self.update_called = True
        return PlatformScheduleResult(success=True, platform_id=schedule_id)

    async def delete_schedule(self, schedule_id: str) -> bool:  # pragma: no cover
        self.delete_called = True
        return True

    async def get_schedule_status(self, schedule_id: str) -> PlatformScheduleStatus:  # pragma: no cover
        self.status_called = True
        return PlatformScheduleStatus(platform_id=schedule_id, is_active=True)

    async def list_schedules(self) -> List[PlatformScheduleInfo]:  # pragma: no cover
        self.list_called = True
        return []

    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        self.validate_called = True
        result = ValidationResult(is_valid=True)
        if config.schedule_pattern.randomize_delay_minutes > 30:
            result.add_error("Randomized delay exceeds 30 minute platform cap")
        return result

    def get_platform_name(self) -> str:
        return "fake-platform"


class FakePolicy:
    def __init__(self, data_refs: List[str], repos: List[str]) -> None:
        self.data_selection_refs = data_refs
        self.target_repositories = repos


class FakePolicyClient:
    def __init__(self, policy: FakePolicy):
        self.policy = policy

    def validate_policy_for_scheduling(self, policy_id: str):
        return True, []

    def get_backup_policy(self, policy_id: str):
        return self.policy


class FakeDataSelectionClient:
    def __init__(self, template: Any):
        self.template = template

    def get_selection_template(self, template_id: str):
        return self.template

    def validate_selection_for_scheduling(self, template_id: str):
        return True, []


class FakeRepositoryClient:
    def get_repository_config(self, repo_id: str):
        return {"id": repo_id}

    def validate_repository_for_scheduling(self, repo_id: str):
        return True, []


def _make_config(tmp_path, randomize_delay: int = 5) -> ScheduleConfig:
    pattern = SchedulePattern(
            pattern_type=SchedulePatternType.CRON,
            cron_expression="*/5 * * * *",
            randomize_delay_minutes=randomize_delay,
    )
    window = tmp_path / "include"
    window.mkdir()
    template = type("Template", (), {"include_paths": [str(window)]})

    config = ScheduleConfig(
            schedule_id="sched-1",
            name="nightly-policy-run",
            description="test schedule",
            policy_id="policy-1",
            schedule_pattern=pattern,
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by="tester",
    )
    return config, template


def test_platform_adapter_errors_are_propagated(tmp_path) -> None:
    config, template = _make_config(tmp_path, randomize_delay=45)  # Above 30 minute cap to trigger adapter error
    adapter = FakePlatformAdapter()
    policy = FakePolicy(data_refs=["sel-1"], repos=["repo-1"])

    validator = ScheduleValidator(
            platform_adapter=adapter,
            policy_client=FakePolicyClient(policy),
            data_selection_client=FakeDataSelectionClient(template),
            repository_client=FakeRepositoryClient(),
    )

    result = validator.validate_schedule_configuration(config, comprehensive=True)

    assert adapter.validate_called is True
    assert result.is_valid is False
    assert any("Randomized delay exceeds 30 minute platform cap" in err for err in result.errors)


@pytest.mark.asyncio
async def test_dry_run_path_does_not_touch_platform_scheduler(tmp_path) -> None:
    config, template = _make_config(tmp_path, randomize_delay=10)
    adapter = FakePlatformAdapter()
    policy = FakePolicy(data_refs=["sel-1"], repos=["repo-1"])

    tester = ScheduleTester(
            platform_adapter=adapter,
            policy_client=FakePolicyClient(policy),
            data_selection_client=FakeDataSelectionClient(template),
            repository_client=FakeRepositoryClient(),
    )

    result = await tester.test_schedule_execution(config, dry_run=True)

    assert adapter.validate_called is True
    assert adapter.create_called is False
    assert result.success is True
    assert result.simulation_result is not None
    assert "policy_retrieval" in result.simulation_result["steps_completed"]
