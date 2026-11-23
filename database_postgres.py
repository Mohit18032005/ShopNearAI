
import os
import re
import psycopg


class HybridRow(dict):
    """Supports both row['column'] and row[0]."""

    def __init__(self, names, values):
        super().__init__(zip(names, values))
        self._values = tuple(values)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


def hybrid_row_factory(cursor):
    def make_row(values):
        names = [column.name for column in cursor.description]
        return HybridRow(names, values)
    return make_row


def prepare_query(query):
    query = re.sub(r"\?", "%s", query)

    # PostgreSQL equivalent of SQLite INSERT OR IGNORE
    query = re.sub(
        r"INSERT\s+OR\s+IGNORE\s+INTO",
        "INSERT INTO",
        query,
        flags=re.IGNORECASE
    )

    if re.search(r"INSERT\s+INTO\s+platform_settings\b", query, re.IGNORECASE):
        if "ON CONFLICT" not in query.upper():
            query = query.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

    return query


class PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, query, params=None):
        query = prepare_query(query)
        self.lastrowid = None

        is_reservation_insert = bool(
            re.search(r"INSERT\s+INTO\s+reservations\b", query, re.IGNORECASE)
        )

        if is_reservation_insert and "RETURNING" not in query.upper():
            query = query.rstrip().rstrip(";") + " RETURNING id"

            if params is None:
                self._cursor.execute(query)
            else:
                self._cursor.execute(query, params)

            result = self._cursor.fetchone()
            if result:
                self.lastrowid = result[0]
            return self

        if params is None:
            self._cursor.execute(query)
        else:
            self._cursor.execute(query, params)

        return self

    def executemany(self, query, params):
        self._cursor.executemany(prepare_query(query), params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount


class PostgresConnection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return PostgresCursor(self._connection.cursor())

    def execute(self, query, params=None):
        query = prepare_query(query)
        query = query.replace("BEGIN IMMEDIATE", "BEGIN")

        if params is None:
            return self._connection.execute(query)
        return self._connection.execute(query, params)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


def get_connection():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    key = k.strip()
                    val = v.strip().strip("'").strip('"')
                    if key == "DATABASE_URL" or key not in os.environ:
                        os.environ[key] = val

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is missing.")

    connection = psycopg.connect(
        database_url,
        row_factory=hybrid_row_factory,
        sslmode="require"
    )

    return PostgresConnection(connection)


def initialize_database():
    """Verify that the migrated Neon tables already exist."""
    connection = get_connection()
    cursor = connection.cursor()

    required_tables = [
        "users",
        "shops",
        "products",
        "categories",
        "reservations",
        "bargaining_requests",
        "platform_settings"
    ]

    for table in required_tables:
        cursor.execute("SELECT to_regclass(?)", (f"public.{table}",))
        if cursor.fetchone()[0] is None:
            connection.close()
            raise RuntimeError(
                f"Required Neon table is missing: {table}"
            )

    connection.close()
