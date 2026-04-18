"""KuzuDB graph store connection and schema."""

import logging
from pathlib import Path

import kuzu

logger = logging.getLogger(__name__)

# Schema definitions
SCHEMA_QUERIES = [
    # Node table
    """
    CREATE NODE TABLE IF NOT EXISTS Symbol (
        id STRING PRIMARY KEY,
        kind STRING,
        name STRING,
        fqn STRING,
        file_path STRING,
        line_start INT64,
        line_end INT64,
        language STRING,
        project_id STRING,
        last_run_id STRING,
        docstring STRING,
        source_hash STRING,
        properties STRING
    )
    """,
    # Relationship table
    """
    CREATE REL TABLE IF NOT EXISTS Edge (
        FROM Symbol TO Symbol,
        type STRING,
        confidence STRING,
        file_path STRING,
        line INT64,
        extractor STRING,
        target_hint STRING,
        last_run_id STRING,
        extra STRING
    )
    """,
    # Indexes
    "CREATE INDEX IF NOT EXISTS ON Symbol(project_id)",
    "CREATE INDEX IF NOT EXISTS ON Symbol(file_path)",
    "CREATE INDEX IF NOT EXISTS ON Symbol(name)",
    "CREATE INDEX IF NOT EXISTS ON Symbol(fqn)",
    "CREATE INDEX IF NOT EXISTS ON Symbol(kind)",
    "CREATE INDEX IF NOT EXISTS ON Symbol(project_id, kind)",
    "CREATE INDEX IF NOT EXISTS ON Edge(type)",
    "CREATE INDEX IF NOT EXISTS ON Edge(confidence)",
]


class GraphStore:
    """KuzuDB graph store wrapper."""

    def __init__(self, db_path: Path):
        """
        Initialize graph store.

        Args:
            db_path: Path to KuzuDB database directory
        """
        logger.info(f"[GraphStore] Initializing with db_path={db_path}")
        self.db_path = db_path
        self.conn: kuzu.Connection | None = None
        self.db: kuzu.Database | None = None

    def connect(self) -> None:
        """Connect to the database and initialize schema."""
        logger.info(f"[GraphStore] Connecting to database at {self.db_path}")
        self.db = kuzu.Database(str(self.db_path))
        self.conn = kuzu.Connection(self.db)
        logger.info(f"[GraphStore] Connected successfully")
        self._init_schema()

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
        if self.db:
            self.db.close()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        logger.info(f"[GraphStore] Initializing schema with {len(SCHEMA_QUERIES)} queries")
        for i, query in enumerate(SCHEMA_QUERIES):
            try:
                self.conn.execute(query)
                logger.debug(f"[GraphStore] Schema query {i+1}/{len(SCHEMA_QUERIES)} executed successfully")
            except Exception as e:
                # Some indexes might already exist
                logger.debug(f"Schema init (may be existing): {e}")
        logger.info(f"[GraphStore] Schema initialization complete")

    def execute(self, query: str, parameters: dict | None = None) -> kuzu.QueryResult:
        """
        Execute a query.

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            Query result
        """
        if parameters:
            return self.conn.execute(query, parameters)
        return self.conn.execute(query)

    def begin_transaction(self) -> kuzu.Connection:
        """Begin a transaction - returns self for context management."""
        # Kuzu Python API doesn't have explicit transactions in older versions
        # Operations are auto-committed
        return self.conn

    def commit_transaction(self, conn: kuzu.Connection) -> None:
        """Commit a transaction (no-op for auto-commit)."""
        pass

    def rollback_transaction(self, conn: kuzu.Connection) -> None:
        """Rollback a transaction (no-op for auto-commit)."""
        pass
