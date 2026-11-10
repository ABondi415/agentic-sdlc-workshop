import csv
import io
import unittest

from notebin.store import add_note, connect, demo_store, export_notes, list_notes


class NotesTests(unittest.TestCase):
    def setUp(self):
        self.db = demo_store()
        self.addCleanup(self.db.close)

    def test_alice_sees_only_her_notes(self):
        notes = list_notes(self.db, "alice")
        self.assertEqual([n["title"] for n in notes], ["Shopping", "Reading"])
        self.assertTrue(all(n["owner"] == "alice" for n in notes))

    def test_bob_sees_only_his_note(self):
        notes = list_notes(self.db, "bob")
        self.assertEqual([n["title"] for n in notes], ["Private"])

    def test_unknown_user_sees_nothing(self):
        self.assertEqual(list_notes(self.db, "charlie"), [])

    def test_quoted_owner_is_not_sql(self):
        self.assertEqual(list_notes(self.db, "alice' OR 1=1 --"), [])

    def test_quotes_in_a_note_are_preserved(self):
        add_note(self.db, "alice", "Today's task", "Don't forget")
        note = list_notes(self.db, "alice")[-1]
        self.assertEqual((note["title"], note["body"]), ("Today's task", "Don't forget"))

    def test_blank_owner_is_rejected(self):
        with self.assertRaises(ValueError):
            add_note(self.db, "", "Title", "Body")

    def test_blank_title_is_rejected(self):
        with self.assertRaises(ValueError):
            add_note(self.db, "alice", "", "Body")

    def test_export_as_csv(self):
        db = connect()
        self.addCleanup(db.close)
        add_note(db, "alice", "Shopping", "Tea, apples")
        rows = list(csv.DictReader(io.StringIO(export_notes(db, "alice"))))
        self.assertEqual(rows, [{"owner": "alice", "title": "Shopping", "body": "Tea, apples"}])

    def test_new_database_is_empty(self):
        db = connect()
        self.addCleanup(db.close)
        self.assertEqual(list_notes(db, "alice"), [])


if __name__ == "__main__":
    unittest.main()
