import argparse

from .store import demo_store, export_notes, list_notes


def show_notes(db, owner):
    notes = list_notes(db, owner)
    print(f"Notes visible to {owner} ({len(notes)}):")
    for note in notes:
        print(f"- {note['title']}: {note['body']}")
    if not notes:
        print("(none)")


def main():
    parser = argparse.ArgumentParser(description="Notebin: private notes per user")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="show Alice's sample notes")
    listing = commands.add_parser("list", help="list one user's sample notes")
    listing.add_argument("owner")
    exporting = commands.add_parser("export", help="export one user's sample notes as CSV")
    exporting.add_argument("owner")
    args = parser.parse_args()
    db = demo_store()
    try:
        if args.command == "demo":
            show_notes(db, "alice")
        elif args.command == "list":
            show_notes(db, args.owner)
        elif args.command == "export":
            print(f"CSV export for {args.owner}:")
            print(export_notes(db, args.owner), end="")
    finally:
        db.close()


if __name__ == "__main__":
    main()
