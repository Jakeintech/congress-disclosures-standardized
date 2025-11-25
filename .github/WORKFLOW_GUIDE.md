# CI/CD Workflow Guide

## Current Setup

### Working Directly on `main` Branch
The CI/CD pipeline is configured to auto-deploy when pushing to `main`. This works for solo development but has risks.

**Pros:**
- Simple, fast iteration
- No PR overhead for solo dev

**Cons:**
- No code review before production
- Breaking changes go straight to production
- Hard to test changes before deploy

### How Auto-Deploy Works

1. **Push to `main`** → Triggers CI workflow
2. **Lint & Tests** → Run (currently set to continue-on-error)
3. **Terraform Validate** → Checks infrastructure code
4. **Build Lambda Packages** → Creates deployment packages
5. **Deploy to AWS** → Updates Terraform & Lambda functions automatically

## Recommended Workflow (When Team Grows)

### Branch Strategy
```
main (production) ← Protected branch, requires PR
  ↑
dev (development) ← Integration branch, auto-deploys to dev environment
  ↑
feature/your-feature ← Work happens here
```

### Development Flow
1. Create feature branch from `dev`:
   ```bash
   git checkout dev
   git pull
   git checkout -b feature/add-gold-kpis
   ```

2. Make changes, commit frequently:
   ```bash
   git add .
   git commit -m "feat: add new gold KPIs"
   ```

3. Push and create PR:
   ```bash
   git push origin feature/add-gold-kpis
   # Create PR on GitHub: feature/add-gold-kpis → dev
   ```

4. After PR approval, merge to `dev`:
   - Auto-deploys to development environment
   - Test in dev before promoting to production

5. When ready for production:
   - Create PR: `dev` → `main`
   - Requires approval (set in GitHub branch protection)
   - Merge triggers production deployment

## Current Workflows

### `.github/workflows/ci.yml`
- **Triggers**: Push to `main`, PR to `main`, Manual
- **Jobs**:
  - Lint & Format (continues on error)
  - Unit Tests (continues on error)
  - Terraform Validate
  - Build Lambda Packages
  - Deploy to AWS (production)

### `.github/workflows/deploy-website.yml`
- **Triggers**: Push to `main` (website changes only)
- **Jobs**:
  - Sync website files to S3
  - Updates with no-cache headers

## Why Deploy Was Skipped

**Before Fix:**
```yaml
if: github.ref == 'refs/heads/main' && github.event_name == 'workflow_dispatch'
```
- Required BOTH conditions: push to main AND manual trigger
- Designed for dev→main workflow with manual production deployment
- Would skip on automatic pushes to main

**After Fix:**
```yaml
if: github.ref == 'refs/heads/main'
```
- Deploys on ANY push to main (automatic or manual)
- Suitable for solo development directly on main

## Future Improvements

When moving to team development:

1. **Branch Protection** on `main`:
   ```
   ✓ Require pull request reviews (1 approval)
   ✓ Require status checks to pass
   ✓ Require branches to be up to date
   ✓ Include administrators
   ```

2. **Separate Environments**:
   - `dev` branch → dev.congress-disclosures.com
   - `main` branch → congress-disclosures.com

3. **Stricter CI Checks**:
   - Remove `continue-on-error` from lint/tests
   - Add integration tests
   - Require 80%+ code coverage

4. **Manual Approval for Production**:
   ```yaml
   if: github.ref == 'refs/heads/main' && github.event_name == 'workflow_dispatch'
   environment:
     name: production
   ```

## Quick Commands

```bash
# Check workflow status
gh run list --workflow=ci.yml

# View latest run
gh run view

# Trigger manual deploy
gh workflow run ci.yml

# Watch workflow
gh run watch
```
