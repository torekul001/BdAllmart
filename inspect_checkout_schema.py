import sys

from db import fetch_all


if len(sys.argv) > 1:
    table_names = sys.argv[1:]
    placeholders = ",".join("?" for _ in table_names)
    query = """
    SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME IN ({0})
    ORDER BY TABLE_NAME, ORDINAL_POSITION
    """.format(placeholders)
    for row in fetch_all(query, table_names):
        print("{0}.{1} {2} nullable={3} length={4}".format(
            row["TABLE_NAME"],
            row["COLUMN_NAME"],
            row["DATA_TYPE"],
            row["IS_NULLABLE"],
            row.get("CHARACTER_MAXIMUM_LENGTH"),
        ))
    raise SystemExit


query = """
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
  AND (
    TABLE_NAME LIKE '%Customer%'
    OR TABLE_NAME LIKE '%Order%'
    OR TABLE_NAME LIKE '%Sales%'
    OR TABLE_NAME LIKE '%Payment%'
    OR TABLE_NAME LIKE '%Invoice%'
    OR TABLE_NAME LIKE '%SMS%'
    OR TABLE_NAME LIKE '%Message%'
  )
ORDER BY TABLE_NAME
"""

for row in fetch_all(query):
    print(row["TABLE_NAME"])
