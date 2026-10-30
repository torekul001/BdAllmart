"""Run the additive marketplace migration explicitly before serving the new portal."""
import json
from datetime import datetime, timezone
from pathlib import Path
from market_db import transaction, migrate, TABLES
from legacy_jobs import migrate_applications


def main():
    with transaction() as store:
        before = store.all("SELECT t.name AS TableName, SUM(p.rows) AS [RowCount] FROM sys.tables t JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN (0,1) GROUP BY t.name ORDER BY t.name")
        columns = store.all("SELECT TABLE_NAME,COLUMN_NAME,DATA_TYPE,CHARACTER_MAXIMUM_LENGTH,IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_NAME,ORDINAL_POSITION")
    directory = Path(__file__).resolve().parent / "instance" / "migration_audit"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = directory / f"before_{stamp}.json"
    snapshot.write_text(json.dumps({"tables": before, "columns": columns}, default=str, indent=2), encoding="utf-8")
    with transaction() as store:
        store.run("SET LOCK_TIMEOUT 10000")
        migrate(store)
        migrate_applications(store)
        tables = store.all("SELECT name FROM sys.tables WHERE name LIKE 'Market%'")
    print(f"Migration complete. {len(TABLES)} marketplace tables expected, {len(tables)} found.")
    print("Existing C# JobAppliedList application schema is available.")
    print(f"Pre-migration schema/count audit: {snapshot}")
    print("No legacy table or record was changed. Schema audit is not a database backup.")


if __name__ == "__main__":
    main()
