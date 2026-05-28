# Architecture Decisions

This document captures notable decisions made to keep the prototype realistic, auditable, and easy to extend.

## 1) Raw-first ingestion
**Decision:** Always create a `RawRecord` for every input row/event, even when parsing fails.

**Why:** Auditability and reprocessing. Analysts can trace every canonical row back to raw input; failures are visible (via `parse_errors`) instead of silently dropped.

**Consequence:** More storage, but simpler and safer lineage.

## 2) Canonical ActivityRecord as the review surface
**Decision:** Normalize all sources into a single `ActivityRecord` model with consistent fields (date/period, quantity/unit, CO2e).

**Why:** Enables a single analyst workflow across heterogeneous sources (ERP purchases, utility bills, travel APIs).

**Consequence:** Requires a flexible `activity_metadata` JSON for source/category-specific fields.

## 3) Emission factor snapshotting
**Decision:** Store `emission_factor_snapshot` on `ActivityRecord` in addition to an FK to `EmissionFactor`.

**Why:** Factors can change (new versions, better data). Snapshotting keeps historical approvals auditable even if the catalog changes.

**Consequence:** Potential data duplication, but it is intentional for audit stability.

## 4) Approval locks records
**Decision:** Approval immediately sets `locked_at/locked_by` and prevents further edits via the service layer.

**Why:** Creates a clear “finalized for audit” boundary.

**Consequence:** If a correction is needed after approval, the system would need a controlled “supersede/amend” flow (explicitly out of scope for this prototype).

## 5) Service-layer writes + thin DRF views
**Decision:** Put ingestion and review logic in `core/services/*` and keep API views thin.

**Why:** Keeps business rules testable and re-usable across API/management commands.

**Consequence:** More modules, but clearer separation of concerns.

## 6) Simple tenant scoping via middleware
**Decision:** Resolve tenant from `X-Tenant-Slug` header (or query param) and scope all querysets by `tenant`.

**Why:** Demonstrates realistic multi-tenancy without implementing complex row-level security.

**Consequence:** Not sufficient for production security by itself; auth/RBAC is intentionally out of scope.

## 7) Frontend configuration in the header
**Decision:** Put API base URL, tenant slug, and analyst email as editable fields in the app header (stored in localStorage).

**Why:** Makes demos and local dev frictionless without building an auth system.

**Consequence:** Not a security model; purely a prototype convenience.

## 8) SAP ingestion: flat-file CSV export (ALV-style)
**Decision:** Model SAP fuel + procurement as a messy flat-file CSV export (semicolon-delimited, locale quirks) uploaded via the UI.

**Why:** In enterprise reality, SAP data often arrives as a spreadsheet export from an ALV report or an extraction job before any clean API integration exists. For a 4-day prototype, a CSV upload captures the “messy export” pain (units, locales, inconsistent dates) without implementing an IDoc/OData integration.

**Subset handled:**
- `Werk` (plant code), `Menge` (quantity), `Einheit` (unit), `Datum` (posting/activity date)
- Fuel: `Brennstofftyp` drives factor mapping (diesel/petrol)
- Procurement: `Materialgruppe` / `Materialkurztext` are retained for review and basic categorization

**Ignored / out of scope:**
- IDoc segments, OData/BAPI auth and paging, master-data lookups (cost centers, vendors)
- Full procurement accounting (currency, price, GL), and line-item reconciliation

## 9) Utility ingestion: portal CSV with billing periods
**Decision:** Model electricity as a facilities team “portal export” CSV uploaded via the UI, with explicit `billing_start`/`billing_end`.

**Why:** Utility exports frequently reflect billing periods and tariffs that don’t align to calendar months; this forces the model to support period-based activities.

**Subset handled:**
- Billing period start/end, plant code, meter id
- Energy quantity as `kwh`, or derived from `peak_usage + off_peak_usage`
- Simple tariff label retained in metadata

**Ignored / out of scope:**
- PDF bill parsing/OCR
- Complex rate structures (demand charges, reactive power, tiering) and interval (15-min) reads

## 10) Travel ingestion: Concur/Navan-style JSON payload
**Decision:** Model corporate travel as an API-shaped JSON payload uploaded via the UI (manual paste/upload), split into flight/hotel/ground subtypes.

**Why:** Travel platforms typically provide structured JSON with heterogeneous transaction types. Uploading a JSON payload simulates an API pull without standing up OAuth flows.

**Subset handled:**
- Flights: origin/destination airport codes, cabin/travel class, optional distance
- Hotels: nights and rooms
- Ground: distance in km for taxi/rail examples
- When flight distance is missing, estimate from airport coordinates (small curated demo list)

**Ignored / out of scope:**
- Multi-leg itineraries, refunds/exchanges, ancillary fees, rail station codes, car rentals
- Full factor governance per carrier/class and radiative forcing model variations

## 11) Questions for the PM (if available)
- What is the expected audit boundary: do auditors require immutable *raw files* or row-level snapshots are sufficient?
- Are we reporting market-based vs location-based electricity (and do we need supplier-specific factors)?
- How should post-approval corrections work: “supersede” records vs unlock with permission?
