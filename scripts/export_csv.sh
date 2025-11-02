#!/bin/bash
# CSV Export Script for Antika Auction Watcher
# Exports data from API endpoints
# Usage: ./export_csv.sh [days]

set -e

# Configuration
API_URL="${API_URL:-http://localhost:8000/api/v1}"
EXPORT_DIR="/backups/exports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DAYS="${1:-30}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Antika CSV Export ===${NC}"
echo "Exporting data for last ${DAYS} days"
echo "Timestamp: $(date)"
echo ""

# Create export directory
mkdir -p "${EXPORT_DIR}"

# Calculate date range
END_DATE=$(date +%Y-%m-%d)
START_DATE=$(date -d "${DAYS} days ago" +%Y-%m-%d)

echo -e "${YELLOW}Date range: ${START_DATE} to ${END_DATE}${NC}"
echo ""

# Export valuations
echo -e "${YELLOW}Exporting valuations...${NC}"
VALUATIONS_FILE="${EXPORT_DIR}/valuations_${TIMESTAMP}.csv"
curl -s "${API_URL}/admin/exports/valuations.csv?from=${START_DATE}&to=${END_DATE}" > "${VALUATIONS_FILE}"

if [ -f "${VALUATIONS_FILE}" ] && [ -s "${VALUATIONS_FILE}" ]; then
    LINES=$(wc -l < "${VALUATIONS_FILE}")
    SIZE=$(du -h "${VALUATIONS_FILE}" | cut -f1)
    echo -e "${GREEN}? Valuations exported: ${LINES} rows (${SIZE})${NC}"
else
    echo "? Valuations export failed or empty"
fi

# Export outcomes
echo -e "${YELLOW}Exporting outcomes...${NC}"
OUTCOMES_FILE="${EXPORT_DIR}/outcomes_${TIMESTAMP}.csv"
curl -s "${API_URL}/admin/exports/outcomes.csv?from=${START_DATE}&to=${END_DATE}" > "${OUTCOMES_FILE}"

if [ -f "${OUTCOMES_FILE}" ] && [ -s "${OUTCOMES_FILE}" ]; then
    LINES=$(wc -l < "${OUTCOMES_FILE}")
    SIZE=$(du -h "${OUTCOMES_FILE}" | cut -f1)
    echo -e "${GREEN}? Outcomes exported: ${LINES} rows (${SIZE})${NC}"
else
    echo "? Outcomes export failed or empty"
fi

# Export feedback summary
echo -e "${YELLOW}Exporting feedback summary...${NC}"
FEEDBACK_FILE="${EXPORT_DIR}/feedback_summary_${TIMESTAMP}.json"
curl -s "${API_URL}/advisor/feedback/summary?days=${DAYS}" > "${FEEDBACK_FILE}"

if [ -f "${FEEDBACK_FILE}" ] && [ -s "${FEEDBACK_FILE}" ]; then
    SIZE=$(du -h "${FEEDBACK_FILE}" | cut -f1)
    echo -e "${GREEN}? Feedback summary exported (${SIZE})${NC}"
else
    echo "? Feedback export failed or empty"
fi

# Export learning progress
echo -e "${YELLOW}Exporting learning progress...${NC}"
LEARNING_FILE="${EXPORT_DIR}/learning_progress_${TIMESTAMP}.json"
curl -s "${API_URL}/advisor/learning/progress" > "${LEARNING_FILE}"

if [ -f "${LEARNING_FILE}" ] && [ -s "${LEARNING_FILE}" ]; then
    SIZE=$(du -h "${LEARNING_FILE}" | cut -f1)
    echo -e "${GREEN}? Learning progress exported (${SIZE})${NC}"
else
    echo "? Learning export failed or empty"
fi

# Create archive
echo ""
echo -e "${YELLOW}Creating archive...${NC}"
ARCHIVE_FILE="${EXPORT_DIR}/antika_export_${TIMESTAMP}.tar.gz"
tar -czf "${ARCHIVE_FILE}" -C "${EXPORT_DIR}" \
    "valuations_${TIMESTAMP}.csv" \
    "outcomes_${TIMESTAMP}.csv" \
    "feedback_summary_${TIMESTAMP}.json" \
    "learning_progress_${TIMESTAMP}.json" 2>/dev/null

if [ -f "${ARCHIVE_FILE}" ]; then
    ARCHIVE_SIZE=$(du -h "${ARCHIVE_FILE}" | cut -f1)
    echo -e "${GREEN}? Archive created: ${ARCHIVE_FILE} (${ARCHIVE_SIZE})${NC}"
    
    # Create latest symlink
    ln -sf "antika_export_${TIMESTAMP}.tar.gz" "${EXPORT_DIR}/latest.tar.gz"
    
    # Cleanup individual files
    rm "${VALUATIONS_FILE}" "${OUTCOMES_FILE}" "${FEEDBACK_FILE}" "${LEARNING_FILE}" 2>/dev/null || true
else
    echo "? Archive creation failed"
fi

# Cleanup old exports (keep last 30)
echo -e "${YELLOW}Cleaning up old exports...${NC}"
cd "${EXPORT_DIR}"
ls -t antika_export_*.tar.gz | tail -n +31 | xargs -r rm
echo -e "${GREEN}? Cleanup complete${NC}"

echo ""
echo -e "${GREEN}=== Export Complete ===${NC}"
echo "Archive: ${ARCHIVE_FILE}"
