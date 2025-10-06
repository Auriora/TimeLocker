#!/bin/bash
# Setup script for MinIO testing environment
# This script verifies access to existing MinIO deployment at minio.local

set -e

echo "🚀 Setting up MinIO testing environment for TimeLocker..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# MinIO configuration (proxied behind Traefik)
MINIO_API_HOST="${MINIO_API_HOST:-minio.local}"
MINIO_CONSOLE_HOST="${MINIO_CONSOLE_HOST:-minio-console.local}"

# Check /etc/hosts for minio.local
echo -e "${YELLOW}🔍 Checking /etc/hosts for minio.local...${NC}"
if grep -q "minio.local" /etc/hosts 2>/dev/null; then
    echo -e "${GREEN}✅ minio.local found in /etc/hosts${NC}"
else
    echo -e "${RED}❌ minio.local not found in /etc/hosts${NC}"
    echo -e "${YELLOW}Please add the following to /etc/hosts:${NC}"
    echo -e "   ${GREEN}<your-minio-ip> minio.local${NC}"
    echo -e "   ${GREEN}<your-minio-ip> minio-console.local${NC}"
    echo ""
    echo -e "${YELLOW}If MinIO is on this machine, use:${NC}"
    echo -e "   ${GREEN}echo '127.0.0.1 minio.local minio-console.local' | sudo tee -a /etc/hosts${NC}"
    echo ""
fi

# Check if MinIO API is accessible
echo -e "${YELLOW}🔌 Checking MinIO API at http://${MINIO_API_HOST}...${NC}"
if curl -sf "http://${MINIO_API_HOST}/minio/health/live" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MinIO API is accessible!${NC}"
else
    echo -e "${RED}❌ MinIO API is not accessible at http://${MINIO_API_HOST}${NC}"
    echo -e "${YELLOW}Please verify:${NC}"
    echo "  1. MinIO is running"
    echo "  2. /etc/hosts has correct entry for minio.local"
    echo "  3. Firewall allows access to port 9000"
    echo ""
    echo -e "${YELLOW}To use a local MinIO instance instead:${NC}"
    echo "  docker-compose -f docker-compose.local.yml up -d"
    echo ""
    exit 1
fi

# Create .env.test if it doesn't exist
if [ ! -f .env.test ]; then
    echo -e "${YELLOW}📝 Creating .env.test from example...${NC}"
    cp .env.test.example .env.test
    echo -e "${GREEN}✅ Created .env.test${NC}"
else
    echo -e "${GREEN}✅ .env.test already exists${NC}"
fi

# Install boto3 if not already installed
echo -e "${YELLOW}📦 Checking Python dependencies...${NC}"
if python3 -c "import boto3" 2>/dev/null; then
    echo -e "${GREEN}✅ boto3 is installed${NC}"
else
    echo -e "${YELLOW}Installing boto3...${NC}"
    pip install --user boto3
    echo -e "${GREEN}✅ boto3 installed${NC}"
fi

# Display access information
echo ""
echo -e "${GREEN}✅ MinIO setup verification complete!${NC}"
echo ""
echo "📊 Access Information:"
echo "  • MinIO Console: http://${MINIO_CONSOLE_HOST}"
echo "  • MinIO API: http://${MINIO_API_HOST}"
echo "  • Username: minioadmin (default)"
echo "  • Password: minioadmin (default)"
echo "  • Bucket: timelocker-test"
echo ""
echo "🧪 Run tests with:"
echo "  source .env.test  # Load environment variables"
echo "  pytest tests/TimeLocker/integration/test_s3_minio.py -v"
echo ""
echo "📚 Documentation:"
echo "  docs/MINIO_TESTING.md"
echo ""
echo "💡 Note: Using existing MinIO deployment at minio.local"
echo "   To use a local MinIO instance: docker-compose -f docker-compose.local.yml up -d"
echo ""

