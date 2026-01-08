# Documentation

## Structure

- `architecture/` - System architecture, data flow, schemas, diagrams
- `guides/` - Setup guides, deployment guides, API documentation, automation
- `plans/` - Master execution plans, modernization roadmaps, implementation plans
- `terraform_audit/` - Infrastructure audit reports, refactoring guides
- `archived/` - Historical documentation, old status reports, deprecated guides
  - `status_reports/` - Implementation summaries, bug fix reports (if exists)
  - `old_makefiles/` - Deprecated Makefile versions

## Quick Links

### Getting Started
- [Deployment Guide](guides/DEPLOYMENT.md) - Self-hosting deployment guide
- [API Key Setup](guides/API_KEY_SETUP.md) - Setting up API authentication
- [Congress.gov Development](guides/CONGRESS_DEV_INSTRUCTIONS.md) - Working with Congress.gov API

### Architecture
- [Architecture Overview](architecture/ARCHITECTURE.md) - Detailed architecture documentation
- [Extraction Architecture](architecture/EXTRACTION_ARCHITECTURE.md) - Extraction pipeline deep dive
- [Data Flow Diagram](architecture/DATA_FLOW_DIAGRAM.md) - Visual data flow
- [Bronze Schema](architecture/BRONZE_SCHEMA.md) - Raw data layer schema
- [Congress S3 Schema](architecture/CONGRESS_S3_SCHEMA.md) - S3 structure for Congress data

### Planning & Strategy
- [Agent Execution Plan](plans/AGENT_EXECUTION_PLAN.md) - Sequential execution plan for agents
- [Cost Optimization](plans/COST_OPTIMIZATION.md) - AWS free tier optimization
- [API Strategy](plans/API_STRATEGY.md) - API design and endpoints
- [Bills Implementation Plan](plans/BILLS_IMPLEMENTATION_PLAN.md) - Congress.gov bills integration

### Operations
- [API Runbook](guides/API_RUNBOOK.md) - API operations and troubleshooting
- [Automation Guide](guides/AUTOMATION.md) - Automated workflows
- [Terraform Audit](terraform_audit/TERRAFORM_AUDIT.md) - Infrastructure audit

## Legal & Compliance

- [Legal Notes](LEGAL_NOTES.md) - 5 U.S.C. § 13107 compliance requirements
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community guidelines

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) in the root directory.
