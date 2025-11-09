# TimeLocker Examples

This directory contains example scripts demonstrating various TimeLocker features and capabilities.

## Backup Operations Examples

### Core Backup Operations
- `backup_operations_demo.py` - Basic backup operations with file selection
- `backup_orchestration_demo.py` - **NEW** Complete backup orchestration workflow
- `backup_tool_configurations_demo.py` - **NEW** Different backup tool configurations and comparisons
- `enhanced_backup_operations_demo.py` - Advanced backup operations features
- `integrated_backup_example.py` - Integrated backup workflow example

### Job Execution
- `backup_job_execution_demo.py` - Backup job execution with orchestration
- `job_executor_demo.py` - Job executor with retry logic

### Monitoring and Reporting
- `backup_notification_demo.py` - Backup notification system
- `progress_monitoring_demo.py` - Real-time progress monitoring
- `performance_monitoring_demo.py` - Performance metrics collection

### Validation and Optimization
- `integrity_validation_demo.py` - Backup integrity validation
- `parallel_execution_optimization_demo.py` - Parallel execution optimization
- `performance_optimization_demo.py` - Performance optimization strategies
- `service_optimization_demo.py` - Service-level optimization

## Data Selection Examples

- `data_selection_demo.py` - File selection with patterns
- `data_selection_integration_demo.py` - Data selection integration
- `pattern_engine_demo.py` - Pattern matching engine
- `pattern_group_and_preset_demo.py` - Pattern groups and presets
- `precedence_resolver_demo.py` - Selection precedence resolution
- `selection_manager_demo.py` - Selection management
- `selection_testing_demo.py` - Selection testing harness
- `template_manager_demo.py` - Selection templates
- `validation_and_preview_demo.py` - Selection validation and preview

## Policy Management Examples

- `policy_engine_demo.py` - Policy engine functionality
- `policy_integration_demo.py` - Policy system integration
- `policy_manager_demo.py` - Policy management
- `policy_simulator_demo.py` - Policy simulation
- `policy_storage_demo.py` - Policy storage
- `policy_validator_demo.py` - Policy validation

## Repository Management Examples

- `repository_management_demo.py` - Repository management
- `repository_manager_demo.py` - Repository manager
- `enhanced_repository_demo.py` - Enhanced repository features

## Recovery Operations Examples

- `recovery_models_demo.py` - **NEW** Recovery operations data models and core interfaces
- `recovery_operations_demo.py` - Recovery and restore operations

## Security Examples

- `security_integration_demo.py` - Security system integration
- `security_logger_demo.py` - Security logging
- `security_service_demo.py` - Security service features

## Plugin System Examples

- `plugin_system_demo.py` - Plugin system architecture
- `plugin_wrapper_demo.py` - Plugin wrapper implementation
- `tool_manager_demo.py` - Tool management

## Running Examples

All examples are standalone Python scripts that can be run directly:

```bash
# Run a specific example
python examples/backup_orchestration_demo.py

# Or make it executable and run
chmod +x examples/backup_orchestration_demo.py
./examples/backup_orchestration_demo.py
```

## Example Categories

### Getting Started
Start with these examples to understand basic concepts:
1. `backup_operations_demo.py` - Basic backup workflow
2. `data_selection_demo.py` - File selection basics
3. `repository_management_demo.py` - Repository setup

### Advanced Features
Explore advanced capabilities:
1. `backup_orchestration_demo.py` - Complete orchestration
2. `backup_tool_configurations_demo.py` - Tool configuration options
3. `parallel_execution_optimization_demo.py` - Performance optimization

### Integration Examples
See how components work together:
1. `integrated_backup_example.py` - Full integration
2. `policy_integration_demo.py` - Policy integration
3. `data_selection_integration_demo.py` - Selection integration

## Documentation

For detailed documentation, see:
- [Backup Operations API Reference](../docs/reference/backup-operations-api.md)
- [Plugin Wrapper Development Guide](../docs/guides/developer/plugin-wrapper-development.md)
- [Backup Operations Troubleshooting](../docs/guides/user/backup-operations-troubleshooting.md)

## Contributing

When adding new examples:
1. Follow the naming convention: `feature_name_demo.py`
2. Include a docstring explaining what the example demonstrates
3. Make the script executable: `chmod +x examples/your_demo.py`
4. Add it to this README in the appropriate category
5. Ensure it runs standalone without external dependencies where possible
