from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"


def normalize_database_url(database_url: str) -> str:
    url = make_url(database_url.strip())

    if url.drivername in {"postgresql", "postgres", "postgresql+psycopg2"}:
        url = url.set(drivername="postgresql+psycopg")

    return url.render_as_string(hide_password=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+psycopg://postgres:change_me@127.0.0.1:5432/db_siirh_app"
    JWT_SECRET: str = "change_me"
    JWT_ALGO: str = "HS256"
    AUTO_CREATE_TABLES: bool = True
    UPLOAD_DIR: str = "uploads"
    AUTH_REQUIRED: bool = True
    DEFAULT_ADMIN_USERNAME: str = "admin@siirh.com"
    DEFAULT_ADMIN_PASSWORD: str = "Siirh2026"
    AUTH_PUBLIC_REGISTRATION_ENABLED: bool = True
    DOCUMENT_VERIFY_SECRET: str = "change_document_secret"
    APP_PUBLIC_URL: str = "http://127.0.0.1:8001"

    def __init__(self, **values):
        super().__init__(**values)
        self.DATABASE_URL = normalize_database_url(self.DATABASE_URL)


settings = Settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency used to obtain a scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create database tables from the SQLAlchemy metadata."""
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_schema_updates()


def _apply_lightweight_schema_updates():
    """Apply small additive schema updates for local/dev environments."""
    inspector = inspect(engine)
    try:
        table_names = set(inspector.get_table_names())
    except Exception:
        return

    with engine.begin() as connection:
        if "calendar_days" in table_names:
            try:
                calendar_columns = {column["name"] for column in inspector.get_columns("calendar_days")}
            except Exception:
                calendar_columns = set()
            if "status" not in calendar_columns:
                connection.execute(text("ALTER TABLE calendar_days ADD COLUMN status VARCHAR(20)"))
            connection.execute(
                text(
                    """
                    UPDATE calendar_days
                    SET status = CASE
                        WHEN is_worked = TRUE THEN 'worked'
                        ELSE 'off'
                    END
                    WHERE status IS NULL OR TRIM(status) = ''
                    """
                )
            )

        additive_columns = {
            "primes": [
                ("target_mode", "VARCHAR(20) DEFAULT 'global'"),
            ],
            "worker_prime_links": [
                ("link_type", "VARCHAR(20) DEFAULT 'include'"),
            ],
            "recruitment_job_profiles": [
                ("submission_attachments_json", "TEXT DEFAULT '[]'"),
                ("workforce_job_profile_id", "INTEGER"),
                ("contract_guidance_json", "TEXT DEFAULT '{}'"),
                ("publication_mode", "VARCHAR(50)"),
                ("publication_url", "VARCHAR(500)"),
                ("submitted_to_inspection_at", "TIMESTAMP"),
                ("last_reviewed_at", "TIMESTAMP"),
            ],
            "custom_contracts": [
                ("validation_status", "VARCHAR(50) DEFAULT 'active_non_validated'"),
                ("inspection_status", "VARCHAR(50) DEFAULT 'pending_review'"),
                ("inspection_comment", "TEXT"),
                ("active_version_number", "INTEGER DEFAULT 1"),
                ("last_published_at", "TIMESTAMP"),
                ("last_reviewed_at", "TIMESTAMP"),
            ],
            "inspector_cases": [
                ("category", "VARCHAR(100)"),
                ("sub_type", "VARCHAR(100)"),
                ("district", "VARCHAR(255)"),
                ("urgency", "VARCHAR(50) DEFAULT 'normal'"),
                ("outcome_summary", "TEXT"),
                ("resolution_type", "VARCHAR(100)"),
                ("due_at", "TIMESTAMP"),
                ("received_at", "TIMESTAMP"),
                ("is_sensitive", "BOOLEAN DEFAULT FALSE"),
            ],
            "employment_master_records": [
                ("workforce_job_profile_id", "INTEGER"),
            ],
        }

        for table_name, additions in additive_columns.items():
            if table_name not in table_names:
                continue
            try:
                existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            except Exception:
                existing_columns = set()
            for column_name, ddl in additions:
                if column_name in existing_columns:
                    continue
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))

        if "prime_organizational_targets" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE prime_organizational_targets (
                        id SERIAL PRIMARY KEY,
                        prime_id INTEGER NOT NULL REFERENCES primes(id) ON DELETE CASCADE,
                        node_id INTEGER NOT NULL REFERENCES organizational_nodes(id) ON DELETE CASCADE,
                        CONSTRAINT uq_prime_organizational_target UNIQUE (prime_id, node_id)
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE INDEX idx_prime_organizational_targets_prime_id ON prime_organizational_targets (prime_id)")
            )
            connection.execute(
                text(
                    "CREATE INDEX idx_prime_organizational_targets_node_id ON prime_organizational_targets (node_id)"
                )
            )
        else:
            try:
                target_columns = {column["name"] for column in inspector.get_columns("prime_organizational_targets")}
            except Exception:
                target_columns = set()
            if "node_id" not in target_columns:
                connection.execute(text("ALTER TABLE prime_organizational_targets ADD COLUMN node_id INTEGER"))
                connection.execute(
                    text(
                        """
                        UPDATE prime_organizational_targets
                        SET node_id = organizational_unit_id
                        WHERE node_id IS NULL
                        """
                    )
                )
            if "organizational_unit_id" in target_columns:
                connection.execute(
                    text("ALTER TABLE prime_organizational_targets ALTER COLUMN organizational_unit_id DROP NOT NULL")
                )
            connection.execute(
                text(
                    """
                    DELETE FROM prime_organizational_targets
                    WHERE node_id IS NULL
                    """
                )
            )

        if "prime_organizational_unit_targets" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE prime_organizational_unit_targets (
                        id SERIAL PRIMARY KEY,
                        prime_id INTEGER NOT NULL REFERENCES primes(id) ON DELETE CASCADE,
                        organizational_unit_id INTEGER NOT NULL REFERENCES organizational_units(id) ON DELETE CASCADE,
                        CONSTRAINT uq_prime_organizational_unit_target UNIQUE (prime_id, organizational_unit_id)
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE INDEX idx_prime_organizational_unit_targets_prime_id ON prime_organizational_unit_targets (prime_id)")
            )
            connection.execute(
                text(
                    "CREATE INDEX idx_prime_organizational_unit_targets_unit_id ON prime_organizational_unit_targets (organizational_unit_id)"
                )
            )

        if "inspector_cases" in table_names:
            connection.execute(
                text(
                    """
                    UPDATE inspector_cases
                    SET received_at = COALESCE(received_at, created_at),
                        urgency = COALESCE(NULLIF(TRIM(urgency), ''), 'normal'),
                        is_sensitive = COALESCE(is_sensitive, FALSE)
                    """
                )
            )
        if "recruitment_job_profiles" in table_names:
            connection.execute(
                text(
                    """
                    UPDATE recruitment_job_profiles
                    SET submission_attachments_json = COALESCE(NULLIF(TRIM(submission_attachments_json), ''), '[]'),
                        contract_guidance_json = COALESCE(NULLIF(TRIM(contract_guidance_json), ''), '{}')
                    """
                )
            )
        if "custom_contracts" in table_names:
            connection.execute(
                text(
                    """
                    UPDATE custom_contracts
                    SET validation_status = COALESCE(NULLIF(TRIM(validation_status), ''), 'active_non_validated'),
                        inspection_status = COALESCE(NULLIF(TRIM(inspection_status), ''), 'pending_review'),
                        active_version_number = COALESCE(active_version_number, 1)
                    """
                )
            )
        if "primes" in table_names:
            connection.execute(
                text(
                    """
                    UPDATE primes
                    SET target_mode = COALESCE(NULLIF(TRIM(target_mode), ''), 'global')
                    """
                )
            )
        if "worker_prime_links" in table_names:
            connection.execute(
                text(
                    """
                    UPDATE worker_prime_links
                    SET link_type = COALESCE(NULLIF(TRIM(link_type), ''), 'include')
                    """
                )
            )
