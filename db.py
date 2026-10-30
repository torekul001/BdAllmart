from contextlib import contextmanager

import pyodbc

from config import get_pyodbc_connection_string


@contextmanager
def get_connection():
    conn = pyodbc.connect(get_pyodbc_connection_string(), timeout=2)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_one(query, params=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        row = cursor.fetchone()
        if row is None:
            return None
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))


def fetch_all(query, params=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def execute(query, params=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        return cursor.rowcount
