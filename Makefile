# CreatorPulse — cross-platform makefile (alternative to PowerShell scripts)
# Windows users: prefer .bat / .ps1 scripts. Unix-like: use make.

.PHONY: setup dev test lint clean

setup:
	@echo "Running setup..."
	@if [ -f scripts/setup.ps1 ]; then \
		powershell -ExecutionPolicy Bypass -File scripts/setup.ps1; \
	else \
		echo "PowerShell setup not available, installing dependencies manually..."; \
		cd backend && pip install -e ".[dev]" && cd ..; \
		cd frontend && pnpm install; \
	fi

dev:
	@if [ -f scripts/dev.ps1 ]; then \
		powershell -ExecutionPolicy Bypass -File scripts/dev.ps1; \
	else \
		cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload & \
		cd frontend && pnpm dev; \
	fi

test:
	@if [ -f scripts/test.ps1 ]; then \
		powershell -ExecutionPolicy Bypass -File scripts/test.ps1; \
	else \
		cd backend && python -m pytest tests/ -q && python -m ruff check app tests && cd ..; \
		cd frontend && pnpm lint && pnpm test && pnpm build; \
	fi

lint:
	cd backend && python -m ruff check app tests && python -m pyright app && cd ..
	cd frontend && pnpm lint

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.pyc" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.ruff_cache backend/.pyright_cache
	rm -rf frontend/dist frontend/.vite frontend/tsconfig.tsbuildinfo
	rm -rf data/*.log
	@echo "Cleaned cache and build artifacts."
