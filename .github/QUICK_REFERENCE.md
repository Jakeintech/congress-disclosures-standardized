# ⚡ Quick Reference - Congress Disclosures Agile

## 🌿 Branch Naming
Format: `agent/<your-name>/<STORY-ID>-kebab-description`
- ✅ `agent/jake/STORY-042-fix-duckdb-nan`
- ❌ `fix-bug`

## 📝 Commit Messages
Format: `<type>(<scope>): [STORY-ID] <description>`
- ✅ `feat(api): [STORY-042] convert NaN to null in response`
- ❌ `fix things`

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`
**Scopes**: `bronze`, `silver`, `gold`, `extraction`, `api`, `infra`, `ui`

## 🛠️ Common Commands

### 📦 Setup & Install
```bash
make setup              # Install dependencies & pre-commit
pre-commit install      # Manual hook install
```

### 🧪 Testing & Linting
```bash
make test               # Run all tests
pytest tests/unit/      # Run unit tests
make lint               # Run linters (black, flake8, mypy)
pre-commit run --all    # Run all hooks manually
```

### 🚀 Pipeline & Infrastructure
```bash
make deploy             # Deploy AWS infrastructure
make run-pipeline       # Start data ingestion (incremental)
make reset-and-run-all  # WIPE EVERYTHING and re-run (be careful!)
```

## 📋 Useful Links
- **Agile Board**: [GitHub Projects Board](https://github.com/users/Jakeintech/projects)
- **Status Report**: [.github/SETUP_STATUS.md](.github/SETUP_STATUS.md)
- **Onboarding**: [.github/AGENT_ONBOARDING.md](.github/AGENT_ONBOARDING.md)
