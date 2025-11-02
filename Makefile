.PHONY: setup audit test build run clean

setup:
	@echo "🔧 Setting up environment..."
	pip install -r backend/requirements.txt

audit:
	@echo "🔍 Running Quality Audit..."
	cd backend/scripts && python audit_quality.py
	@echo "✅ Audit complete. See AUDIT_REPORT.md"

test:
	@echo "🧪 Running tests..."
	cd backend && pytest -q --disable-warnings
	@echo "✅ Tests completed."

build: audit
	@echo "📦 Building Docker containers..."
	docker-compose build

run:
	@echo "🚀 Starting system..."
	docker-compose up

clean:
	@echo "🧹 Cleaning up cache, logs and temp files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f AUDIT_REPORT.md
	@echo "✅ Clean complete."
