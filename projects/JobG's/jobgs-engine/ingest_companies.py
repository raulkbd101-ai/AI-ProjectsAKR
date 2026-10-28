from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from database import DB_FILE

MAX_FILE_RECORDS = 1_000
DB_WRITE_CHUNK_SIZE = 1_000


CompanySizeTier = Literal[
    "Startup (<50)",
    "SMB (50-250)",
    "Mid-Market (250-1000)",
    "Enterprise (1000+)",
]


class TechStack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cloud_infrastructure: list[str] = Field(default_factory=list, max_length=100)
    languages_frameworks: list[str] = Field(default_factory=list, max_length=100)
    data_tools: list[str] = Field(default_factory=list, max_length=100)

    @field_validator(
        "cloud_infrastructure",
        "languages_frameworks",
        "data_tools",
    )
    @classmethod
    def clean_stack_items(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(cleaned))


class CompanyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1, max_length=250)
    primary_domain: str = Field(min_length=1, max_length=253)
    country_of_hq: str = Field(min_length=1, max_length=100)
    industry_vertical: str = Field(min_length=1, max_length=200)
    core_services: list[str] = Field(min_length=1, max_length=50)
    company_size_tier: CompanySizeTier
    tech_stack: TechStack
    careers_url: str = Field(min_length=1, max_length=2048)
    source_provenance: str = Field(min_length=1, max_length=500)

    @field_validator(
        "company_name",
        "country_of_hq",
        "industry_vertical",
        "source_provenance",
    )
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("core_services")
    @classmethod
    def clean_core_services(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if not cleaned:
            raise ValueError("Provide at least one core service.")
        return list(dict.fromkeys(cleaned))

    @field_validator("primary_domain")
    @classmethod
    def normalize_domain(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("Primary domain cannot be blank.")

        # Accept either example.com or https://www.example.com/path.
        parsed = urlsplit(value if "://" in value else f"//{value}")
        host = (parsed.hostname or "").strip(".").lower()

        if not host or "." not in host or any(char.isspace() for char in host):
            raise ValueError("Enter a valid company domain, such as example.com.")

        if host.startswith("www."):
            host = host[4:]

        return host

    @field_validator("careers_url")
    @classmethod
    def validate_careers_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlsplit(value)

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Careers URL must be an absolute http:// or https:// URL.")

        return value


UPSERT_SQL = """
    INSERT INTO companies_inventory (
        company_name,
        domain,
        hq,
        vertical,
        company_size,
        tech_stack_json,
        careers_url,
        core_services_json,
        source_provenance,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(company_name COLLATE NOCASE) DO UPDATE SET
        company_name = excluded.company_name,
        domain = CASE
            WHEN excluded.domain <> '' THEN excluded.domain
            ELSE companies_inventory.domain
        END,
        hq = CASE
            WHEN excluded.hq <> '' THEN excluded.hq
            ELSE companies_inventory.hq
        END,
        vertical = CASE
            WHEN excluded.vertical <> '' THEN excluded.vertical
            ELSE companies_inventory.vertical
        END,
        company_size = CASE
            WHEN excluded.company_size <> '' THEN excluded.company_size
            ELSE companies_inventory.company_size
        END,
        tech_stack_json = CASE
            WHEN excluded.tech_stack_json <> '{}'
            THEN excluded.tech_stack_json
            ELSE companies_inventory.tech_stack_json
        END,
        careers_url = CASE
            WHEN excluded.careers_url <> '' THEN excluded.careers_url
            ELSE companies_inventory.careers_url
        END,
        core_services_json = CASE
            WHEN excluded.core_services_json <> '[]'
            THEN excluded.core_services_json
            ELSE companies_inventory.core_services_json
        END,
        source_provenance = CASE
            WHEN excluded.source_provenance <> ''
            THEN excluded.source_provenance
            ELSE companies_inventory.source_provenance
        END,
        updated_at = excluded.updated_at
"""


def ingest_company_records(
    records: list[CompanyRecord | dict],
    *,
    db_file: str | Path = DB_FILE,
) -> int:
    """Validate and upsert a batch of company records atomically."""
    if not records:
        raise ValueError("The company batch cannot be empty.")
    if len(records) > MAX_FILE_RECORDS:
        raise ValueError(
            f"Import one batch of at most {MAX_FILE_RECORDS:,} companies at a time. "
            "Split larger source files into sequential batches before importing."
        )

    validated = [
        record if isinstance(record, CompanyRecord) else CompanyRecord.model_validate(record)
        for record in records
    ]

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []

    for company in validated:
        tech_stack = company.tech_stack.model_dump()
        rows.append(
            (
                company.company_name,
                company.primary_domain,
                company.country_of_hq,
                company.industry_vertical,
                company.company_size_tier,
                json.dumps(tech_stack, ensure_ascii=False, separators=(",", ":")),
                company.careers_url,
                json.dumps(company.core_services, ensure_ascii=False),
                company.source_provenance,
                now,
            )
        )

    connection = sqlite3.connect(str(db_file), timeout=10)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        for start in range(0, len(rows), DB_WRITE_CHUNK_SIZE):
            batch = rows[start : start + DB_WRITE_CHUNK_SIZE]
            connection.executemany(UPSERT_SQL, batch)
        connection.commit()
        return len(rows)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def load_json_records(path: str | Path) -> list[dict]:
    """Load a JSON array or an object containing a 'companies' array."""
    with Path(path).open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(payload, dict):
        payload = payload.get("companies")

    if not isinstance(payload, list):
        raise ValueError("JSON must be an array or an object with a 'companies' array.")

    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("Every item in the companies array must be a JSON object.")

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and upsert one sequential batch of up to 1,000 company "
            "records from a JSON file into JobG's SQLite inventory."
        )
    )
    parser.add_argument("json_file", help="Path to a JSON file containing company records.")
    args = parser.parse_args()

    try:
        records = load_json_records(args.json_file)
        count = ingest_company_records(records)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"SQLite error: {exc}", file=sys.stderr)
        return 1

    batch_file = Path(args.json_file).name
    print(
        f"Batch '{batch_file}' complete: upserted {count} company record(s) "
        f"into {DB_FILE}. Import the next source batch when ready."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
