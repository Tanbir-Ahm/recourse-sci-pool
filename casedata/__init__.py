"""Internal case-data layer: one standard way to ask for court-case data, whatever the source.

The product (briefs, case summaries, alerts) asks `layer.CaseDataLayer` for a case; the layer asks one adapter (`adapter.Adapter`) for the data. Today there is only a made-up
adapter (`fake.FakeAdapter`) for tests: nothing here makes a network call, needs a key or spends money. A real source (a vendor, the lawyer's own input, an official route if one is
ever allowed) is a new adapter; nothing above it changes. Standard library only.

Rules the layer keeps (see layer.py):
  * every record says where it came from, when it was fetched and whether it is FRESH, STALE or FAILED; a failed update is never shown as fresh;
  * it reads its own saved copy first and pays a source only for what is missing or old;
  * every paid call is capped per day and written to a ledger before it is sent;
  * a case is known by a nickname and its last four digits in anything a person reads (labels, events, the ledger).
"""
