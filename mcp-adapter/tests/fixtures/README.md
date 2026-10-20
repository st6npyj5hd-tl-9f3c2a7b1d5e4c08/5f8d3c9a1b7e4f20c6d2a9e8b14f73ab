# Fixture provenance

The four fixture files are byte-for-byte copies from production repository commit
`f4b70f2d901cc15b4b186c8b6342ad3c6a323040` (remote main inspected 2026-10-20).
They are copies under this test directory, not changes to published files.
`status.json` includes original school metadata to test that the adapter filters
it out; no school file is copied or fetched by the adapter.

The source status records SHA-256 for each weather payload. `test_success`
verifies those hashes match the original bytes. Parser tests compare scalar
values and hourly start/end arrays directly against source XML. Synthetic
variants in tests cover nils, namespaces, hazards, DST, malformed sources,
missing series, stale times and failed attempts without network requests.

The frozen clock for successful fixture responses is 2026-10-20T17:00:00Z.
Do not update fixtures just to make a stale test pass; review content changes and
update the recorded provenance and expected comparisons together.
