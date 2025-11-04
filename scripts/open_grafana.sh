#!/bin/bash
# Open Grafana dashboard (Sprint 3)

echo "?? Opening Grafana..."
echo "URL: http://localhost:3000"
echo "Default credentials: admin/admin"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:3000
elif [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:3000
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    start http://localhost:3000
else
    echo "Please open http://localhost:3000 in your browser"
fi
