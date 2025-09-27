#!/bin/bash
# Script to run restic configuration extraction with proper permissions

set -e

echo "🔧 Restic Configuration Extraction for TimeLocker"
echo "=================================================="

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script needs to be run with sudo to access restic user files"
    echo "Usage: sudo ./scripts/run_extraction.sh"
    exit 1
fi

# Set up paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
EXTRACTION_SCRIPT="$SCRIPT_DIR/extract_restic_config.py"
OUTPUT_DIR="$PROJECT_DIR/extracted_configs"
OUTPUT_FILE="$OUTPUT_DIR/restic_config.json"
BACKUP_DIR="/tmp/restic_config_backup_$(date +%Y%m%d_%H%M%S)"

echo "📁 Project directory: $PROJECT_DIR"
echo "📄 Extraction script: $EXTRACTION_SCRIPT"
echo "💾 Output file: $OUTPUT_FILE"
echo "🔒 Backup directory: $BACKUP_DIR"
echo

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check if required files exist
echo "🔍 Checking for required files..."
if [[ ! -f "/var/restic/.resticrc" ]]; then
    echo "❌ /var/restic/.resticrc not found"
    exit 1
fi

if [[ ! -f "/var/restic/.config/npbackup/npbackup.conf" ]]; then
    echo "❌ /var/restic/.config/npbackup/npbackup.conf not found"
    exit 1
fi

echo "✅ Required configuration files found"
echo

# Install required Python packages if needed
echo "📦 Checking Python dependencies..."
python3 -c "import yaml" 2>/dev/null || {
    echo "Installing PyYAML..."
    pip3 install PyYAML
}

# Run the extraction
echo "🚀 Running configuration extraction..."
python3 "$EXTRACTION_SCRIPT" --output "$OUTPUT_FILE" --backup-dir "$BACKUP_DIR"

# Check if extraction was successful
if [[ $? -eq 0 && -f "$OUTPUT_FILE" ]]; then
    echo
    echo "✅ Extraction completed successfully!"
    echo
    echo "📊 Configuration Summary:"
    echo "========================"
    
    # Display summary of extracted configuration
    python3 -c "
import json
import sys

try:
    with open('$OUTPUT_FILE', 'r') as f:
        config = json.load(f)
    
    print(f'🗂️  Repositories: {len(config.get(\"repositories\", {}))}')
    print(f'📂 Backup targets: {len(config.get(\"backup_targets\", {}))}')
    
    if 'repositories' in config:
        for name, repo in config['repositories'].items():
            print(f'   📍 {name}: {repo.get(\"uri\", \"N/A\")}')
    
    if 'backup_targets' in config:
        for name, target in config['backup_targets'].items():
            paths = target.get('paths', [])
            print(f'   📁 {name}: {len(paths)} paths')
    
    if 'extraction_metadata' in config:
        meta = config['extraction_metadata']
        print(f'⏰ Extracted at: {meta.get(\"extracted_at\", \"N/A\")}')
        print(f'📅 Original cron: {meta.get(\"original_cron_schedule\", \"N/A\")}')
    
except Exception as e:
    print(f'Error reading config: {e}')
    sys.exit(1)
"
    
    echo
    echo "📋 Next Steps:"
    echo "=============="
    echo "1. Review the configuration file: $OUTPUT_FILE"
    echo "2. Test repository connection with extracted credentials"
    echo "3. Import configuration into TimeLocker"
    echo "4. Verify backup functionality"
    echo
    echo "⚠️  Important Notes:"
    echo "- Original configurations backed up to: $BACKUP_DIR"
    echo "- The extracted config contains sensitive credentials"
    echo "- Consider the existing cron job scheduling when setting up TimeLocker"
    echo
    
    # Set proper permissions on output file
    chmod 600 "$OUTPUT_FILE"
    echo "🔒 Set secure permissions (600) on configuration file"
    
else
    echo "❌ Extraction failed!"
    exit 1
fi
