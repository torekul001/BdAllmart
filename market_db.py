"""Additive marketplace storage. No legacy table is created, altered or deleted."""
from contextlib import contextmanager
from db import get_connection


TABLES = {
    "MarketSetting": "Id NVARCHAR(100) PRIMARY KEY, Value NVARCHAR(MAX) NOT NULL, Updated NVARCHAR(32) NOT NULL",
    "MarketProfile": "UserId NVARCHAR(100) PRIMARY KEY, DisplayName NVARCHAR(160) NOT NULL, Bio NVARCHAR(2000) NOT NULL, Business INTEGER NOT NULL DEFAULT 0, InstituteStatus NVARCHAR(20) NOT NULL DEFAULT 'none'",
    "MarketListing": "Id NVARCHAR(36) PRIMARY KEY, OwnerId NVARCHAR(100) NOT NULL, Kind NVARCHAR(20) NOT NULL, Mode NVARCHAR(20) NOT NULL, Title NVARCHAR(180) NOT NULL, Description NVARCHAR(MAX) NOT NULL, Price BIGINT NOT NULL CHECK (Price >= 0), Stock INTEGER NOT NULL CHECK (Stock >= 0), Status NVARCHAR(20) NOT NULL, Commission INTEGER NOT NULL CHECK (Commission BETWEEN 0 AND 80), Affiliate INTEGER NOT NULL, Asset NVARCHAR(200) NOT NULL, Image NVARCHAR(200) NOT NULL DEFAULT '', Meta NVARCHAR(MAX) NOT NULL, Created NVARCHAR(32) NOT NULL",
    "MarketAffiliate": "Id NVARCHAR(36) PRIMARY KEY, UserId NVARCHAR(100) NOT NULL, ListingId NVARCHAR(36) NOT NULL REFERENCES MarketListing(Id), Created NVARCHAR(32) NOT NULL, UNIQUE(UserId, ListingId)",
    "MarketJob": "Id NVARCHAR(36) PRIMARY KEY, OwnerId NVARCHAR(100) NOT NULL, Kind NVARCHAR(20) NOT NULL, Title NVARCHAR(180) NOT NULL, Description NVARCHAR(MAX) NOT NULL, Budget BIGINT NOT NULL CHECK (Budget > 0), Deadline NVARCHAR(32) NOT NULL, Status NVARCHAR(24) NOT NULL, PaymentRef NVARCHAR(120) NOT NULL, WinnerId NVARCHAR(36) NOT NULL, Created NVARCHAR(32) NOT NULL",
    "MarketProposal": "Id NVARCHAR(36) PRIMARY KEY, JobId NVARCHAR(36) NOT NULL REFERENCES MarketJob(Id), UserId NVARCHAR(100) NOT NULL, Body NVARCHAR(MAX) NOT NULL, Amount BIGINT NOT NULL CHECK (Amount > 0), Asset NVARCHAR(200) NOT NULL, Status NVARCHAR(20) NOT NULL, Created NVARCHAR(32) NOT NULL, UNIQUE(JobId, UserId)",
    "MarketOrder": "Id NVARCHAR(36) PRIMARY KEY, BuyerId NVARCHAR(100) NOT NULL, SellerId NVARCHAR(100) NOT NULL, ListingId NVARCHAR(36) NOT NULL, ProposalId NVARCHAR(36) NOT NULL, Kind NVARCHAR(20) NOT NULL, Title NVARCHAR(180) NOT NULL, Amount BIGINT NOT NULL CHECK (Amount >= 0), Quantity INTEGER NOT NULL CHECK (Quantity > 0), Status NVARCHAR(24) NOT NULL, PaymentStatus NVARCHAR(24) NOT NULL, PaymentRef NVARCHAR(120) NOT NULL, ReferrerId NVARCHAR(100) NOT NULL, Commission BIGINT NOT NULL CHECK (Commission >= 0), Brief NVARCHAR(MAX) NOT NULL, Delivery NVARCHAR(MAX) NOT NULL, Asset NVARCHAR(200) NOT NULL, Meta NVARCHAR(MAX) NOT NULL, RequestKey NVARCHAR(36) NOT NULL UNIQUE, Created NVARCHAR(32) NOT NULL",
    "MarketLegacyContract": "Id NVARCHAR(100) PRIMARY KEY, OrderId NVARCHAR(36) NOT NULL UNIQUE REFERENCES MarketOrder(Id), DesignerId NVARCHAR(100) NOT NULL, SubmissionId NVARCHAR(100) NOT NULL, Created NVARCHAR(32) NOT NULL",
    "MarketLedger": "Id NVARCHAR(36) PRIMARY KEY, UserId NVARCHAR(100) NOT NULL, SourceId NVARCHAR(36) NOT NULL, EntryType NVARCHAR(30) NOT NULL, Amount BIGINT NOT NULL, Note NVARCHAR(500) NOT NULL, Created NVARCHAR(32) NOT NULL, UNIQUE(UserId, SourceId, EntryType)",
    "MarketWithdrawal": "Id NVARCHAR(36) PRIMARY KEY, UserId NVARCHAR(100) NOT NULL, Amount BIGINT NOT NULL CHECK (Amount > 0), Destination NVARCHAR(300) NOT NULL, Status NVARCHAR(20) NOT NULL, Reference NVARCHAR(120) NOT NULL, RequestKey NVARCHAR(36) NOT NULL UNIQUE, Created NVARCHAR(32) NOT NULL",
    "MarketLesson": "Id NVARCHAR(36) PRIMARY KEY, ListingId NVARCHAR(36) NOT NULL REFERENCES MarketListing(Id), Title NVARCHAR(180) NOT NULL, Content NVARCHAR(MAX) NOT NULL, Video NVARCHAR(1000) NOT NULL, Asset NVARCHAR(200) NOT NULL, Preview INTEGER NOT NULL, Position INTEGER NOT NULL",
    "MarketEnrollment": "Id NVARCHAR(36) PRIMARY KEY, ListingId NVARCHAR(36) NOT NULL REFERENCES MarketListing(Id), UserId NVARCHAR(100) NOT NULL, OrderId NVARCHAR(36) NOT NULL, Status NVARCHAR(20) NOT NULL, Created NVARCHAR(32) NOT NULL, UNIQUE(ListingId, UserId)",
    "MarketProgress": "Id NVARCHAR(36) PRIMARY KEY, LessonId NVARCHAR(36) NOT NULL REFERENCES MarketLesson(Id), UserId NVARCHAR(100) NOT NULL, Created NVARCHAR(32) NOT NULL, UNIQUE(LessonId, UserId)",
    "MarketMessage": "Id NVARCHAR(36) PRIMARY KEY, OrderId NVARCHAR(36) NOT NULL REFERENCES MarketOrder(Id), SenderId NVARCHAR(100) NOT NULL, Body NVARCHAR(MAX) NOT NULL, Asset NVARCHAR(200) NOT NULL, Created NVARCHAR(32) NOT NULL",
    "MarketReview": "Id NVARCHAR(36) PRIMARY KEY, OrderId NVARCHAR(36) NOT NULL UNIQUE REFERENCES MarketOrder(Id), UserId NVARCHAR(100) NOT NULL, SellerId NVARCHAR(100) NOT NULL, Rating INTEGER NOT NULL CHECK (Rating BETWEEN 1 AND 5), Body NVARCHAR(2000) NOT NULL, Created NVARCHAR(32) NOT NULL",
    "MarketAttendance": "Id NVARCHAR(36) PRIMARY KEY, ListingId NVARCHAR(36) NOT NULL REFERENCES MarketListing(Id), UserId NVARCHAR(100) NOT NULL, ClassDate NVARCHAR(10) NOT NULL, Present INTEGER NOT NULL, UNIQUE(ListingId,UserId,ClassDate)",
    "MarketEvent": "Id NVARCHAR(36) PRIMARY KEY, ActorId NVARCHAR(100) NOT NULL, TargetId NVARCHAR(100) NOT NULL, Event NVARCHAR(100) NOT NULL, Details NVARCHAR(2000) NOT NULL, RecipientId NVARCHAR(100) NOT NULL, Created NVARCHAR(32) NOT NULL",
    "MarketPaymentClaim": "Reference NVARCHAR(120) PRIMARY KEY, SourceId NVARCHAR(36) NOT NULL UNIQUE, Created NVARCHAR(32) NOT NULL",
}


class Store:
    def __init__(self, connection, sqlite=False):
        self.connection = connection
        self.sqlite = sqlite

    def run(self, sql, params=()):
        return self.connection.cursor().execute(sql, params)

    def all(self, sql, params=()):
        cursor = self.run(sql, params)
        names = [col[0] for col in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]

    def one(self, sql, params=()):
        rows = self.all(sql, params)
        return rows[0] if rows else None

    def page(self, sql, params=(), offset=0, limit=25):
        if self.sqlite:
            return self.all(sql + " LIMIT ? OFFSET ?", [*params, limit, offset])
        return self.all(sql + " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY", [*params, offset, limit])

    def get(self, table, identity, lock=False, key="Id"):
        assert table in TABLES and key in {"Id", "UserId", "Reference"}
        hint = " WITH (UPDLOCK, HOLDLOCK)" if lock and not self.sqlite else ""
        return self.one(f"SELECT * FROM {table}{hint} WHERE {key} = ?", [str(identity)])

    def insert(self, table, values):
        assert table in TABLES
        columns = ", ".join(values)
        marks = ", ".join("?" for _ in values)
        self.run(f"INSERT INTO {table} ({columns}) VALUES ({marks})", list(values.values()))

    def update(self, table, identity, values):
        assert table in TABLES
        key = "UserId" if table == "MarketProfile" else "Id"
        fields = ", ".join(f"{column} = ?" for column in values)
        self.run(f"UPDATE {table} SET {fields} WHERE {key} = ?", [*values.values(), str(identity)])


@contextmanager
def transaction():
    with get_connection() as connection:
        # Short, transaction-scoped row/range locks protect stock and financial transitions.
        yield Store(connection)


def migrate(store):
    for name, fields in TABLES.items():
        if store.sqlite:
            fields = fields.replace("NVARCHAR(MAX)", "TEXT")
            store.run(f"CREATE TABLE IF NOT EXISTS {name} ({fields})")
        else:
            store.run(f"IF OBJECT_ID(N'dbo.{name}', N'U') IS NULL CREATE TABLE dbo.{name} ({fields})")
    if not store.sqlite:
        store.run("IF COL_LENGTH('dbo.MarketListing','Image') IS NULL ALTER TABLE dbo.MarketListing ADD Image NVARCHAR(200) NOT NULL DEFAULT ''")
        if store.one("SELECT COL_LENGTH('dbo.MarketWithdrawal','RequestKey') AS Size")["Size"] is None:
            store.run("ALTER TABLE dbo.MarketWithdrawal ADD RequestKey NVARCHAR(36) NULL")
            store.run("UPDATE dbo.MarketWithdrawal SET RequestKey=Id WHERE RequestKey IS NULL")
            store.run("ALTER TABLE dbo.MarketWithdrawal ALTER COLUMN RequestKey NVARCHAR(36) NOT NULL")
            store.run("CREATE UNIQUE INDEX IX_MarketWithdrawal_RequestKey ON dbo.MarketWithdrawal(RequestKey)")
    indexes = {
        "MarketListing": [("OwnerId",), ("Status", "Kind")],
        "MarketOrder": [("BuyerId", "Created"), ("SellerId", "Created"), ("ListingId",), ("PaymentStatus", "Status")],
        "MarketEvent": [("RecipientId", "Created"), ("TargetId",)],
        "MarketLedger": [("UserId",)],
        "MarketJob": [("OwnerId",), ("Status",)],
        "MarketMessage": [("OrderId",)],
    }
    for table, definitions in indexes.items():
        for columns in definitions:
            name = "IX_" + table + "_" + "_".join(columns)
            fields = ",".join(columns)
            if store.sqlite:
                store.run(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({fields})")
            else:
                store.run(f"IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name=N'{name}' AND object_id=OBJECT_ID(N'dbo.{table}')) CREATE INDEX {name} ON dbo.{table} ({fields})")
    if store.sqlite:
        store.run("CREATE UNIQUE INDEX IF NOT EXISTS IX_MarketWithdrawal_Reference ON MarketWithdrawal (Reference) WHERE Reference <> ''")
    else:
        store.run("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_MarketWithdrawal_Reference' AND object_id=OBJECT_ID(N'dbo.MarketWithdrawal')) CREATE UNIQUE INDEX IX_MarketWithdrawal_Reference ON dbo.MarketWithdrawal (Reference) WHERE Reference <> ''")


if __name__ == "__main__":
    with transaction() as migration_store:
        migrate(migration_store)
    print(f"Marketplace migration complete: {len(TABLES)} additive tables; legacy tables unchanged.")
