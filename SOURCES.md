# Sources / Research Notes

This prototype uses a small, illustrative emission factor catalog and simplified ingestion mappings.

- The references below informed the *structure* (Scopes 1/2/3, audit expectations) and the *shapes* of the three source types.
- Seeded factor values are demo-only and not intended to be authoritative.

## 1) SAP (fuel + procurement)

### What format I researched
SAP integration commonly happens via:
- **IDocs** (structured message format)
- **OData APIs** (SAP Gateway)
- **Flat exports** from SAP GUI/ALV reports (CSV/Excel)

For a 4-day prototype, I chose the flat export path because it’s a realistic “first-mile” onboarding artifact and it forces the system to handle locale/unit/date mess.

Reference starting points:
- SAP OData overview: https://help.sap.com/docs/SAP_GATEWAY
- IDoc overview: https://en.wikipedia.org/wiki/IDoc

### What I learned (that shaped the model)
- Plant codes (`Werk`) are meaningless without a lookup table.
- Locale quirks are common: **semicolon delimiter**, **decimal comma**, and non-English headers.
- Units are inconsistent across exports and user edits (e.g. `L`, `liter`, `LTR`).

### What the sample data looks like and why
File: `sample_data/sap_export.csv`

Included on purpose:
- German headers (`Werk`, `Brennstofftyp`, `Menge`, `Einheit`, `Datum`)
- Semicolon-delimited CSV + decimal comma (`1.234,5`)
- Multiple date formats (`31.12.2025`, `2025/11/05`, `05-11-25`)
- Unit variants (`L`, `liter`, `LTR`, `m3`) and an unsupported example (`gal`)
- A missing fuel type row (to simulate procurement rows)
- An unknown plant code (`9999`) and a negative quantity (anomaly)

### What would break / isn’t modeled
- True SAP IDoc/OData semantics, paging, auth, and change deltas
- Complex procurement details (currency, vendor, PO/invoice lifecycles)
- Deep master-data enrichment (cost centers, materials hierarchy)

## 2) Utility data (electricity)

### What format I researched
Facilities teams commonly pull usage from a **utility portal CSV export**. In some regions, “Green Button” is also used for standardized energy usage exports.

References:
- Green Button initiative (utility usage data standard): https://www.greenbuttondata.org/

### What I learned (that shaped the model)
- Billing periods rarely align to calendar months; period-based records are required.
- Exports can contain either a single total kWh, or TOU (peak/off-peak) buckets.
- Bad rows happen: missing totals, reversed dates, unknown meters.

### What the sample data looks like and why
File: `sample_data/utility_export.csv`

Included on purpose:
- Billing periods that cross months (`2026-02-15` → `2026-03-14`)
- Missing total `kwh` but present `peak_usage`/`off_peak_usage` (derived total)
- Multi-month period (`2026-04-14` → `2026-06-30`)
- Reversed period dates (start after end)
- Unknown plant code (`9999`)

### What would break / isn’t modeled
- PDF bills/OCR
- Interval data (15-min) and demand/voltage/reactive power fields
- Tariff rate math (charges, taxes) and supplier-specific emissions (market-based)

## 3) Corporate travel (flights, hotels, ground)

### What format I researched
Corporate travel platforms (e.g., Concur) typically expose transaction feeds via APIs with heterogeneous item types.

References:
- Concur developer portal: https://developer.concur.com/

### What I learned (that shaped the model)
- Flights can be missing distances; sometimes you only get airport codes.
- The same feed mixes different categories (flight/hotel/ground) with different factor units.
- You need category-specific metadata without exploding the schema.

### What the sample data looks like and why
File: `sample_data/travel_payload.json`

Included on purpose:
- Flight with missing `distance_km` (distance estimated from airport codes)
- Flight with provided distance
- Unknown airport code (`XXX`) to show parse failure behavior
- Hotel stays (nights/rooms) and ground travel (km)

### What would break / isn’t modeled
- Multi-leg itineraries, ticket changes/refunds, ancillary fees
- Large/authoritative airport dataset (prototype includes a small curated list)
- More detailed class/cabin rules and radiative forcing variants

## Cross-cutting references

### Accounting scopes & guidance
- GHG Protocol overview and standards (Scopes 1/2/3): https://ghgprotocol.org/

### Emission factor catalogs (examples)
- UK Government GHG Conversion Factors for Company Reporting: https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting
- US EPA eGRID (electricity emissions data): https://www.epa.gov/egrid

### Travel distance / air travel conventions
- ICAO Carbon Emissions Calculator (general methodology references): https://www.icao.int/environmental-protection/CarbonOffset/Pages/default.aspx
- Great-circle distance is estimated using the haversine formula.

### Implementation references
- Django documentation: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- django-filter: https://django-filter.readthedocs.io/
