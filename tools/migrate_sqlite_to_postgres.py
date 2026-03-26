from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, func, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.engine.url import make_url


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DEFAULT_SOURCE_URL = f"sqlite:///{(BACKEND / 'method_aware.db').as_posix()}"
SCHEMA_ID = "project6.sqlite_to_postgres_migration.v1"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _mask_url(url: str) -> str:
    return make_url(url).render_as_string(hide_password=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Copy the canonical Tier1 SQLite database into a PostgreSQL target.")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--truncate-target", action="store_true", help="Truncate PostgreSQL user tables before copying.")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--report", default="")
    return parser


def _run_target_migrations(target_url: str) -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", target_url)
    command.upgrade(cfg, "head")


def _reflect(engine: Engine) -> MetaData:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    return metadata


def _user_tables(metadata: MetaData) -> list:
    return [table for table in metadata.sorted_tables if table.name != "alembic_version"]


def _ensure_supported_urls(source_url: str, target_url: str) -> None:
    source = make_url(source_url)
    target = make_url(target_url)
    if source.get_backend_name() != "sqlite":
        raise ValueError(f"source URL must be SQLite, got {source.drivername}")
    if target.get_backend_name() != "postgresql":
        raise ValueError(f"target URL must be PostgreSQL, got {target.drivername}")
    if source.render_as_string(hide_password=False) == target.render_as_string(hide_password=False):
        raise ValueError("source and target URLs must differ")


def _ensure_matching_tables(source_metadata: MetaData, target_metadata: MetaData) -> None:
    source_tables = {table.name for table in _user_tables(source_metadata)}
    target_tables = {table.name for table in _user_tables(target_metadata)}
    if source_tables != target_tables:
        missing = sorted(source_tables - target_tables)
        extra = sorted(target_tables - source_tables)
        raise RuntimeError(f"source/target table mismatch; missing={missing}, extra={extra}")


def _nonempty_target_tables(connection: Connection, tables: list) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in tables:
        count = int(connection.execute(select(func.count()).select_from(table)).scalar_one())
        if count:
            counts[table.name] = count
    return counts


def _truncate_target(connection: Connection, tables: list) -> None:
    if not tables:
        return
    quoted = ", ".join(f'"{table.name}"' for table in tables)
    connection.exec_driver_sql(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")


def _rows_from_source(connection: Connection, table) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(select(table)).mappings().all()]


def _insert_batches(connection: Connection, table, rows: list[dict[str, Any]], batch_size: int) -> None:
    if not rows:
        return
    for start in range(0, len(rows), batch_size):
        connection.execute(table.insert(), rows[start:start + batch_size])


def _copy_self_referential_table(connection: Connection, table, rows: list[dict[str, Any]], batch_size: int) -> int:
    self_constraints = []
    inserted_by_column: dict[str, set[Any]] = {}
    pk_names = [column.name for column in table.primary_key.columns]
    for pk_name in pk_names:
        inserted_by_column[pk_name] = set()

    for constraint in table.foreign_key_constraints:
        if constraint.referred_table.name != table.name:
            continue
        local_cols = [element.parent.name for element in constraint.elements]
        remote_cols = [element.column.name for element in constraint.elements]
        if len(local_cols) != 1 or len(remote_cols) != 1:
            raise RuntimeError(f"unsupported self-referential FK shape for table {table.name}")
        remote_col = remote_cols[0]
        if remote_col not in inserted_by_column:
            raise RuntimeError(f"unsupported self-referential FK target {table.name}.{remote_col}")
        self_constraints.append((local_cols[0], remote_col))

    pending = list(rows)
    inserted = 0
    while pending:
        ready: list[dict[str, Any]] = []
        still_pending: list[dict[str, Any]] = []
        for row in pending:
            is_ready = True
            for local_col, remote_col in self_constraints:
                local_value = row.get(local_col)
                if local_value is None:
                    continue
                if local_value not in inserted_by_column[remote_col]:
                    is_ready = False
                    break
            if is_ready:
                ready.append(row)
            else:
                still_pending.append(row)
        if not ready:
            sample = still_pending[0]
            raise RuntimeError(f"unable to resolve self-referential insert order for table {table.name}: {sample}")
        _insert_batches(connection, table, ready, batch_size)
        inserted += len(ready)
        for row in ready:
            for pk_name in pk_names:
                inserted_by_column[pk_name].add(row.get(pk_name))
        pending = still_pending
    return inserted


def _copy_table(source_connection: Connection, target_connection: Connection, source_table, target_table, batch_size: int) -> int:
    rows = _rows_from_source(source_connection, source_table)
    if not rows:
        return 0
    has_self_fk = any(constraint.referred_table.name == target_table.name for constraint in target_table.foreign_key_constraints)
    if has_self_fk:
        return _copy_self_referential_table(target_connection, target_table, rows, batch_size)
    _insert_batches(target_connection, target_table, rows, batch_size)
    return len(rows)


def _normalize_stat_value(value: Any) -> Any:
    if isinstance(value, datetime):
        normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return normalized.isoformat().replace("+00:00", "Z")
    return value


def _risk_stats(connection: Connection, metadata: MetaData) -> dict[str, Any]:
    stats: dict[str, Any] = {}

    connector_run = metadata.tables["connector_run"]
    stats["connector_run"] = {
        "rows": int(connection.execute(select(func.count()).select_from(connector_run)).scalar_one()),
        "next_page_available_true": int(connection.execute(select(func.count()).select_from(connector_run).where(connector_run.c.next_page_available.is_(True))).scalar_one()),
        "budget_exhausted_true": int(connection.execute(select(func.count()).select_from(connector_run).where(connector_run.c.budget_exhausted.is_(True))).scalar_one()),
        "submitted_at_min": _normalize_stat_value(connection.execute(select(func.min(connector_run.c.submitted_at))).scalar_one()),
        "submitted_at_max": _normalize_stat_value(connection.execute(select(func.max(connector_run.c.submitted_at))).scalar_one()),
    }

    aps_document = metadata.tables["aps_content_document"]
    stats["aps_content_document"] = {
        "rows": int(connection.execute(select(func.count()).select_from(aps_document)).scalar_one()),
        "visual_page_refs_nonnull": int(connection.execute(select(func.count(aps_document.c.visual_page_refs_json)).select_from(aps_document)).scalar_one()),
        "visual_page_refs_max_len": _normalize_stat_value(connection.execute(select(func.max(func.length(aps_document.c.visual_page_refs_json)))).scalar_one()),
    }

    aps_chunk = metadata.tables["aps_content_chunk"]
    stats["aps_content_chunk"] = {
        "rows": int(connection.execute(select(func.count()).select_from(aps_chunk)).scalar_one()),
        "chunk_text_nonempty": int(connection.execute(select(func.count()).select_from(aps_chunk).where(func.length(aps_chunk.c.chunk_text) > 0)).scalar_one()),
        "chunk_text_max_len": _normalize_stat_value(connection.execute(select(func.max(func.length(aps_chunk.c.chunk_text)))).scalar_one()),
    }
    return stats


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _ensure_supported_urls(args.source_url, args.target_url)
    report_path = Path(args.report).resolve() if str(args.report).strip() else None
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)

    _run_target_migrations(args.target_url)
    source_engine = create_engine(args.source_url, future=True)
    target_engine = create_engine(args.target_url, future=True)

    try:
        source_metadata = _reflect(source_engine)
        target_metadata = _reflect(target_engine)
        _ensure_matching_tables(source_metadata, target_metadata)
        target_tables = _user_tables(target_metadata)

        with target_engine.begin() as target_connection:
            if args.truncate_target:
                _truncate_target(target_connection, target_tables)
            else:
                existing_rows = _nonempty_target_tables(target_connection, target_tables)
                if existing_rows:
                    raise RuntimeError(f"target contains data; use --truncate-target to reset it: {existing_rows}")

        migrated_counts: dict[str, int] = {}
        with source_engine.connect() as source_connection, target_engine.begin() as target_connection:
            for source_table in _user_tables(source_metadata):
                target_table = target_metadata.tables[source_table.name]
                migrated_counts[source_table.name] = _copy_table(
                    source_connection,
                    target_connection,
                    source_table,
                    target_table,
                    args.batch_size,
                )

        with source_engine.connect() as source_connection, target_engine.connect() as target_connection:
            source_counts = {
                table.name: int(source_connection.execute(select(func.count()).select_from(table)).scalar_one())
                for table in _user_tables(source_metadata)
            }
            target_counts = {
                table.name: int(target_connection.execute(select(func.count()).select_from(table)).scalar_one())
                for table in _user_tables(target_metadata)
            }
            parity = {
                table_name: {
                    "source": source_counts[table_name],
                    "target": target_counts[table_name],
                    "match": source_counts[table_name] == target_counts[table_name],
                }
                for table_name in sorted(source_counts)
            }
            source_risk = _risk_stats(source_connection, source_metadata)
            target_risk = _risk_stats(target_connection, target_metadata)

        passed = all(item["match"] for item in parity.values()) and source_risk == target_risk
        payload = {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "generated_at_utc": _utc_iso(),
            "passed": passed,
            "source_url": _mask_url(args.source_url),
            "target_url": _mask_url(args.target_url),
            "truncate_target": bool(args.truncate_target),
            "batch_size": int(args.batch_size),
            "migrated_rows": migrated_counts,
            "row_count_parity": parity,
            "source_risk_stats": source_risk,
            "target_risk_stats": target_risk,
        }
        if report_path is not None:
            report_path.write_text(_stable_json(payload), encoding="utf-8")

        print(f"source={payload['source_url']}")
        print(f"target={payload['target_url']}")
        print(f"passed={payload['passed']}")
        print("row_count_parity")
        for table_name in sorted(parity):
            entry = parity[table_name]
            print(f"  {table_name}: {entry['source']} -> {entry['target']} (match={entry['match']})")
        if report_path is not None:
            print(f"report={report_path}")
        return 0 if passed else 1
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
