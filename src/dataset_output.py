from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "dataset"
CHUNK_SIZE = 50000
XLSX_MAX_ROWS = 1048576
XLSX_DATA_ROWS = XLSX_MAX_ROWS - 1
SYSTEM_SCHEMAS = {"information_schema", "pg_catalog", "pg_toast"}


def build_database_url() -> str:
    load_dotenv()
    db_user = os.getenv("user")
    db_password = os.getenv("password")
    db_host = os.getenv("host")
    db_port = os.getenv("port")
    db_name = os.getenv("name")
    missing = [
        key
        for key, value in {
            "user": db_user,
            "password": db_password,
            "host": db_host,
            "port": db_port,
            "name": db_name,
        }.items()
        if not value
    ]
    if missing:
        raise EnvironmentError(f"Missing database environment variables: {', '.join(missing)}")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_export_targets(engine: Engine) -> list[tuple[str, str, str]]:
    inspector = inspect(engine)
    targets: list[tuple[str, str, str]] = []
    for schema in inspector.get_schema_names():
        if schema in SYSTEM_SCHEMAS or schema.startswith("pg_"):
            continue
        for table_name in inspector.get_table_names(schema=schema):
            targets.append((schema, table_name, "table"))
        for view_name in inspector.get_view_names(schema=schema):
            targets.append((schema, view_name, "view"))
    return sorted(targets)


def quote_relation(engine: Engine, schema: str, relation: str) -> str:
    preparer = engine.dialect.identifier_preparer
    return f"{preparer.quote_schema(schema)}.{preparer.quote(relation)}"


def safe_filename(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", value).strip("_")


def normalize_excel_value(value: Any) -> Any:
    if value is None:
        return value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, memoryview):
        return value.tobytes().hex()
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, (pd.Timestamp, dt.datetime)) and value.tzinfo is not None:
        return value.isoformat()
    try:
        if pd.isna(value):
            return value
    except (TypeError, ValueError):
        pass
    return value


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    object_columns = df.select_dtypes(include=["object"]).columns
    timezone_columns = [column for column in df.columns if getattr(df[column].dtype, "tz", None) is not None]
    if object_columns.empty and not timezone_columns:
        return df
    df = df.copy()
    for column in timezone_columns:
        df[column] = df[column].map(normalize_excel_value)
    for column in object_columns:
        df[column] = df[column].map(normalize_excel_value)
    return df


def output_path(output_dir: Path, schema: str, relation: str, part: int | None = None) -> Path:
    base_name = safe_filename(f"{schema}_{relation}") or "database_export"
    suffix = f"_part{part:03d}" if part is not None else ""
    return output_dir / f"{base_name}{suffix}.xlsx"


def write_sheet(path: Path, chunks: Iterable[pd.DataFrame]) -> int:
    rows_written = 0
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        startrow = 0
        wrote_sheet = False
        for chunk in chunks:
            if chunk.empty and len(chunk.columns) == 0:
                continue
            chunk = normalize_dataframe(chunk)
            chunk.to_excel(
                writer,
                sheet_name="data",
                index=False,
                header=startrow == 0,
                startrow=startrow,
            )
            wrote_sheet = True
            rows_written += len(chunk)
            startrow += len(chunk) + (1 if startrow == 0 else 0)
        if not wrote_sheet:
            writer.book.create_sheet("data")
    return rows_written


def export_relation(engine: Engine, schema: str, relation: str, output_dir: Path) -> list[Path]:
    sql = text(f"SELECT * FROM {quote_relation(engine, schema, relation)}")
    reader = pd.read_sql_query(sql, engine, chunksize=CHUNK_SIZE)
    exported_paths: list[Path] = []
    part = 1
    pending_chunks: list[pd.DataFrame] = []
    pending_rows = 0
    saw_chunk = False

    for chunk in reader:
        saw_chunk = True
        start = 0
        while start < len(chunk):
            capacity = XLSX_DATA_ROWS - pending_rows
            piece = chunk.iloc[start : start + capacity]
            pending_chunks.append(piece)
            pending_rows += len(piece)
            start += len(piece)

            if pending_rows == XLSX_DATA_ROWS:
                path = output_path(output_dir, schema, relation, part)
                write_sheet(path, pending_chunks)
                exported_paths.append(path)
                part += 1
                pending_chunks = []
                pending_rows = 0

    if not saw_chunk:
        empty_df = pd.read_sql_query(text(f"SELECT * FROM {quote_relation(engine, schema, relation)} LIMIT 0"), engine)
        pending_chunks.append(empty_df)

    if pending_chunks or not exported_paths:
        path = output_path(output_dir, schema, relation, part if exported_paths else None)
        write_sheet(path, pending_chunks)
        exported_paths.append(path)

    return exported_paths


def export_database(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(build_database_url())
    exported_paths: list[Path] = []

    try:
        targets = get_export_targets(engine)
        if not targets:
            raise ValueError("No tables or views found to export.")

        for schema, relation, relation_type in targets:
            paths = export_relation(engine, schema, relation, output_dir)
            exported_paths.extend(paths)
            print(f"Exported {relation_type} {schema}.{relation} -> {', '.join(str(path) for path in paths)}")
    finally:
        engine.dispose()

    return exported_paths


def main() -> None:
    exported_paths = export_database()
    print(f"Exported {len(exported_paths)} xlsx file(s) to: {DEFAULT_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
