#!/bin/bash
# Open Jaeger UI (Sprint 3)

echo "?? Opening Jaeger UI..."
echo "URL: http://localhost:16686"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:16686
elif [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:16686
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    start http://localhost:16686
else
    echo "Please open http://localhost:16686 in your browser"
fi
