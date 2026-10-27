"""Apply the idempotent multi-cloud profile/evidence seed to the local SQLite DB."""

import sqlite3

import database


def main() -> None:
    database.init_db()
    try:
        database.seed_multicloud_profile()
    except ValueError as exc:
        raise SystemExit(f"{exc} First run `python database.py` to create a profile.")

    with sqlite3.connect(database.DB_FILE) as conn:
        profile = conn.execute(
            "SELECT core_tech_stack FROM master_profile ORDER BY id LIMIT 1"
        ).fetchone()
        claims = conn.execute(
            """SELECT competency, target_persona, evidence_status
               FROM profile_evidence ORDER BY id"""
        ).fetchall()

    print("Current master profile tech stack:")
    print(profile[0])
    print("Saved profile evidence (all self-reported unless later updated):")
    for competency, persona, status in claims:
        print(f"- {competency} | persona={persona} | status={status}")


if __name__ == "__main__":
    main()
