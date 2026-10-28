import sqlite3
from datetime import date
import json
from pathlib import Path

DB_FILE = str(Path(__file__).resolve().parent / "jobgs_engine.db")


def _create_job_tables(cursor):
    """Create additive Week 2 company-inventory and job-triage tables."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            domain TEXT NOT NULL DEFAULT '',
            hq TEXT NOT NULL DEFAULT '',
            vertical TEXT NOT NULL DEFAULT '',
            company_size TEXT NOT NULL DEFAULT '',
            tech_stack_json TEXT NOT NULL DEFAULT '{}',
            careers_url TEXT NOT NULL DEFAULT '',
            core_services_json TEXT NOT NULL DEFAULT '[]',
            source_provenance TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Upgrade existing local databases in place; do not discard inventory rows.
    company_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(companies_inventory)").fetchall()
    }
    if "core_services_json" not in company_columns:
        cursor.execute(
            "ALTER TABLE companies_inventory "
            "ADD COLUMN core_services_json TEXT NOT NULL DEFAULT '[]'"
        )
    if "source_provenance" not in company_columns:
        cursor.execute(
            "ALTER TABLE companies_inventory "
            "ADD COLUMN source_provenance TEXT NOT NULL DEFAULT ''"
        )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS application_tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies_inventory(id),
            company_name TEXT NOT NULL,
            role_title TEXT NOT NULL,
            job_url TEXT NOT NULL UNIQUE,
            location TEXT NOT NULL DEFAULT '',
            work_model TEXT NOT NULL DEFAULT 'Unknown'
                CHECK (work_model IN ('Remote', 'Hybrid', 'On-site', 'Unknown')),
            raw_description TEXT NOT NULL,
            assigned_persona TEXT NOT NULL DEFAULT 'Unclear'
                CHECK (assigned_persona IN ('Director', 'Architect', 'TPM', 'Unclear')),
            domain_tags_json TEXT NOT NULL DEFAULT '[]',
            triage_json TEXT NOT NULL DEFAULT '{}',
            rag_results_json TEXT NOT NULL DEFAULT '{}',
            transferable_bridges_json TEXT NOT NULL DEFAULT '[]',
            outreach_draft TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'DISCOVERED'
                CHECK (status IN ('DISCOVERED', 'REVIEWED', 'APPLIED', 'INTERVIEW', 'OFFER', 'REJECTED', 'WITHDRAWN')),
            human_reviewed_at TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_application_tracker_status_created "
        "ON application_tracker(status, created_at DESC)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_application_tracker_persona "
        "ON application_tracker(assigned_persona)"
    )


def init_job_tables():
    """Idempotently ensure Week 2 tables exist for an already initialized DB."""
    conn = sqlite3.connect(DB_FILE, timeout=10)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            _create_job_tables(conn.cursor())
    finally:
        conn.close()

def init_db():
    """Initialize SQLite database tables for Master Profile & Daily Target Tracking."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # 1. Master Profile Table (Immutable Single Profile)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            title TEXT NOT NULL,
            years_experience INTEGER NOT NULL,
            location TEXT NOT NULL,
            notice_period_days INTEGER NOT NULL,
            min_ctc_lpa REAL NOT NULL,
            video_pitch_url TEXT,
            core_domains TEXT, -- Stored as JSON string
            core_tech_stack TEXT -- Stored as JSON string
        )
    ''')

    # 2. Daily Applications & Limit Governor Table (Max 10 per day)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apply_date TEXT NOT NULL,
            company_name TEXT NOT NULL,
            role_title TEXT NOT NULL,
            job_url TEXT,
            match_score REAL NOT NULL, -- Legacy name; new rows store profile-term coverage here.
            status TEXT DEFAULT 'USER_REVIEWED',
            context_footer TEXT,
            hrbp_contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Week 2 role intake is separate from daily_applications: discovering or
    # triaging a vacancy does not count as applying to it.
    _create_job_tables(cursor)

    # 3. Candidate-provided claims linked to concise evidence notes.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL REFERENCES master_profile(id) ON DELETE CASCADE,
            competency TEXT NOT NULL,
            claim TEXT NOT NULL,
            context TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL,
            impact_metric TEXT NOT NULL DEFAULT '',
            source_reference TEXT NOT NULL DEFAULT '',
            target_persona TEXT NOT NULL DEFAULT 'All'
                CHECK (target_persona IN ('All', 'Director', 'Architect', 'TPM')),
            evidence_status TEXT NOT NULL DEFAULT 'self_reported'
                CHECK (evidence_status IN ('self_reported', 'reference_added', 'supporting_material_noted')),
            confidentiality TEXT NOT NULL DEFAULT 'private'
                CHECK (confidentiality IN ('public', 'private', 'confidential')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Add the persona field to existing local databases without discarding claims.
    evidence_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(profile_evidence)").fetchall()
    }
    if "target_persona" not in evidence_columns:
        cursor.execute('''
            ALTER TABLE profile_evidence
            ADD COLUMN target_persona TEXT NOT NULL DEFAULT 'All'
                CHECK (target_persona IN ('All', 'Director', 'Architect', 'TPM'))
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transferable_tech_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_technology TEXT NOT NULL,
            source_technology TEXT NOT NULL,
            relationship TEXT NOT NULL,
            bridge_template TEXT NOT NULL,
            target_persona TEXT NOT NULL DEFAULT 'All'
                CHECK (target_persona IN ('All', 'Director', 'Architect', 'TPM')),
            review_status TEXT NOT NULL DEFAULT 'suggested'
                CHECK (review_status IN ('suggested', 'approved', 'rejected')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (target_technology, source_technology, target_persona)
        )
    ''')

    # These are reviewable adjacency suggestions, not declarations of candidate skill.
    cursor.executemany(
        """INSERT OR IGNORE INTO transferable_tech_mapping
           (target_technology, source_technology, relationship, bridge_template,
            target_persona, review_status)
           VALUES (?, ?, ?, ?, 'All', 'suggested')""",
        [
            ("Snowflake", "BigQuery", "cloud data warehouse concepts",
             "The recorded {source} evidence may offer concepts relevant to {target}; review whether the claim's scope supports that comparison. It does not establish hands-on {target} use."),
            ("AWS", "GCP", "cloud architecture concepts",
             "The recorded {source} evidence may offer concepts relevant to {target}; review whether the claim's scope supports that comparison. It does not establish hands-on {target} use."),
            ("AWS", "Azure", "cloud architecture concepts",
             "The recorded {source} evidence may offer concepts relevant to {target}; review whether the claim's scope supports that comparison. It does not establish hands-on {target} use."),
            ("Redshift", "BigQuery", "cloud data warehouse concepts",
             "The recorded {source} evidence may offer concepts relevant to {target}; review whether the claim's scope supports that comparison. It does not establish hands-on {target} use."),
            ("Azure", "GCP", "cloud architecture concepts",
             "The recorded {source} evidence may offer concepts relevant to {target}; review whether the claim's scope supports that comparison. It does not establish hands-on {target} use."),
            ("Azure", "AWS", "cloud architecture concepts",
             "The recorded {source} evidence may offer concepts relevant to {target}; review whether the claim's scope supports that comparison. It does not establish hands-on {target} use."),
            ("GCP", "AWS", "cloud architecture concepts",
             "The recorded {source} evidence may offer concepts relevant to {target}; review whether the claim's scope supports that comparison. It does not establish hands-on {target} use."),
            ("GCP", "Azure", "cloud architecture concepts",
             "The recorded {source} evidence may offer concepts relevant to {target}; review whether the claim's scope supports that comparison. It does not establish hands-on {target} use."),
        ],
    )

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")

def seed_master_profile():
    """Populate a generic starter profile when the profile table is empty."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM master_profile")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO master_profile (
                full_name, title, years_experience, location, notice_period_days, min_ctc_lpa, video_pitch_url, core_domains, core_tech_stack
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "Example Candidate",
            "BI Platform Delivery Manager / Principal Cloud Architect",
            15,
            "Your City",
            60,
            0.0,
            "",
            json.dumps([]),
            json.dumps({
                "database": [],
                "cloud": ["GCP", "AWS", "Azure"],
                "analytics": [],
                "core": ["Multi-cloud Architecture", "Cloud Transformation", "Data Engineering"],
            })
        ))
        conn.commit()
        print("✅ Master Profile seeded successfully.")
    else:
        print("ℹ️ Master Profile already exists.")

    conn.close()
    seed_multicloud_profile()


MULTICLOUD_PROFILE_CLAIMS = (
    {
        "competency": "Multi-cloud architecture",
        "claim": "I have 6+ years of hands-on architecture experience across GCP, AWS, and Azure in executive platform transformation roles.",
        "context": "Executive platform transformation roles; add specific projects and dates when appropriate.",
        "evidence_summary": "Candidate-reported experience statement. Add non-confidential project examples and supporting references before reusing this claim in application materials.",
        "impact_metric": "6+ years (candidate reported)",
    },
    {
        "competency": "Multi-cloud transformation",
        "claim": "My hands-on platform transformation work spans GCP, AWS, and Azure.",
        "context": "Executive platform transformation roles; add specific platform scope and outcomes when appropriate.",
        "evidence_summary": "Candidate-reported experience statement. Add non-confidential project examples and supporting references before reusing this claim in application materials.",
        "impact_metric": "",
    },
    {
        "competency": "Multi-cloud data engineering",
        "claim": "My hands-on data engineering experience spans services and platforms across GCP, AWS, and Azure.",
        "context": "Add the specific data platforms, services, and role context before using this claim in a resume.",
        "evidence_summary": "Candidate-reported foundational claim. Specific tools, project examples, and supporting references have not yet been recorded.",
        "impact_metric": "",
    },
)


def seed_multicloud_profile():
    """Idempotently add the candidate-reported multi-cloud stack and evidence claims."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    profile = cursor.execute(
        "SELECT id, core_tech_stack FROM master_profile ORDER BY id LIMIT 1"
    ).fetchone()
    if profile is None:
        conn.close()
        raise ValueError("Master profile not found. Run seed_master_profile() first.")

    profile_id, stack_json = profile
    tech_stack = json.loads(stack_json or "{}")
    if not isinstance(tech_stack, dict):
        tech_stack = {}
    for category, values in {
        "cloud": ["GCP", "AWS", "Azure"],
        "core": ["Multi-cloud Architecture", "Cloud Transformation", "Data Engineering"],
    }.items():
        existing = tech_stack.get(category)
        existing = existing if isinstance(existing, list) else []
        tech_stack[category] = list(dict.fromkeys(
            [item for item in existing if isinstance(item, str)] + values
        ))

    cursor.execute(
        "UPDATE master_profile SET core_tech_stack = ? WHERE id = ?",
        (json.dumps(tech_stack), profile_id),
    )

    for claim in MULTICLOUD_PROFILE_CLAIMS:
        existing = cursor.execute(
            """SELECT 1 FROM profile_evidence
               WHERE profile_id = ? AND competency = ? AND claim = ? AND target_persona = 'All'
               LIMIT 1""",
            (profile_id, claim["competency"], claim["claim"]),
        ).fetchone()
        if existing:
            continue
        cursor.execute(
            """INSERT INTO profile_evidence (
                   profile_id, competency, claim, context, evidence_summary,
                   impact_metric, source_reference, target_persona,
                   evidence_status, confidentiality
               ) VALUES (?, ?, ?, ?, ?, ?, ?, 'All', 'self_reported', 'private')""",
            (
                profile_id,
                claim["competency"],
                claim["claim"],
                claim["context"],
                claim["evidence_summary"],
                claim["impact_metric"],
                "Candidate-provided JobG's profile update (2026-10-27)",
            ),
        )

    conn.commit()
    conn.close()
    print("✅ Multi-cloud profile stack and self-reported evidence seeded.")

def check_daily_limit():
    """Check how many target applications have been processed today (Max 10)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    today_str = date.today().isoformat()

    cursor.execute("SELECT COUNT(*) FROM daily_applications WHERE apply_date = ?", (today_str,))
    count = cursor.fetchone()[0]
    conn.close()

    remaining = max(0, 10 - count)
    return {"today_count": count, "remaining_slots": remaining, "can_apply": remaining > 0}

if __name__ == "__main__":
    init_db()
    seed_master_profile()
    status = check_daily_limit()
    print(f"📊 Daily Governor Status: {status['today_count']}/10 applied today ({status['remaining_slots']} slots remaining).")
