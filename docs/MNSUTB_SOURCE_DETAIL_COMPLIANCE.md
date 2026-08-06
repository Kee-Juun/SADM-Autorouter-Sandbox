# MNSUTB Source Detail Compliance

Status: implemented  
Required IRT value: `Table-(5-day spec source)`

## Change

MNSUTB order-title detection remains unchanged, but
`classify_mnsutb_source_detail()` now maps an `ORDER` title to the required business
Source Detail:

```text
Table-(5-day spec source)
```

It no longer emits `Order` as MNSUTB metadata.

The value is defined once as `MNSUTB_SOURCE_DETAIL` in
`core/mnsutb_extractor.py`. Parsed `MNSUTBMetadata` carries that exact value, and the
existing `handle_mnsutb_fields()` path passes it to the shared Source Detail dropdown
selector.

The 2026-07-28 sync also aligns the Excel abbreviation mapping (`t`) and GUI
filename mapping (`t`/`table`) with the same exact value.

## Verification

`tests/test_mnsutb_source_detail_compliance.py` verifies:

- the exact mandated constant;
- `Order` title classification does not return `Order`;
- parsed MNSUTB document metadata carries the mandated value;
- the form-field helper requests the exact mandated visible text;
- the Excel Source Detail mapping uses the mandated value;
- filename-based Source Detail extraction uses the mandated value.

Existing MNSUTB form characterization fixtures now use the shared constant. The full
offline suite passes 381 tests.

No live browser or staging route was performed, so availability of the exact visible
dropdown option remains a live-validation item.
