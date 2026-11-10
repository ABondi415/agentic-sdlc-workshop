import csv
import io
import sqlite3


def connect():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY,
            owner TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL
        )
    """)
    return db


def add_note(db, owner, title, body):
    if not owner or not title:
        raise ValueError("owner and title are required")
    db.execute(
        "INSERT INTO notes (owner, title, body) VALUES (?, ?, ?)",
        (owner, title, body),
    )


def list_notes(db, owner):
    rows = db.execute(
        "SELECT id, owner, title, body FROM notes WHERE owner = ? ORDER BY id",
        (owner,),
    ).fetchall()
    return [dict(row) for row in rows]


def demo_store():
    db = connect()
    add_note(db, "alice", "Shopping", "Buy tea and apples")
    add_note(db, "bob", "Private", "Surprise party on Friday")
    add_note(db, "alice", "Reading", "Finish chapter three")
    return db


def export_notes(db, owner):
    """Download a user's notes as CSV, in creation order."""
    rows = db.execute("SELECT owner, title, body FROM notes ORDER BY id").fetchall()
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["owner", "title", "body"])
    writer.writerows(tuple(row) for row in rows)
    return output.getvalue()
