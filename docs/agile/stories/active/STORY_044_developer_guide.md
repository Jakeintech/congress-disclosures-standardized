# STORY-044: Write Developer Guide

**Epic**: EPIC-001 | **Sprint**: Sprint 4 | **Points**: 2 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** developer
**I want** guide for extending the system
**So that** I can add new features

## Acceptance Criteria
- **GIVEN** Developer guide document
- **WHEN** I want to add new Lambda
- **THEN** Guide shows how
- **AND** Explains how to modify state machine
- **AND** Documents testing approach

## Technical Tasks
- [ ] Create `docs/DEVELOPER_GUIDE.md`
- [ ] Document how to add new Lambda functions
- [ ] Explain state machine modifications
- [ ] Document adding new data sources
- [ ] Add testing guide
- [ ] Include code examples

## Guide Sections
1. Adding New Lambda Functions
   - Create Lambda directory
   - Write handler.py
   - Add Terraform resource
   - Package dependencies
   - Deploy and test

2. Modifying State Machine
   - Edit state machine JSON
   - Update Terraform template
   - Test locally with SAM
   - Deploy and validate

3. Adding New Data Sources
   - Bronze layer pattern
   - Silver transformation
   - Gold aggregation
   - API integration

4. Testing
   - Running tests locally
   - Writing new tests
   - Debugging failures

## Estimated Effort: 2 hours
**Target**: Jan 9, 2026
