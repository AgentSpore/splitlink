# SplitLink

## Problem
Users struggle to track shared expenses without creating accounts or sharing personal data. Manual calculations and spreadsheet coordination lead to disputes and accounting errors. Friends frequently ask: "How do we split this bill fairly?" with no simple solution that preserves privacy.

## Proposed Solution
SplitLink provides a privacy-first, link-only bill-splitting service. Users create expense events, add rows with amounts and names, and receive auto-calculated splits. No account registration is required. Participants access the event via a shareable link and settle payments through view-only summaries that show who owes whom.

## Proposed Architecture
FastAPI backend with:
- **api/** routers for events, expenses, and settlements
- **services/** for bill calculation logic (per-capita, custom ratios)
- **core/** for database layer using a lightweight store (SQLite for MVP)
- **schemas/** Pydantic models for request/response validation
- **utils/** for link generation and ID encryption

Public-facing web UI for creating/editing events, displayed as read-only summaries for participants. Mobile-responsive design. Event links use short tokens; optional PIN protection for private events.

## Target User
Friends, roommates, travel companions, and shared-expense groups who need to split bills quickly without account friction or data collection.

## Success Criteria
- Users can create expense events via web form
- Participants can view events through shareable links
- Auto-split calculations show per-person amounts
- View-only settlement summaries display outstanding balances
- End-to-end URL includes event token; no account signup required