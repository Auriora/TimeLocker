"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TypedDict, TypeAlias

from ..interfaces.data_models import BackupJob, ToolConfiguration
from .parallel_execution_optimizer import ParallelExecutionOptimizer

logger = logging.getLogger(__name__)

ToolOptionValue: TypeAlias = (
    bool | int | float | str | list["ToolOptionValue"] | dict[str, "ToolOptionValue"]
)
ToolOptionMap: TypeAlias = dict[str, ToolOptionValue]


class Feature(Enum):
    """Backup tool features that may be supported"""

    # Core features
    INCREMENTAL_BACKUP = "incremental_backup"
    FULL_BACKUP = "full_backup"
    DIFFERENTIAL_BACKUP = "differential_backup"

    # Data integrity
    INTEGRITY_VERIFICATION = "integrity_verification"
    CHECKSUM_VALIDATION = "checksum_validation"
    DATA_DEDUPLICATION = "data_deduplication"

    # Performance
    PARALLEL_PROCESSING = "parallel_processing"
    COMPRESSION = "compression"
    BANDWIDTH_LIMITING = "bandwidth_limiting"

    # Security
    ENCRYPTION = "encryption"
    ENCRYPTION_AT_REST = "encryption_at_rest"
    ENCRYPTION_IN_TRANSIT = "encryption_in_transit"

    # Selection
    INCLUDE_PATTERNS = "include_patterns"
    EXCLUDE_PATTERNS = "exclude_patterns"
    REGEX_PATTERNS = "regex_patterns"

    # Snapshot management
    SNAPSHOT_TAGGING = "snapshot_tagging"
    SNAPSHOT_METADATA = "snapshot_metadata"
    SNAPSHOT_COMPARISON = "snapshot_comparison"

    # Repository
    REPOSITORY_LOCKING = "repository_locking"
    REPOSITORY_VERIFICATION = "repository_verification"
    MULTI_REPOSITORY = "multi_repository"

    # Advanced
    RESUME_SUPPORT = "resume_support"
    PROGRESS_REPORTING = "progress_reporting"
    DRY_RUN = "dry_run"


class JobCompatibilityResult(TypedDict):
    """Structured result for backup-tool and job compatibility checks."""

    is_compatible: bool
    warnings: list[str]
    missing_features: list[Feature]
    recommendations: list[str]


class ParallelExecutionReport(TypedDict):
    """Structured report returned for a monitored parallel operation."""

    operation_id: str
    configured_parallelism: int
    actual_parallelism: int
    parallel_efficiency: float
    resource_usage: dict[str, float]
    bottlenecks: list[str]
    degradation_events: int
    efficiency_rating: str


@dataclass
class Limitation:
    """
    Represents a limitation of a backup tool.

    Attributes:
        feature: The feature that is limited
        description: Description of the limitation
        workaround: Optional workaround description
        severity: Severity level (low, medium, high)
    """

    feature: str
    description: str
    workaround: str | None = None
    severity: str = "medium"


@dataclass
class PerformanceProfile:
    """
    Performance characteristics of a backup tool.

    Attributes:
        typical_throughput_mbps: Typical throughput in MB/s
        cpu_usage: Typical CPU usage (low, medium, high)
        memory_usage: Typical memory usage (low, medium, high)
        parallel_efficiency: Efficiency of parallel operations (0.0-1.0)
        compression_overhead: Compression performance impact (low, medium, high)
        supports_resume: Whether tool supports resuming interrupted operations
    """

    typical_throughput_mbps: float | None = None
    cpu_usage: str = "medium"
    memory_usage: str = "medium"
    parallel_efficiency: float = 0.7
    compression_overhead: str = "medium"
    supports_resume: bool = False


@dataclass
class ToolCapabilities:
    """
    Comprehensive capability information for a backup tool.

    Attributes:
        tool_name: Name of the backup tool
        version: Tool version string
        native_features: Features natively supported by the tool
        wrapper_features: Features provided by plugin wrapper
        limitations: List of known limitations
        performance_characteristics: Performance profile
        recommended_use_cases: List of recommended use cases
        configuration_options: Available configuration options
    """

    tool_name: str
    version: str
    native_features: set[Feature] = field(default_factory=set)
    wrapper_features: set[Feature] = field(default_factory=set)
    limitations: list[Limitation] = field(default_factory=list)
    performance_characteristics: PerformanceProfile = field(
        default_factory=PerformanceProfile
    )
    recommended_use_cases: list[str] = field(default_factory=list)
    configuration_options: ToolOptionMap = field(default_factory=dict)

    @property
    def all_features(self) -> set[Feature]:
        """Get all available features (native + wrapper)"""
        return self.native_features | self.wrapper_features

    def has_feature(self, feature: Feature) -> bool:
        """Check if feature is available (native or wrapper)"""
        return feature in self.all_features

    def is_native_feature(self, feature: Feature) -> bool:
        """Check if feature is natively supported"""
        return feature in self.native_features

    def is_wrapper_feature(self, feature: Feature) -> bool:
        """Check if feature is provided by wrapper"""
        return feature in self.wrapper_features


@dataclass
class ToolInfo:
    """
    Summary information about a supported backup tool.

    Attributes:
        tool_name: Name of the backup tool
        version: Tool version
        is_available: Whether tool is installed and available
        feature_count: Number of supported features
        native_feature_count: Number of natively supported features
        wrapper_feature_count: Number of wrapper-provided features
    """

    tool_name: str
    version: str | None
    is_available: bool
    feature_count: int = 0
    native_feature_count: int = 0
    wrapper_feature_count: int = 0


class ToolManager:
    """
    Manages backup tool integration and capabilities.

    This class provides:
    - Tool capability detection and reporting
    - Tool configuration and optimization
    - Plugin wrapper coordination
    - Performance optimization recommendations
    """

    def __init__(self, parallel_optimizer: ParallelExecutionOptimizer | None = None):
        """
        Initialize tool manager.

        Args:
            parallel_optimizer: Optional parallel execution optimizer
        """
        self._capabilities_cache: dict[str, ToolCapabilities] = {}
        self._tool_detectors: dict[str, Callable[[], ToolCapabilities]] = {
            "restic": self._detect_restic_capabilities,
            "borg": self._detect_borg_capabilities,
            "duplicity": self._detect_duplicity_capabilities,
        }
        self._parallel_optimizer: ParallelExecutionOptimizer = (
            parallel_optimizer or ParallelExecutionOptimizer()
        )
        logger.debug("ToolManager initialized with parallel execution optimizer")

    def get_tool_capabilities(self, tool_type: str) -> ToolCapabilities:
        """
        Get comprehensive capability information for a backup tool.

        Args:
            tool_type: Type of backup tool (e.g., 'restic', 'borg')

        Returns:
            ToolCapabilities with complete capability information

        Raises:
            ValueError: If tool type is not supported
        """
        logger.debug(f"Getting capabilities for tool: {tool_type}")

        # Check cache first
        if tool_type in self._capabilities_cache:
            logger.debug(f"Returning cached capabilities for {tool_type}")
            return self._capabilities_cache[tool_type]

        # Detect capabilities
        if tool_type not in self._tool_detectors:
            raise ValueError(f"Unsupported tool type: {tool_type}")

        detector = self._tool_detectors[tool_type]
        capabilities = detector()

        # Cache the result
        self._capabilities_cache[tool_type] = capabilities

        logger.info(f"Detected capabilities for {tool_type} v{capabilities.version}: {len(capabilities.native_features)} native, {len(capabilities.wrapper_features)} wrapper features")

        return capabilities

    def configure_tool_for_job(
        self, tool_type: str, job: BackupJob
    ) -> ToolConfiguration:
        """
        Configure backup tool for optimal job execution.

        This method analyzes the job requirements and tool capabilities
        to create an optimized tool configuration.

        Args:
            tool_type: Type of backup tool
            job: Backup job to configure for

        Returns:
            ToolConfiguration optimized for the job
        """
        logger.debug(f"Configuring {tool_type} for job {job.config.job_id}")

        # Get tool capabilities
        capabilities = self.get_tool_capabilities(tool_type)

        # Start with existing configuration or create new one
        config = job.tool_configuration or ToolConfiguration(tool_type=tool_type)

        # Optimize parallel operations using parallel execution optimizer
        if capabilities.has_feature(Feature.PARALLEL_PROCESSING):
            # Get system resources
            system_resources = self._parallel_optimizer.get_system_resources()

            # Calculate optimal parallelism
            parallel_config = self._parallel_optimizer.calculate_optimal_parallelism(
                capabilities, job, system_resources
            )

            config.parallel_operations = parallel_config.parallel_operations

            # Store optimization details in metadata
            config.tool_specific_options["parallel_optimization"] = {
                "configured_parallelism": parallel_config.parallel_operations,
                "max_parallelism": parallel_config.max_parallel_operations,
                "resource_constraint": parallel_config.resource_constraint_level.value,
                "optimization_reason": parallel_config.optimization_reason,
                "degradation_applied": parallel_config.degradation_applied,
                "recommendations": parallel_config.recommendations,
            }

            logger.info(
                f"Optimized parallel operations to {config.parallel_operations}: {parallel_config.optimization_reason}"
            )

            # Log recommendations
            for recommendation in parallel_config.recommendations:
                logger.info(f"Recommendation: {recommendation}")
        else:
            config.parallel_operations = 1
            logger.debug("Tool does not support parallel operations")

        # Configure compression
        if capabilities.has_feature(Feature.COMPRESSION):
            config.compression_level = self._determine_compression_level(
                capabilities, job
            )
            logger.debug(f"Set compression level to {config.compression_level}")

        # Configure encryption
        if capabilities.has_feature(Feature.ENCRYPTION):
            config.encryption_enabled = True
            logger.debug("Encryption enabled")
        else:
            config.encryption_enabled = False
            logger.warning(f"{tool_type} does not support encryption")

        # Configure integrity checking
        if capabilities.has_feature(Feature.INTEGRITY_VERIFICATION):
            config.integrity_check_enabled = True
            logger.debug("Integrity checking enabled")
        else:
            config.integrity_check_enabled = False
            if capabilities.is_wrapper_feature(Feature.INTEGRITY_VERIFICATION):
                logger.info("Integrity checking will be provided by wrapper")

        # Add tool-specific optimizations
        config.tool_specific_options = self._get_tool_specific_options(
            tool_type, capabilities, job
        )

        logger.info(f"Tool configuration complete for {tool_type}: parallel={config.parallel_operations}, compression={config.compression_level}, encryption={config.encryption_enabled}")

        return config

    def get_supported_tools(self) -> list[ToolInfo]:
        """
        Get list of all supported backup tools with capability summaries.

        Returns:
            List of ToolInfo objects for all supported tools
        """
        logger.debug("Getting list of supported tools")

        tools: list[ToolInfo] = []
        for tool_name in self._tool_detectors.keys():
            try:
                capabilities = self.get_tool_capabilities(tool_name)

                tool_info = ToolInfo(
                    tool_name=tool_name,
                    version=capabilities.version,
                    is_available=True,
                    feature_count=len(capabilities.all_features),
                    native_feature_count=len(capabilities.native_features),
                    wrapper_feature_count=len(capabilities.wrapper_features),
                )
                tools.append(tool_info)

            except Exception as e:
                logger.warning(f"Could not detect {tool_name}: {e}")
                tools.append(
                    ToolInfo(tool_name=tool_name, version=None, is_available=False)
                )

        available_tool_count = sum(1 for tool in tools if tool.is_available)
        logger.info(f"Found {available_tool_count} available tools")
        return tools

    def validate_job_compatibility(
        self, tool_type: str, job: BackupJob
    ) -> JobCompatibilityResult:
        """
        Validate that a job is compatible with the specified tool.

        Args:
            tool_type: Type of backup tool
            job: Backup job to validate

        Returns:
            Dictionary with validation results including:
            - is_compatible: bool
            - warnings: List[str]
            - missing_features: List[Feature]
            - recommendations: List[str]
        """
        logger.debug(
            f"Validating job {job.config.job_id} compatibility with {tool_type}"
        )

        capabilities = self.get_tool_capabilities(tool_type)

        result: JobCompatibilityResult = {
            "is_compatible": True,
            "warnings": [],
            "missing_features": [],
            "recommendations": [],
        }

        # Check required features
        required_features = self._determine_required_features(job)

        for feature in required_features:
            if not capabilities.has_feature(feature):
                result["missing_features"].append(feature)
                result["warnings"].append(
                    f"Feature {feature.value} not available in {tool_type}"
                )

        # Check for limitations that might affect the job
        for limitation in capabilities.limitations:
            if limitation.severity == "high":
                result["warnings"].append(
                    f"High severity limitation: {limitation.description}"
                )
                if limitation.workaround:
                    result["recommendations"].append(limitation.workaround)

        # Add performance recommendations
        if job.config.priority > 5:  # High priority job
            if capabilities.performance_characteristics.parallel_efficiency > 0.8:
                result["recommendations"].append(
                    f"{tool_type} has excellent parallel performance - consider increasing parallel operations"
                )

        result["is_compatible"] = len(result["missing_features"]) == 0

        logger.info(f"Compatibility check complete: compatible={result['is_compatible']}, warnings={len(result['warnings'])}")

        return result

    def _detect_restic_capabilities(self) -> ToolCapabilities:
        """Detect Restic backup tool capabilities"""
        logger.debug("Detecting Restic capabilities")

        # Try to get Restic version
        tool_version = "unknown"
        try:
            result = subprocess.run(
                ["restic", "version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Parse version from output
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if line.startswith("restic "):
                        parts = line.split()
                        if len(parts) >= 2:
                            tool_version = parts[1]
                            break
        except Exception as e:
            logger.warning(f"Could not detect Restic version: {e}")

        # Define Restic native features
        native_features = {
            Feature.INCREMENTAL_BACKUP,
            Feature.FULL_BACKUP,
            Feature.INTEGRITY_VERIFICATION,
            Feature.CHECKSUM_VALIDATION,
            Feature.DATA_DEDUPLICATION,
            Feature.PARALLEL_PROCESSING,
            Feature.COMPRESSION,
            Feature.BANDWIDTH_LIMITING,
            Feature.ENCRYPTION,
            Feature.ENCRYPTION_AT_REST,
            Feature.INCLUDE_PATTERNS,
            Feature.EXCLUDE_PATTERNS,
            Feature.SNAPSHOT_TAGGING,
            Feature.SNAPSHOT_METADATA,
            Feature.SNAPSHOT_COMPARISON,
            Feature.REPOSITORY_LOCKING,
            Feature.REPOSITORY_VERIFICATION,
            Feature.RESUME_SUPPORT,
            Feature.PROGRESS_REPORTING,
            Feature.DRY_RUN,
        }

        # Features provided by wrapper
        wrapper_features = {
            Feature.REGEX_PATTERNS,  # Wrapper can translate regex to Restic patterns
        }

        # Known limitations
        limitations = [
            Limitation(
                feature="multi_repository",
                description="Restic requires separate commands for multiple repositories",
                workaround="Use wrapper to coordinate multi-repository operations",
                severity="low",
            )
        ]

        # Performance profile
        performance = PerformanceProfile(
            typical_throughput_mbps=100.0,
            cpu_usage="medium",
            memory_usage="medium",
            parallel_efficiency=0.85,
            compression_overhead="low",
            supports_resume=True,
        )

        # Recommended use cases
        use_cases = [
            "General purpose backup",
            "Cloud storage backup",
            "Encrypted backup",
            "Deduplication-heavy workloads",
        ]

        # Configuration options
        config_options: ToolOptionMap = {
            "max_parallel_files": 8,
            "compression_levels": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "default_compression": "auto",
            "supports_pack_size": True,
            "supports_read_concurrency": True,
        }

        return ToolCapabilities(
            tool_name="restic",
            version=tool_version,
            native_features=native_features,
            wrapper_features=wrapper_features,
            limitations=limitations,
            performance_characteristics=performance,
            recommended_use_cases=use_cases,
            configuration_options=config_options,
        )

    def _detect_borg_capabilities(self) -> ToolCapabilities:
        """Detect Borg backup tool capabilities"""
        logger.debug("Detecting Borg capabilities")

        # Try to get Borg version
        tool_version = "unknown"
        try:
            result = subprocess.run(
                ["borg", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Parse version from output
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    tool_version = parts[1]
        except Exception as e:
            logger.warning(f"Could not detect Borg version: {e}")

        # Define Borg native features
        native_features = {
            Feature.INCREMENTAL_BACKUP,
            Feature.FULL_BACKUP,
            Feature.INTEGRITY_VERIFICATION,
            Feature.CHECKSUM_VALIDATION,
            Feature.DATA_DEDUPLICATION,
            Feature.COMPRESSION,
            Feature.ENCRYPTION,
            Feature.ENCRYPTION_AT_REST,
            Feature.INCLUDE_PATTERNS,
            Feature.EXCLUDE_PATTERNS,
            Feature.REGEX_PATTERNS,
            Feature.SNAPSHOT_TAGGING,
            Feature.SNAPSHOT_METADATA,
            Feature.REPOSITORY_LOCKING,
            Feature.REPOSITORY_VERIFICATION,
            Feature.PROGRESS_REPORTING,
            Feature.DRY_RUN,
        }

        # Features provided by wrapper
        wrapper_features = {
            Feature.PARALLEL_PROCESSING,  # Wrapper can parallelize Borg operations
            Feature.BANDWIDTH_LIMITING,  # Wrapper can implement bandwidth limiting
        }

        # Known limitations
        limitations = [
            Limitation(
                feature="parallel_processing",
                description="Borg does not natively support parallel file processing",
                workaround="Wrapper provides parallel processing for multiple archives",
                severity="medium",
            ),
            Limitation(
                feature="cloud_storage",
                description="Borg primarily designed for local/SSH storage",
                workaround="Use rclone or similar tools for cloud storage",
                severity="medium",
            ),
        ]

        # Performance profile
        performance = PerformanceProfile(
            typical_throughput_mbps=120.0,
            cpu_usage="medium",
            memory_usage="low",
            parallel_efficiency=0.6,  # Lower due to limited native parallel support
            compression_overhead="low",
            supports_resume=False,
        )

        # Recommended use cases
        use_cases = [
            "Local backup",
            "SSH/SFTP backup",
            "Low memory environments",
            "Deduplication-heavy workloads",
        ]

        # Configuration options
        config_options: ToolOptionMap = {
            "compression_algorithms": ["none", "lz4", "zstd", "zlib", "lzma"],
            "default_compression": "lz4",
            "supports_chunker_params": True,
            "supports_checkpoint_interval": True,
        }

        return ToolCapabilities(
            tool_name="borg",
            version=tool_version,
            native_features=native_features,
            wrapper_features=wrapper_features,
            limitations=limitations,
            performance_characteristics=performance,
            recommended_use_cases=use_cases,
            configuration_options=config_options,
        )

    def _detect_duplicity_capabilities(self) -> ToolCapabilities:
        """Detect Duplicity backup tool capabilities"""
        logger.debug("Detecting Duplicity capabilities")

        # Try to get Duplicity version
        tool_version = "unknown"
        try:
            result = subprocess.run(
                ["duplicity", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Parse version from output
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    tool_version = parts[1]
        except Exception as e:
            logger.warning(f"Could not detect Duplicity version: {e}")

        # Define Duplicity native features
        native_features = {
            Feature.INCREMENTAL_BACKUP,
            Feature.FULL_BACKUP,
            Feature.DIFFERENTIAL_BACKUP,
            Feature.ENCRYPTION,
            Feature.COMPRESSION,
            Feature.INCLUDE_PATTERNS,
            Feature.EXCLUDE_PATTERNS,
            Feature.BANDWIDTH_LIMITING,
            Feature.PROGRESS_REPORTING,
        }

        # Features provided by wrapper
        wrapper_features = {
            Feature.PARALLEL_PROCESSING,
            Feature.INTEGRITY_VERIFICATION,
            Feature.SNAPSHOT_TAGGING,
            Feature.REPOSITORY_LOCKING,
        }

        # Known limitations
        limitations = [
            Limitation(
                feature="deduplication",
                description="Duplicity does not support deduplication",
                workaround="Use Restic or Borg for deduplication needs",
                severity="high",
            ),
            Limitation(
                feature="parallel_processing",
                description="Duplicity does not support parallel operations",
                workaround="Wrapper can parallelize multiple backup sets",
                severity="medium",
            ),
        ]

        # Performance profile
        performance = PerformanceProfile(
            typical_throughput_mbps=80.0,
            cpu_usage="high",
            memory_usage="medium",
            parallel_efficiency=0.5,
            compression_overhead="high",
            supports_resume=False,
        )

        # Recommended use cases
        use_cases = [
            "Cloud storage backup",
            "Traditional incremental backup",
            "GPG encryption requirements",
        ]

        # Configuration options
        config_options: ToolOptionMap = {
            "supports_gpg_encryption": True,
            "supports_full_if_older_than": True,
            "supports_volsize": True,
        }

        return ToolCapabilities(
            tool_name="duplicity",
            version=tool_version,
            native_features=native_features,
            wrapper_features=wrapper_features,
            limitations=limitations,
            performance_characteristics=performance,
            recommended_use_cases=use_cases,
            configuration_options=config_options,
        )

    def _calculate_optimal_parallelism(
        self, capabilities: ToolCapabilities, job: BackupJob
    ) -> int:
        """
        Calculate optimal number of parallel operations.

        Args:
            capabilities: Tool capabilities
            job: Backup job

        Returns:
            Optimal number of parallel operations
        """
        # Start with a base value
        base_parallelism = 4

        # Adjust based on tool efficiency
        efficiency = capabilities.performance_characteristics.parallel_efficiency
        if efficiency > 0.8:
            base_parallelism = 8
        elif efficiency < 0.5:
            base_parallelism = 2

        # Adjust based on job priority
        if job.config.priority > 7:
            base_parallelism = min(base_parallelism * 2, 16)
        elif job.config.priority < 3:
            base_parallelism = max(base_parallelism // 2, 1)

        # Check configuration limits
        max_parallel_raw = capabilities.configuration_options.get(
            "max_parallel_files", 8
        )
        max_parallel = max_parallel_raw if isinstance(max_parallel_raw, int) else 8

        return min(base_parallelism, max_parallel)

    def _determine_compression_level(
        self, capabilities: ToolCapabilities, job: BackupJob
    ) -> int | None:
        """
        Determine optimal compression level.

        Args:
            capabilities: Tool capabilities
            job: Backup job

        Returns:
            Compression level (0-9) or None for auto
        """
        # Check if compression is supported
        if not capabilities.has_feature(Feature.COMPRESSION):
            return None

        # Get compression overhead
        overhead = capabilities.performance_characteristics.compression_overhead

        # High priority jobs use lower compression
        if job.config.priority > 7:
            if overhead == "high":
                return 1  # Minimal compression
            else:
                return 3  # Light compression

        # Normal priority jobs use balanced compression
        if overhead == "low":
            return 6  # Good compression with low overhead
        else:
            return 4  # Balanced compression

    def _get_tool_specific_options(
        self, tool_type: str, capabilities: ToolCapabilities, _job: BackupJob
    ) -> ToolOptionMap:
        """
        Get tool-specific configuration options.

        Args:
            tool_type: Type of backup tool
            capabilities: Tool capabilities
            job: Backup job

        Returns:
            Dictionary of tool-specific options
        """
        options: ToolOptionMap = {}

        if tool_type == "restic":
            options["exclude_caches"] = True
            options["one_file_system"] = False
            if capabilities.configuration_options.get("supports_pack_size"):
                options["pack_size"] = 128  # MB

        elif tool_type == "borg":
            if capabilities.configuration_options.get("supports_checkpoint_interval"):
                options["checkpoint_interval"] = 300  # seconds
            options["compression"] = "lz4"

        elif tool_type == "duplicity":
            if capabilities.configuration_options.get("supports_volsize"):
                options["volsize"] = 200  # MB

        return options

    def _determine_required_features(self, job: BackupJob) -> set[Feature]:
        """
        Determine which features are required for a job.

        Args:
            job: Backup job

        Returns:
            Set of required features
        """
        required = {Feature.FULL_BACKUP}

        # Check if encryption is required
        if job.tool_configuration and job.tool_configuration.encryption_enabled:
            required.add(Feature.ENCRYPTION)

        # Check if integrity checking is required
        if job.tool_configuration and job.tool_configuration.integrity_check_enabled:
            required.add(Feature.INTEGRITY_VERIFICATION)

        # Check if patterns are used
        if job.exclude_patterns or job.include_patterns:
            required.add(Feature.EXCLUDE_PATTERNS)
            required.add(Feature.INCLUDE_PATTERNS)

        # Check if tags are used
        if job.config.tags:
            required.add(Feature.SNAPSHOT_TAGGING)

        return required

    def get_parallel_optimizer(self) -> ParallelExecutionOptimizer:
        """
        Get the parallel execution optimizer.

        Returns:
            ParallelExecutionOptimizer instance
        """
        return self._parallel_optimizer

    def monitor_parallel_execution(
        self, operation_id: str, tool_type: str, configured_parallelism: int
    ) -> None:
        """
        Start monitoring parallel execution for an operation.

        Args:
            operation_id: Unique operation identifier
            tool_type: Type of backup tool
            configured_parallelism: Configured parallelism level
        """
        _ = self._parallel_optimizer.start_execution_monitoring(
            operation_id, configured_parallelism
        )

        logger.debug(f"Started parallel execution monitoring for {operation_id} with {tool_type} at parallelism={configured_parallelism}")

    def update_parallel_execution_metrics(
        self,
        operation_id: str,
        actual_parallelism: int | None = None,
        resource_usage: dict[str, float] | None = None,
        bottleneck: str | None = None,
    ) -> None:
        """
        Update parallel execution metrics during operation.

        Args:
            operation_id: Operation identifier
            actual_parallelism: Actual parallelism achieved
            resource_usage: Current resource usage
            bottleneck: Identified bottleneck
        """
        self._parallel_optimizer.update_execution_metrics(
            operation_id, actual_parallelism, resource_usage, bottleneck
        )

    def handle_parallel_execution_failure(
        self, operation_id: str, current_parallelism: int, failure_reason: str
    ) -> int:
        """
        Handle parallel execution failure with graceful degradation.

        Args:
            operation_id: Operation identifier
            current_parallelism: Current parallelism level
            failure_reason: Reason for failure

        Returns:
            New reduced parallelism level
        """
        new_parallelism = self._parallel_optimizer.apply_graceful_degradation(
            operation_id, current_parallelism, failure_reason
        )

        logger.warning(
            f"Applied graceful degradation for {operation_id}: {current_parallelism} -> {new_parallelism}"
        )

        return new_parallelism

    def get_parallel_execution_report(
        self, operation_id: str
    ) -> ParallelExecutionReport | None:
        """
        Get parallel execution report for an operation.

        Args:
            operation_id: Operation identifier

        Returns:
            Dictionary with execution metrics and analysis
        """
        metrics = self._parallel_optimizer.get_execution_metrics(operation_id)

        if not metrics:
            return None

        return {
            "operation_id": metrics.operation_id,
            "configured_parallelism": metrics.configured_parallelism,
            "actual_parallelism": metrics.actual_parallelism,
            "parallel_efficiency": metrics.parallel_efficiency,
            "resource_usage": metrics.resource_usage,
            "bottlenecks": metrics.bottlenecks,
            "degradation_events": metrics.degradation_events,
            "efficiency_rating": self._rate_parallel_efficiency(
                metrics.parallel_efficiency
            ),
        }

    def _rate_parallel_efficiency(self, efficiency: float) -> str:
        """
        Rate parallel efficiency.

        Args:
            efficiency: Parallel efficiency (0.0-1.0)

        Returns:
            Efficiency rating string
        """
        if efficiency >= 0.9:
            return "excellent"
        elif efficiency >= 0.75:
            return "good"
        elif efficiency >= 0.5:
            return "fair"
        else:
            return "poor"
