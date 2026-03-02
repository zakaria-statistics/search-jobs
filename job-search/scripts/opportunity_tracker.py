#!/usr/bin/env python3
"""
opportunity_tracker.py — Track job applications, statuses, and stats.

Usage:
    python opportunity_tracker.py add       — Add a new opportunity
    python opportunity_tracker.py list      — List all opportunities
    python opportunity_tracker.py update    — Update status of an opportunity
    python opportunity_tracker.py stats     — Show application statistics
    python opportunity_tracker.py export    — Export to Markdown table
    python opportunity_tracker.py due       — Show follow-ups due today
    python opportunity_tracker.py import    — Import ranked jobs from JSON file
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

TRACKER_FILE = Path(__file__).parent.parent / "output" / "opportunities.json"

STATUSES = ["New", "Applied", "Screening", "Interview", "Technical", "Offer", "Accepted", "Rejected", "Withdrawn"]


def load_data():
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text())
    return {"opportunities": [], "next_id": 1}


def save_data(data):
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def add_opportunity():
    data = load_data()
    print("\n--- Add New Opportunity ---")
    opp = {
        "id": data["next_id"],
        "company": input("Company: ").strip(),
        "role": input("Role: ").strip(),
        "location": input("Location: ").strip(),
        "remote": input("Remote? (remote/hybrid/onsite): ").strip().lower(),
        "contract": input("Contract (CDI/freelance): ").strip(),
        "source": input("Source (LinkedIn/WTTJ/Indeed/career page/referral/other): ").strip(),
        "url": input("Job URL: ").strip(),
        "salary": input("Salary/TJM (if known): ").strip(),
        "status": "New",
        "applied_date": None,
        "follow_up_date": None,
        "notes": input("Notes: ").strip(),
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "history": [],
    }
    data["opportunities"].append(opp)
    data["next_id"] += 1
    save_data(data)
    print(f"\n✓ Added #{opp['id']}: {opp['role']} at {opp['company']}")


def list_opportunities():
    data = load_data()
    opps = data["opportunities"]
    if not opps:
        print("No opportunities tracked yet. Use 'add' to start.")
        return

    # Group by status
    by_status = {}
    for opp in opps:
        by_status.setdefault(opp["status"], []).append(opp)

    for status in STATUSES:
        items = by_status.get(status, [])
        if items:
            print(f"\n{'='*50}")
            print(f"  {status.upper()} ({len(items)})")
            print(f"{'='*50}")
            for o in items:
                remote_tag = f"[{o['remote']}]" if o.get("remote") else ""
                print(f"  #{o['id']:>3}  {o['company']:<20} {o['role']:<25} {o['location']:<15} {remote_tag}")
                if o.get("follow_up_date"):
                    print(f"        ↳ Follow-up: {o['follow_up_date']}")

    print(f"\nTotal: {len(opps)} opportunities")


def update_opportunity():
    data = load_data()
    try:
        opp_id = int(input("Opportunity ID to update: "))
    except ValueError:
        print("Invalid ID.")
        return

    opp = next((o for o in data["opportunities"] if o["id"] == opp_id), None)
    if not opp:
        print(f"Opportunity #{opp_id} not found.")
        return

    print(f"\nCurrent: #{opp['id']} — {opp['role']} at {opp['company']} [{opp['status']}]")
    print(f"Statuses: {', '.join(f'{i}={s}' for i, s in enumerate(STATUSES))}")

    try:
        status_idx = int(input("New status (number): "))
        new_status = STATUSES[status_idx]
    except (ValueError, IndexError):
        print("Invalid status.")
        return

    old_status = opp["status"]
    opp["status"] = new_status
    opp["updated"] = datetime.now().isoformat()
    opp["history"].append({
        "from": old_status,
        "to": new_status,
        "date": datetime.now().isoformat(),
    })

    if new_status == "Applied" and not opp["applied_date"]:
        opp["applied_date"] = datetime.now().strftime("%Y-%m-%d")
        # Auto-set follow-up in 5 days
        opp["follow_up_date"] = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        print(f"  → Applied date set. Follow-up scheduled for {opp['follow_up_date']}")

    notes = input("Notes (enter to skip): ").strip()
    if notes:
        opp["notes"] = (opp.get("notes", "") + f" | {datetime.now().strftime('%m/%d')}: {notes}").strip(" |")

    follow_up = input("Set follow-up date (YYYY-MM-DD, enter to skip): ").strip()
    if follow_up:
        opp["follow_up_date"] = follow_up

    save_data(data)
    print(f"\n✓ Updated #{opp_id}: {old_status} → {new_status}")


def show_stats():
    data = load_data()
    opps = data["opportunities"]
    if not opps:
        print("No data yet.")
        return

    total = len(opps)
    by_status = {}
    for o in opps:
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1

    by_source = {}
    for o in opps:
        by_source[o.get("source", "unknown")] = by_source.get(o.get("source", "unknown"), 0) + 1

    by_company = {}
    for o in opps:
        by_company[o["company"]] = by_company.get(o["company"], 0) + 1

    print(f"\n{'='*40}")
    print(f"  APPLICATION STATISTICS")
    print(f"{'='*40}")
    print(f"\n  Total opportunities: {total}")

    print(f"\n  By Status:")
    for s in STATUSES:
        count = by_status.get(s, 0)
        if count:
            bar = "█" * count
            print(f"    {s:<12} {count:>3}  {bar}")

    print(f"\n  By Source:")
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"    {source:<20} {count:>3}")

    print(f"\n  By Company (top 10):")
    for company, count in sorted(by_company.items(), key=lambda x: -x[1])[:10]:
        print(f"    {company:<20} {count:>3}")

    # Response rate
    applied = sum(1 for o in opps if o["status"] not in ("New",))
    responses = sum(1 for o in opps if o["status"] in ("Screening", "Interview", "Technical", "Offer", "Accepted"))
    if applied:
        print(f"\n  Response rate: {responses}/{applied} = {responses/applied*100:.0f}%")


def export_markdown():
    data = load_data()
    opps = data["opportunities"]
    if not opps:
        print("No data to export.")
        return

    out = Path(__file__).parent.parent / "output" / "opportunities_export.md"
    lines = [
        f"# Opportunities Export — {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "| # | Company | Role | Location | Remote | Contract | Source | Status | Applied | Follow-up |",
        "|---|---------|------|----------|--------|----------|--------|--------|---------|-----------|",
    ]
    for o in opps:
        lines.append(
            f"| {o['id']} | {o['company']} | {o['role']} | {o['location']} | {o.get('remote','')} "
            f"| {o.get('contract','')} | {o.get('source','')} | **{o['status']}** "
            f"| {o.get('applied_date','—')} | {o.get('follow_up_date','—')} |"
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"✓ Exported to {out}")


def show_due():
    data = load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    due = [o for o in data["opportunities"] if o.get("follow_up_date") and o["follow_up_date"] <= today and o["status"] not in ("Accepted", "Rejected", "Withdrawn")]

    if not due:
        print("No follow-ups due today.")
        return

    print(f"\n{'='*40}")
    print(f"  FOLLOW-UPS DUE ({today})")
    print(f"{'='*40}")
    for o in due:
        print(f"  #{o['id']:>3}  {o['company']:<20} {o['role']:<25} [{o['status']}]")
        print(f"        Follow-up date: {o['follow_up_date']}")
        if o.get("notes"):
            print(f"        Notes: {o['notes'][:80]}")
        print()


def import_ranked():
    """Import jobs from a ranked JSON file into the tracker."""
    if len(sys.argv) < 3:
        # Auto-find latest ranked file
        output_dir = Path(__file__).parent.parent / "output"
        ranked_files = sorted(output_dir.glob("ranked_*.json"), reverse=True)
        if not ranked_files:
            print("No ranked files found. Provide a path: python opportunity_tracker.py import --file <path>")
            return
        filepath = ranked_files[0]
    else:
        # Check for --file flag
        if "--file" in sys.argv:
            idx = sys.argv.index("--file")
            if idx + 1 < len(sys.argv):
                filepath = Path(sys.argv[idx + 1])
            else:
                print("Missing file path after --file")
                return
        else:
            filepath = Path(sys.argv[2])

    if not filepath.exists():
        print(f"File not found: {filepath}")
        return

    ranked_data = json.loads(filepath.read_text())
    ranked_jobs = ranked_data.get("ranked_jobs", [])
    if not ranked_jobs:
        print("No ranked jobs found in file.")
        return

    data = load_data()
    existing_urls = {o.get("url") for o in data["opportunities"]}

    imported = 0
    skipped = 0
    for job in ranked_jobs:
        url = job.get("url", "")
        if url in existing_urls:
            skipped += 1
            continue

        opp = {
            "id": data["next_id"],
            "company": job.get("company", ""),
            "role": job.get("title", ""),
            "location": job.get("location", ""),
            "remote": "",
            "contract": "",
            "source": "scraper",
            "url": url,
            "salary": "",
            "status": "New",
            "applied_date": None,
            "follow_up_date": None,
            "notes": f"Score: {job.get('scores', {}).get('overall', '?')}/100 | "
                     f"Priority: {job.get('priority', '?')} | "
                     f"Skills: {', '.join(job.get('matching_skills', [])[:5])}",
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "history": [],
        }
        data["opportunities"].append(opp)
        data["next_id"] += 1
        existing_urls.add(url)
        imported += 1

    save_data(data)
    print(f"\nImported {imported} jobs ({skipped} duplicates skipped) from {filepath.name}")


COMMANDS = {
    "add": add_opportunity,
    "list": list_opportunities,
    "update": update_opportunity,
    "stats": show_stats,
    "export": export_markdown,
    "due": show_due,
    "import": import_ranked,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
