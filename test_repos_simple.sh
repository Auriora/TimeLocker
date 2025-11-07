#!/bin/bash
# Simple test of repository commands

echo "=== Testing repos --help ==="
python -m TimeLocker.cli repos --help

echo ""
echo "=== Testing repos list (should show no repositories) ==="
python -m TimeLocker.cli repos list

echo ""
echo "=== Testing repos validate --help ==="
python -m TimeLocker.cli repos validate --help

echo ""
echo "=== Testing repos add --help ==="
python -m TimeLocker.cli repos add --help
