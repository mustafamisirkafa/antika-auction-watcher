#!/bin/bash
# Redis Restore Script for Antika Auction Watcher
# Usage: ./restore_redis.sh [backup_file]

set -e

# Configuration
BACKUP_DIR="/backups/redis"
CONTAINER_NAME="antika_redis"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Antika Redis Restore ===${NC}"

# Determine backup file
if [ -z "$1" ]; then
    # Use latest backup if no file specified
    BACKUP_FILE="${BACKUP_DIR}/latest.rdb.gz"
    echo "No backup file specified, using latest: ${BACKUP_FILE}"
else
    BACKUP_FILE="$1"
fi

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}Error: Backup file not found: ${BACKUP_FILE}${NC}"
    echo ""
    echo "Available backups:"
    ls -lh "${BACKUP_DIR}" | grep ".rdb"
    exit 1
fi

# Confirmation prompt
echo -e "${YELLOW}WARNING: This will REPLACE all current Redis data!${NC}"
echo "Backup file: ${BACKUP_FILE}"
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Check if Redis container is running
if ! docker ps | grep -q "${CONTAINER_NAME}"; then
    echo -e "${RED}Error: Redis container '${CONTAINER_NAME}' is not running${NC}"
    exit 1
fi

# Decompress if needed
RESTORE_FILE="${BACKUP_FILE}"
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    echo -e "${YELLOW}Decompressing backup...${NC}"
    RESTORE_FILE="${BACKUP_DIR}/restore_temp.rdb"
    gunzip -c "${BACKUP_FILE}" > "${RESTORE_FILE}"
fi

# Stop Redis writes
echo -e "${YELLOW}Stopping Redis writes...${NC}"
docker exec "${CONTAINER_NAME}" redis-cli --no-auth-warning -a "${REDIS_PASSWORD:-changeme}" CONFIG SET save ""

# Copy backup to container
echo -e "${YELLOW}Copying backup to Redis container...${NC}"
docker cp "${RESTORE_FILE}" "${CONTAINER_NAME}:/data/dump.rdb"

# Restart Redis to load new data
echo -e "${YELLOW}Restarting Redis container...${NC}"
docker restart "${CONTAINER_NAME}"

# Wait for Redis to be ready
echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
sleep 5

for i in {1..30}; do
    if docker exec "${CONTAINER_NAME}" redis-cli --no-auth-warning -a "${REDIS_PASSWORD:-changeme}" ping | grep -q "PONG"; then
        echo -e "${GREEN}? Redis is ready${NC}"
        break
    fi
    echo -n "."
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}? Redis failed to start${NC}"
        exit 1
    fi
done

# Verify data
echo -e "${YELLOW}Verifying restored data...${NC}"
KEY_COUNT=$(docker exec "${CONTAINER_NAME}" redis-cli --no-auth-warning -a "${REDIS_PASSWORD:-changeme}" DBSIZE | grep -oE '[0-9]+')
echo -e "${GREEN}? Restored ${KEY_COUNT} keys${NC}"

# Cleanup temp file
if [ -f "${BACKUP_DIR}/restore_temp.rdb" ]; then
    rm "${BACKUP_DIR}/restore_temp.rdb"
fi

echo ""
echo -e "${GREEN}=== Restore Complete ===${NC}"
