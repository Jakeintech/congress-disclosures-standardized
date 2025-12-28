# 🗺️ Project Roadmap - Agile Sprints

```mermaid
gantt
    title Congress Disclosures Data Pipeline Roadmap
    dateFormat  YYYY-MM-DD
    section Sprint 1: Foundation
    Environment Setup & Infra         :done, s1a, 2025-11-01, 7d
    Bronze Layer Ingestion            :done, s1b, after s1a, 14d
    Initial Silver Extraction         :done, s1c, after s1b, 14d
    
    section Sprint 2: Gold Layer
    Schema Standardization            :done, s2a, 2025-12-01, 7d
    Analytic Aggregations             :done, s2b, after s2a, 14d
    Step Functions Orchestration      :done, s2c, after s2b, 14d

    section Sprint 3: Integration
    Multi-dataset Correlation         :active, s3a, 2025-12-25, 10d
    API Optimization                  :s3b, after s3a, 10d
    Next.js UI Integration            :s3c, after s3b, 10d

    section Sprint 4: Production
    Production Deployment             :s4a, 2026-01-20, 7d
    Monitoring & Alerting             :s4b, after s4a, 10d
    Public Launch                     :milestone, 2026-02-15, 0d
```

## 🎯 Current Status: Sprint 3 (Integration)

We are currently focusing on:
- **STORY-028**: Unified State Machine Design.
- **STORY-042**: API Performance & Data Quality.
- **STORY-050**: UI/UX Refinement & Next.js Prerendering.

For more details, see:
- [Sprint 3 Plan](docs/agile/sprints/SPRINT_3_PLAN.md)
- [Project Metrics](docs/agile/metrics/INDEX.md)
