# Canonical save schema 1 — TEST observations only

SQLite file default: `Saves/Guardian_Test/probe.sqlite3`. This contains probe event totals, not Guardian equipment, resources, bases, ships or native game save data.

| Table | Columns | Meaning |
|---|---|---|
| observations | role TEXT, incarnation TEXT, seq INTEGER; composite primary key | Highest observed action sequence per adapter incarnation |
| totals | role TEXT primary key, count INTEGER | Canonical observed increments from each role |

`PRAGMA user_version=1`, WAL mode, synchronous FULL. Incarnations are decimal text to avoid unsigned-64 to signed-SQLite overflow. New sequence delta and total commit in one SQLite transaction. Repeated sequence is a no-op; regression is refused. Quick-check validates database opening; malformed SQLite and future schemas are refused. Schema 0 initializes empty tables; no multi-generation campaign migration engine exists yet.

Backups use SQLite's snapshot API into a unique same-directory `.partial` file with synchronous FULL, commit and quick_check validation. The destination connection and all cursors are explicitly closed BEFORE replacement publishes the `.sqlite3` snapshot. SQLite connection context management alone only owns a transaction. Promotion failure cleans the partial after handle closure and propagates its error. Replacement is atomic where the filesystem supports it; no universal crash/power-loss durability guarantee is claimed for directory metadata. Backups occur on opening, orderly closing and an explicit backup call. A killed process does not execute closing backup. SQLite WAL provides committed-write recovery, subject to normal filesystem durability. Backup retention/restore UI and cross-game native checkpoints are not implemented.

Native Sunrise `investment.sqlite3` and NMS saves remain under their games' ownership. Never copy a live WAL database by copying only its main file. Future canonical item references must include engine/build/catalog identity; no guessed native item hashes belong in this schema.

## Ownership after the Windows repair

Store owns its source connection from the moment connect succeeds. Any failed initialization, including future schema or corruption refusal, closes it directly without attempting a closing backup. Store is a context manager and close is idempotent; an error during closing backup still closes the source and is reported. Explicit backup refuses an active source write transaction to avoid a self-blocked snapshot. Committed state and schema are unchanged. No garbage-collection timing or cleanup retry sleeps are relied on.
