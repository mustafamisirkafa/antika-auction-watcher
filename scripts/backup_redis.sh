#!/bin/bash
# Redis Backup Script for Antika Auction Watcher
# Usage: ./backup_redis.sh

set -e

# Configuration
BACKUP_DIR="/backups/redis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="redis_backup_${TIMESTAMP}.rdb"
CONTAINER_NAME="antika_redis"
RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Antika Redis Backup ===${NC}"
echo "Timestamp: $(date)"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Check if Redis container is running
if ! docker ps | grep -q "${CONTAINER_NAME}"; then
    echo -e "${RED}Error: Redis container '${CONTAINER_NAME}' is not running${NC}"
    exit 1
fi

echo -e "${YELLOW}Triggering Redis SAVE...${NC}"
docker exec "${CONTAINER_NAME}" redis-cli --no-auth-warning -a "${REDIS_PASSWORD:-changeme}" SAVE

echo -e "${YELLOW}Copying dump.rdb to backup location...${NC}"
docker cp "${CONTAINER_NAME}:/data/dump.rdb" "${BACKUP_DIR}/${BACKUP_FILE}"

if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    # Get file size
    SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
    echo -e "${GREEN}? Backup successful: ${BACKUP_FILE} (${SIZE})${NC}"
    
    # Compress backup
    echo -e "${YELLOW}Compressing backup...${NC}"
    gzip "${BACKUP_DIR}/${BACKUP_FILE}"
    COMPRESSED_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)
    echo -e "${GREEN}? Compressed: ${BACKUP_FILE}.gz (${COMPRESSED_SIZE})${NC}"
    
    # Create latest symlink
    ln -sf "${BACKUP_FILE}.gz" "${BACKUP_DIR}/latest.rdb.gz"
else
    echo -e "${RED}? Backup failed${NC}"
    exit 1
fi

# Cleanup old backups
echo -e "${YELLOW}Cleaning up backups older than ${RETENTION_DAYS} days...${NC}"
find "${BACKUP_DIR}" -name "redis_backup_*.rdb.gz" -type f -mtime +${RETENTION_DAYS} -delete
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "redis_backup_*.rdb.gz" -type f -mtime +${RETENTION_DAYS} | wc -l)
echo -e "${GREEN}? Cleaned up ${DELETED_COUNT} old backups${NC}"

# List recent backups
echo ""
echo "Recent backups:"
ls -lh "${BACKUP_DIR}" | grep "redis_backup_" | tail -5

echo ""
echo -e "${GREEN}=== Backup Complete ===${NC}"
