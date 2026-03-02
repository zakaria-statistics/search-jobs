#!/usr/bin/env python3
"""
contact_pipeline.py — Track recruiter/tech lead outreach and follow-ups.

Usage:
    python contact_pipeline.py add       — Add a new contact
    python contact_pipeline.py list      — List all contacts by status
    python contact_pipeline.py update    — Update a contact's status
    python contact_pipeline.py due       — Show follow-ups due today
    python contact_pipeline.py stats     — Outreach statistics
    python contact_pipeline.py export    — Export to Markdown
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

CONTACTS_FILE = Path(__file__).parent.parent / "output" / "contacts.json"

STATUSES = ["New", "Sent", "Connected", "Replied", "Call scheduled", "Referred", "No response", "Not interested"]
CONTACT_TYPES = ["Recruiter", "Tech Lead", "Engineering Manager", "Peer Engineer", "Business Manager", "HR", "Other"]


def load_data():
    if CONTACTS_FILE.exists():
        return json.loads(CONTACTS_FILE.read_text())
    return {"contacts": [], "next_id": 1}


def save_data(data):
    CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONTACTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def add_contact():
    data = load_data()
    print("\n--- Add New Contact ---")
    print(f"Types: {', '.join(f'{i}={t}' for i, t in enumerate(CONTACT_TYPES))}")

    try:
        type_idx = int(input("Contact type (number): "))
        contact_type = CONTACT_TYPES[type_idx]
    except (ValueError, IndexError):
        contact_type = "Other"

    contact = {
        "id": data["next_id"],
        "name": input("Name: ").strip(),
        "company": input("Company: ").strip(),
        "role": input("Their role/title: ").strip(),
        "type": contact_type,
        "platform": input("Platform (LinkedIn/email/event/other): ").strip(),
        "profile_url": input("Profile URL: ").strip(),
        "status": "New",
        "message_sent_date": None,
        "follow_up_1": None,
        "follow_up_2": None,
        "next_follow_up": None,
        "notes": input("Notes: ").strip(),
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
    }
    data["contacts"].append(contact)
    data["next_id"] += 1
    save_data(data)
    print(f"\n+ Added #{contact['id']}: {contact['name']} ({contact['type']}) at {contact['company']}")


def list_contacts():
    data = load_data()
    contacts = data["contacts"]
    if not contacts:
        print("No contacts tracked yet. Use 'add' to start.")
        return

    by_status = {}
    for c in contacts:
        by_status.setdefault(c["status"], []).append(c)

    for status in STATUSES:
        items = by_status.get(status, [])
        if items:
            print(f"\n{'='*55}")
            print(f"  {status.upper()} ({len(items)})")
            print(f"{'='*55}")
            for c in items:
                print(f"  #{c['id']:>3}  {c['name']:<22} {c['company']:<18} [{c['type']}]")
                if c.get("next_follow_up"):
                    print(f"        ↳ Next follow-up: {c['next_follow_up']}")

    print(f"\nTotal contacts: {len(contacts)}")


def update_contact():
    data = load_data()
    try:
        contact_id = int(input("Contact ID to update: "))
    except ValueError:
        print("Invalid ID.")
        return

    contact = next((c for c in data["contacts"] if c["id"] == contact_id), None)
    if not contact:
        print(f"Contact #{contact_id} not found.")
        return

    print(f"\nCurrent: #{contact['id']} — {contact['name']} at {contact['company']} [{contact['status']}]")
    print(f"Statuses: {', '.join(f'{i}={s}' for i, s in enumerate(STATUSES))}")

    try:
        status_idx = int(input("New status (number): "))
        new_status = STATUSES[status_idx]
    except (ValueError, IndexError):
        print("Invalid status.")
        return

    old_status = contact["status"]
    contact["status"] = new_status
    contact["updated"] = datetime.now().isoformat()

    # Auto-schedule follow-ups based on cadence
    today = datetime.now().strftime("%Y-%m-%d")
    if new_status == "Sent" and not contact["message_sent_date"]:
        contact["message_sent_date"] = today
        contact["next_follow_up"] = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        print(f"  → Message sent. Follow-up #1 scheduled for {contact['next_follow_up']}")
    elif new_status == "Sent" and contact["message_sent_date"] and not contact["follow_up_1"]:
        contact["follow_up_1"] = today
        contact["next_follow_up"] = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        print(f"  → Follow-up #1 sent. Follow-up #2 scheduled for {contact['next_follow_up']}")
    elif new_status == "Sent" and contact["follow_up_1"] and not contact["follow_up_2"]:
        contact["follow_up_2"] = today
        contact["next_follow_up"] = None
        print(f"  → Follow-up #2 sent. Max follow-ups reached.")

    notes = input("Notes (enter to skip): ").strip()
    if notes:
        contact["notes"] = (contact.get("notes", "") + f" | {today}: {notes}").strip(" |")

    manual_follow_up = input("Override next follow-up date (YYYY-MM-DD, enter to skip): ").strip()
    if manual_follow_up:
        contact["next_follow_up"] = manual_follow_up

    save_data(data)
    print(f"\n+ Updated #{contact_id}: {old_status} -> {new_status}")


def show_due():
    data = load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    due = [
        c for c in data["contacts"]
        if c.get("next_follow_up") and c["next_follow_up"] <= today
        and c["status"] not in ("Referred", "No response", "Not interested")
    ]

    if not due:
        print("No follow-ups due today.")
        return

    print(f"\n{'='*45}")
    print(f"  CONTACT FOLLOW-UPS DUE ({today})")
    print(f"{'='*45}")
    for c in due:
        print(f"  #{c['id']:>3}  {c['name']:<22} {c['company']:<18} [{c['status']}]")
        print(f"        Platform: {c.get('platform','')}  |  Due: {c['next_follow_up']}")
        if c.get("profile_url"):
            print(f"        URL: {c['profile_url']}")
        print()


def show_stats():
    data = load_data()
    contacts = data["contacts"]
    if not contacts:
        print("No data yet.")
        return

    total = len(contacts)
    by_status = {}
    for c in contacts:
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1

    by_type = {}
    for c in contacts:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1

    by_company = {}
    for c in contacts:
        by_company[c["company"]] = by_company.get(c["company"], 0) + 1

    print(f"\n{'='*40}")
    print(f"  CONTACT PIPELINE STATS")
    print(f"{'='*40}")
    print(f"\n  Total contacts: {total}")

    print(f"\n  By Status:")
    for s in STATUSES:
        count = by_status.get(s, 0)
        if count:
            bar = "█" * count
            print(f"    {s:<16} {count:>3}  {bar}")

    print(f"\n  By Type:")
    for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {t:<22} {count:>3}")

    print(f"\n  By Company (top 10):")
    for company, count in sorted(by_company.items(), key=lambda x: -x[1])[:10]:
        print(f"    {company:<22} {count:>3}")

    # Conversion
    sent = sum(1 for c in contacts if c["status"] not in ("New",))
    replied = sum(1 for c in contacts if c["status"] in ("Replied", "Call scheduled", "Referred"))
    if sent:
        print(f"\n  Reply rate: {replied}/{sent} = {replied/sent*100:.0f}%")


def export_markdown():
    data = load_data()
    contacts = data["contacts"]
    if not contacts:
        print("No data to export.")
        return

    out = Path(__file__).parent.parent / "output" / "contacts_export.md"
    lines = [
        f"# Contact Pipeline Export — {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "| # | Name | Company | Role | Type | Platform | Status | Sent | Follow-up |",
        "|---|------|---------|------|------|----------|--------|------|-----------|",
    ]
    for c in contacts:
        lines.append(
            f"| {c['id']} | {c['name']} | {c['company']} | {c['role']} | {c['type']} "
            f"| {c.get('platform','')} | **{c['status']}** | {c.get('message_sent_date','—')} "
            f"| {c.get('next_follow_up','—')} |"
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"+ Exported to {out}")


COMMANDS = {
    "add": add_contact,
    "list": list_contacts,
    "update": update_contact,
    "due": show_due,
    "stats": show_stats,
    "export": export_markdown,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
