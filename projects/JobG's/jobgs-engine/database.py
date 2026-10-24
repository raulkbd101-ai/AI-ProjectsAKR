import sqlite3
from datetime import date
import json

DB_FILE = "jobgs_engine.db"

def init_db():
    """Initialize SQLite database tables for Master Profile & Daily Target Tracking."""
    conn = sqlite3.connect(DB_FILE)
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
            match_score REAL NOT NULL,
            status TEXT DEFAULT 'PENDING_REVIEW', -- 'APPROVED', 'BLOCKED_BELOW_90', 'DISPATCHED'
            context_footer TEXT,
            hrbp_contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

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
            "", # Add a video pitch URL only in your local profile if desired.
            json.dumps(["Enterprise Cloud Transformation", "BI Platform Modernization", "AI Proofs of Concept", "Global Team Leadership"]),
            json.dumps({"database": ["Relational", "NoSQL", "Snowflake"], "cloud": ["GCP", "AWS"], "analytics": ["Tableau", "Looker"], "core": ["C++", "Python", "Cloud Architecture"]})
        ))
        conn.commit()
        print("✅ Master Profile seeded successfully.")
    else:
        print("ℹ️ Master Profile already exists.")

    conn.close()

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
