from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import threading
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.engine import make_url

from .. import schemas
from ..config.config import BACKEND_ROOT, settings
from .file_storage import sanitize_filename_part


PROJECT_ROOT = BACKEND_ROOT.parent.resolve()
UPDATE_ROOT = (BACKEND_ROOT / "uploads" / "system_updates").resolve()
BACKUP_ROOT = (PROJECT_ROOT / "backups" / "last_stable").resolve()
LOG_LIMIT = 600
TOKEN_PATTERN = re.compile(r"[^a-zA-Z0-9._/-]+")


@dataclass
class DatabaseBackup:
    engine: str
    primary_artifact: Path
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class BackupContext:
    backup_dir: Path
    db_backup: DatabaseBackup
    destinations: list[Path]
    existing_destinations: set[str]


@dataclass
class UpdateJob:
    job_id: str
    package_filename: str
    package_path: Path
    status: str = "queued"
    stage: str = "queued"
    progress: int = 0
    environment_mode: str = "unknown"
    package_sha256: Optional[str] = None
    package_version: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    backup_path: Optional[str] = None
    rollback_performed: bool = False
    logs: list[str] = field(default_factory=list)
    error: Optional[str] = None


_jobs: dict[str, UpdateJob] = {}
_jobs_lock = threading.Lock()


def start_update_job(*, package_file_obj, package_filename: str) -> schemas.SystemUpdateJobStatus:
    if not _is_supported_archive(package_filename):
        raise ValueError("Format non supporte. Utilisez un fichier .zip, .tar.gz ou .tgz.")

    UPDATE_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    job_id = f"upd_{timestamp}_{uuid.uuid4().hex[:8]}"
    safe_name = sanitize_filename_part(package_filename)
    job_dir = UPDATE_ROOT / job_id
    incoming_dir = job_dir / "incoming"
    incoming_dir.mkdir(parents=True, exist_ok=True)
    package_path = incoming_dir / safe_name

    with package_path.open("wb") as target:
        shutil.copyfileobj(package_file_obj, target)

    job = UpdateJob(
        job_id=job_id,
        package_filename=package_filename,
        package_path=package_path,
        status="queued",
        stage="uploaded",
        progress=5,
    )
    with _jobs_lock:
        _jobs[job_id] = job
    _append_log(job_id, f"Package recu: {package_filename}")

    worker = threading.Thread(target=_run_update_job, args=(job_id,), daemon=True)
    worker.start()
    return get_update_job(job_id)


def get_update_job(job_id: str) -> schemas.SystemUpdateJobStatus:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise KeyError(f"Job introuvable: {job_id}")
        return _serialize_job(job)


def list_update_jobs(limit: int = 20) -> list[schemas.SystemUpdateJobStatus]:
    with _jobs_lock:
        jobs = sorted(_jobs.values(), key=lambda item: item.started_at, reverse=True)[:limit]
        return [_serialize_job(item) for item in jobs]


def _serialize_job(job: UpdateJob) -> schemas.SystemUpdateJobStatus:
    return schemas.SystemUpdateJobStatus(
        job_id=job.job_id,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        environment_mode=job.environment_mode,
        package_filename=job.package_filename,
        package_sha256=job.package_sha256,
        package_version=job.package_version,
        started_at=job.started_at,
        finished_at=job.finished_at,
        backup_path=job.backup_path,
        rollback_performed=job.rollback_performed,
        logs=list(job.logs),
        error=job.error,
    )


def _run_update_job(job_id: str) -> None:
    backup_context: Optional[BackupContext] = None
    try:
        _set_status(job_id, status="running", stage="verification", progress=12)
        mode = _detect_environment_mode()
        _update_fields(job_id, environment_mode=mode)
        _append_log(job_id, f"Environnement detecte: {mode}")

        manifest = _validate_manifest_and_hash(job_id)
        _append_log(job_id, f"Manifest valide. Version package: {manifest.version}")

        _set_status(job_id, stage="precheck", progress=20)
        _validate_write_permissions(manifest)
        _append_log(job_id, "Permissions ecriture validees.")

        _set_status(job_id, stage="backup", progress=32)
        backup_context = _create_backup(job_id, manifest)
        _append_log(job_id, f"Backup cree: {backup_context.backup_dir}")

        _set_status(job_id, stage="extract", progress=45)
        payload_root = _extract_archive(job_id, manifest)
        _append_log(job_id, "Extraction terminee.")

        _set_status(job_id, stage="apply_files", progress=62)
        _apply_payload(manifest=manifest, payload_root=payload_root)
        _append_log(job_id, "Mise a jour des fichiers terminee.")

        if manifest.requires_migration:
            _set_status(job_id, stage="migration", progress=78)
            _run_migrations(job_id)
            _append_log(job_id, "Migration SQL terminee (alembic upgrade head).")

        _set_status(job_id, stage="restart", progress=92)
        _restart_services(job_id, mode=mode)

        _set_status(job_id, status="success", stage="completed", progress=100, finished_at=datetime.utcnow())
        _append_log(job_id, "Mise a jour terminee avec succes.")
    except Exception as exc:  # pragma: no cover - defensive catch
        _append_log(job_id, f"Erreur update: {exc}")
        rollback_done = False
        if backup_context is not None:
            try:
                _set_status(job_id, stage="rollback", progress=96)
                _rollback_from_backup(backup_context)
                rollback_done = True
                _append_log(job_id, "Rollback effectue (code + base de donnees).")
            except Exception as rollback_exc:
                _append_log(job_id, f"Echec rollback: {rollback_exc}")
        _set_status(
            job_id,
            status="failed",
            stage="failed",
            progress=100,
            finished_at=datetime.utcnow(),
            error=str(exc),
            rollback_performed=rollback_done,
        )


def _validate_manifest_and_hash(job_id: str) -> schemas.SystemUpdateManifest:
    package_path = _get_job(job_id).package_path
    sha256_actual = _compute_sha256(package_path)
    manifest_payload = _read_manifest(package_path)
    manifest = schemas.SystemUpdateManifest.model_validate(manifest_payload)
    sha256_expected = manifest.package_sha256.strip().lower()
    if sha256_actual.lower() != sha256_expected:
        raise ValueError(
            "Empreinte SHA-256 invalide. "
            f"attendu={sha256_expected}, recu={sha256_actual.lower()}"
        )
    if not manifest.targets:
        raise ValueError("Manifest invalide: aucun target declare.")
    _update_fields(job_id, package_sha256=sha256_actual, package_version=manifest.version)
    return manifest


def _read_manifest(package_path: Path) -> dict[str, Any]:
    suffix = package_path.name.lower()
    if suffix.endswith(".zip"):
        with zipfile.ZipFile(package_path, "r") as archive:
            names = [name for name in archive.namelist() if Path(name).name == "manifest.json"]
            if len(names) != 1:
                raise ValueError("Le package doit contenir exactement un manifest.json.")
            return json.loads(archive.read(names[0]).decode("utf-8"))

    if suffix.endswith(".tar.gz") or suffix.endswith(".tgz"):
        with tarfile.open(package_path, "r:gz") as archive:
            members = [member for member in archive.getmembers() if Path(member.name).name == "manifest.json"]
            if len(members) != 1:
                raise ValueError("Le package doit contenir exactement un manifest.json.")
            stream = archive.extractfile(members[0])
            if stream is None:
                raise ValueError("Impossible de lire manifest.json.")
            return json.loads(stream.read().decode("utf-8"))

    raise ValueError("Format d'archive non supporte.")


def _validate_write_permissions(manifest: schemas.SystemUpdateManifest) -> None:
    for target in manifest.targets:
        destination = _resolve_project_path(target.destination)
        parent = destination if destination.is_dir() else destination.parent
        parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(prefix=".writecheck_", dir=parent, delete=True):
                pass
        except Exception as exc:
            raise PermissionError(f"Permission ecriture refusee pour {destination}: {exc}") from exc


def _create_backup(job_id: str, manifest: schemas.SystemUpdateManifest) -> BackupContext:
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    backup_dir = BACKUP_ROOT / f"{timestamp}_{job_id}"
    backup_code_dir = backup_dir / "code"
    backup_code_dir.mkdir(parents=True, exist_ok=True)

    destinations: list[Path] = []
    existing_destinations: set[str] = set()
    for target in manifest.targets:
        destination = _resolve_project_path(target.destination)
        destinations.append(destination)
        rel_dest = destination.relative_to(PROJECT_ROOT)
        backup_path = (backup_code_dir / rel_dest).resolve()
        if destination.exists():
            existing_destinations.add(str(destination))
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            if destination.is_dir():
                shutil.copytree(destination, backup_path, dirs_exist_ok=True)
            else:
                shutil.copy2(destination, backup_path)
            _append_log(job_id, f"Backup code: {rel_dest}")
        else:
            _append_log(job_id, f"Target nouveau (pas de backup source): {rel_dest}")

    db_backup = _backup_database(job_id=job_id, backup_dir=backup_dir)
    _update_fields(job_id, backup_path=str(backup_dir))
    return BackupContext(
        backup_dir=backup_dir,
        db_backup=db_backup,
        destinations=destinations,
        existing_destinations=existing_destinations,
    )


def _backup_database(*, job_id: str, backup_dir: Path) -> DatabaseBackup:
    url = make_url(settings.DATABASE_URL)
    db_backup_dir = backup_dir / "database"
    db_backup_dir.mkdir(parents=True, exist_ok=True)

    if url.drivername.startswith("sqlite"):
        db_value = url.database or ""
        if not db_value:
            raise ValueError("DATABASE_URL SQLite invalide: database manquante.")
        db_path = Path(db_value)
        if not db_path.is_absolute():
            db_path = (BACKEND_ROOT / db_path).resolve()
        if not db_path.exists():
            raise FileNotFoundError(f"Base SQLite introuvable: {db_path}")

        main_backup = db_backup_dir / db_path.name
        with sqlite3.connect(str(db_path)) as src_conn, sqlite3.connect(str(main_backup)) as dst_conn:
            src_conn.backup(dst_conn)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{db_path}{suffix}")
            if sidecar.exists():
                shutil.copy2(sidecar, db_backup_dir / sidecar.name)

        _append_log(job_id, f"Backup DB sqlite: {db_path.name}")
        return DatabaseBackup(
            engine="sqlite",
            primary_artifact=main_backup,
            meta={"database_path": str(db_path)},
        )

    if url.drivername.startswith("postgresql"):
        pg_dump = shutil.which("pg_dump")
        pg_restore = shutil.which("pg_restore")
        if not pg_dump or not pg_restore:
            raise RuntimeError(
                "Backup PostgreSQL impossible: pg_dump/pg_restore indisponibles."
            )

        dump_file = db_backup_dir / "postgres_backup.dump"
        cmd = [pg_dump, "--format=custom", "--file", str(dump_file)]
        if url.host:
            cmd.extend(["--host", url.host])
        if url.port:
            cmd.extend(["--port", str(url.port)])
        if url.username:
            cmd.extend(["--username", url.username])
        if url.database:
            cmd.append(url.database)
        env = os.environ.copy()
        if url.password:
            env["PGPASSWORD"] = url.password
        _run_command(job_id=job_id, cmd=cmd, cwd=PROJECT_ROOT, env=env)
        _append_log(job_id, "Backup DB PostgreSQL termine.")
        return DatabaseBackup(
            engine="postgresql",
            primary_artifact=dump_file,
            meta={
                "host": url.host,
                "port": url.port,
                "username": url.username,
                "database": url.database,
            },
        )

    raise RuntimeError(
        f"SGBD non supporte pour rollback automatique: {url.drivername}. "
        "Utilisez SQLite ou PostgreSQL."
    )


def _extract_archive(job_id: str, manifest: schemas.SystemUpdateManifest) -> Path:
    job = _get_job(job_id)
    package_path = job.package_path
    extract_root = package_path.parent.parent / "extract"
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)

    suffix = package_path.name.lower()
    if suffix.endswith(".zip"):
        with zipfile.ZipFile(package_path, "r") as archive:
            for member in archive.infolist():
                member_path = (extract_root / member.filename).resolve()
                _ensure_within_root(member_path, extract_root, "Chemin zip invalide")
                archive.extract(member, extract_root)
    elif suffix.endswith(".tar.gz") or suffix.endswith(".tgz"):
        with tarfile.open(package_path, "r:gz") as archive:
            for member in archive.getmembers():
                if member.issym() or member.islnk():
                    raise ValueError(f"Archive invalide: lien symbolique interdit ({member.name})")
                member_path = (extract_root / member.name).resolve()
                _ensure_within_root(member_path, extract_root, "Chemin tar invalide")
            archive.extractall(extract_root)
    else:
        raise ValueError("Archive non supportee.")

    payload_root = (extract_root / _normalize_manifest_token(manifest.payload_root)).resolve()
    _ensure_within_root(payload_root, extract_root, "payload_root invalide")
    if not payload_root.exists() or not payload_root.is_dir():
        raise ValueError(f"payload_root introuvable dans l'archive: {manifest.payload_root}")
    return payload_root


def _apply_payload(*, manifest: schemas.SystemUpdateManifest, payload_root: Path) -> None:
    for target in manifest.targets:
        source_rel = _normalize_manifest_token(target.source)
        destination = _resolve_project_path(target.destination)
        source = (payload_root / source_rel).resolve()
        _ensure_within_root(source, payload_root, "Source package invalide")
        if not source.exists():
            raise FileNotFoundError(f"Source manquante dans package: {target.source}")

        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()

        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)


def _run_migrations(job_id: str) -> None:
    cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
    _run_command(job_id=job_id, cmd=cmd, cwd=BACKEND_ROOT)


def _restart_services(job_id: str, *, mode: str) -> None:
    if mode == "cloud_container":
        restart_cmd = os.getenv("SIIRH_ORCHESTRATOR_RESTART_COMMAND", "").strip()
    else:
        restart_cmd = os.getenv("SIIRH_RESTART_COMMAND", "").strip()

    if not restart_cmd:
        _append_log(
            job_id,
            "Aucune commande de restart configuree. Redemarrage manuel recommande.",
        )
        return

    cmd = shlex.split(restart_cmd)
    _append_log(job_id, f"Execution restart command: {' '.join(cmd)}")
    try:
        _run_command(job_id=job_id, cmd=cmd, cwd=PROJECT_ROOT)
    except Exception as exc:
        _append_log(job_id, f"Restart non bloqueur en echec: {exc}")


def _rollback_from_backup(context: BackupContext) -> None:
    _restore_database(context.db_backup)
    backup_code_dir = context.backup_dir / "code"
    for destination in context.destinations:
        rel_dest = destination.relative_to(PROJECT_ROOT)
        backup_copy = (backup_code_dir / rel_dest).resolve()
        destination_exists_before = str(destination) in context.existing_destinations

        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()

        if destination_exists_before:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if backup_copy.is_dir():
                shutil.copytree(backup_copy, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(backup_copy, destination)


def _restore_database(db_backup: DatabaseBackup) -> None:
    if db_backup.engine == "sqlite":
        db_path = Path(str(db_backup.meta["database_path"])).resolve()
        db_backup_dir = db_backup.primary_artifact.parent
        if db_path.exists():
            db_path.unlink()
        shutil.copy2(db_backup.primary_artifact, db_path)
        for suffix in ("-wal", "-shm"):
            backup_sidecar = db_backup_dir / f"{db_path.name}{suffix}"
            live_sidecar = Path(f"{db_path}{suffix}")
            if live_sidecar.exists():
                live_sidecar.unlink()
            if backup_sidecar.exists():
                shutil.copy2(backup_sidecar, live_sidecar)
        return

    if db_backup.engine == "postgresql":
        pg_restore = shutil.which("pg_restore")
        if not pg_restore:
            raise RuntimeError("pg_restore indisponible pour rollback PostgreSQL.")
        meta = db_backup.meta
        cmd = [pg_restore, "--clean", "--if-exists", "--no-owner", "--no-privileges"]
        if meta.get("host"):
            cmd.extend(["--host", str(meta["host"])])
        if meta.get("port"):
            cmd.extend(["--port", str(meta["port"])])
        if meta.get("username"):
            cmd.extend(["--username", str(meta["username"])])
        if meta.get("database"):
            cmd.extend(["--dbname", str(meta["database"])])
        cmd.append(str(db_backup.primary_artifact))
        env = os.environ.copy()
        url = make_url(settings.DATABASE_URL)
        if url.password:
            env["PGPASSWORD"] = url.password
        subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        return

    raise RuntimeError(f"Rollback DB non supporte pour {db_backup.engine}")


def _run_command(*, job_id: str, cmd: list[str], cwd: Path, env: Optional[dict[str, str]] = None) -> None:
    _append_log(job_id, f"$ {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    assert process.stdout is not None
    for line in process.stdout:
        cleaned = line.rstrip()
        if cleaned:
            _append_log(job_id, cleaned)
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"Commande en echec ({return_code}): {' '.join(cmd)}")


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_project_path(value: str) -> Path:
    token = _normalize_manifest_token(value)
    path = (PROJECT_ROOT / token).resolve()
    _ensure_within_root(path, PROJECT_ROOT, "Chemin destination hors projet")
    return path


def _normalize_manifest_token(value: str) -> str:
    raw = (value or "").strip().replace("\\", "/")
    normalized = TOKEN_PATTERN.sub("_", raw).strip("/")
    if not normalized:
        raise ValueError("Chemin manifeste vide ou invalide.")
    return normalized


def _ensure_within_root(path: Path, root: Path, message: str) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{message}: {path}") from exc


def _detect_environment_mode() -> str:
    if Path("/.dockerenv").exists():
        return "cloud_container"
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return "cloud_container"
    if os.getenv("SIIRH_CONTAINER_MODE", "").strip() == "1":
        return "cloud_container"
    return "local"


def _is_supported_archive(filename: str) -> bool:
    value = filename.lower()
    return value.endswith(".zip") or value.endswith(".tar.gz") or value.endswith(".tgz")


def _get_job(job_id: str) -> UpdateJob:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise KeyError(f"Job introuvable: {job_id}")
        return job


def _append_log(job_id: str, message: str) -> None:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with _jobs_lock:
        job = _jobs[job_id]
        job.logs.append(f"[{timestamp}] {message}")
        if len(job.logs) > LOG_LIMIT:
            del job.logs[0 : len(job.logs) - LOG_LIMIT]


def _set_status(
    job_id: str,
    *,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    progress: Optional[int] = None,
    finished_at: Optional[datetime] = None,
    error: Optional[str] = None,
    rollback_performed: Optional[bool] = None,
) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        if status is not None:
            job.status = status
        if stage is not None:
            job.stage = stage
        if progress is not None:
            job.progress = max(0, min(100, progress))
        if finished_at is not None:
            job.finished_at = finished_at
        if error is not None:
            job.error = error
        if rollback_performed is not None:
            job.rollback_performed = rollback_performed


def _update_fields(job_id: str, **kwargs: Any) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        for key, value in kwargs.items():
            setattr(job, key, value)
