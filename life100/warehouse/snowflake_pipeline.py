"""Real Snowflake warehouse pipeline. SRS §18-19.

An alternative to the DuckDB stand-in (warehouse/duckdb_pipeline.py) used
when real Snowflake credentials are configured — see SCOPE.md for why
DuckDB is the default for this submission (no warehouse/database/schema
were provisioned in Snowflake when the vertical slice was first built).
This module creates them on first use if missing, sized to minimize credit
usage (XSMALL, AUTO_SUSPEND=60s, starts suspended). Same fact_events/
dim_citizen shape as the DuckDB version, so either can serve the analytical
layer described in SRS §18-19.

The `snowflake.connector` import is deferred so importing this module (or
running the test suite) never requires the driver or live credentials.
"""

from __future__ import annotations

import os

from sqlalchemy import select

from life100.db.models import CitizenRow, EventRow
from life100.db.session import make_engine, make_session_factory


def _get_connection():
    import snowflake.connector  # deferred import, see module docstring

    account = os.environ["SNOWFLAKE_ACCOUNT"]
    user = os.environ["SNOWFLAKE_USER"]
    password = os.environ["SNOWFLAKE_PASSWORD"]
    role = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
    warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE") or "LIFE100_WH"
    database = os.environ.get("SNOWFLAKE_DATABASE") or "LIFE100_DB"
    schema = os.environ.get("SNOWFLAKE_SCHEMA") or "PUBLIC"

    conn = snowflake.connector.connect(account=account, user=user, password=password, role=role)
    cur = conn.cursor()
    try:
        cur.execute(
            f"CREATE WAREHOUSE IF NOT EXISTS {warehouse} "
            "WITH WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE INITIALLY_SUSPENDED=TRUE"
        )
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {database}.{schema}")
        cur.execute(f"USE WAREHOUSE {warehouse}")
        cur.execute(f"USE DATABASE {database}")
        cur.execute(f"USE SCHEMA {schema}")
    finally:
        cur.close()
    return conn


def build_warehouse(database_url: str | None = None) -> dict[str, int]:
    """(Re)build fact_events / dim_citizen in real Snowflake from Postgres."""
    engine = make_engine(database_url)
    session_factory = make_session_factory(engine)
    with session_factory() as session:
        events = list(session.scalars(select(EventRow)))
        citizens = list(session.scalars(select(CitizenRow)))

    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE OR REPLACE TABLE fact_events (
                event_id STRING, event_type STRING, schema_version INT,
                simulation_id STRING, simulation_tick INT, simulation_time STRING,
                source_entity STRING, source_type STRING, city_id STRING,
                payload_json STRING, received_at TIMESTAMP_NTZ
            )
            """
        )
        cur.execute(
            """
            CREATE OR REPLACE TABLE dim_citizen (
                citizen_id STRING, name STRING, age INT, gender STRING,
                household_id STRING, occupation STRING
            )
            """
        )
        if events:
            cur.executemany(
                "INSERT INTO fact_events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [
                    (
                        e.event_id,
                        e.event_type,
                        e.schema_version,
                        e.simulation_id,
                        e.simulation_tick,
                        e.simulation_time,
                        e.source_entity,
                        e.source_type,
                        e.city_id,
                        str(e.payload),
                        e.received_at,
                    )
                    for e in events
                ],
            )
        if citizens:
            cur.executemany(
                "INSERT INTO dim_citizen VALUES (%s,%s,%s,%s,%s,%s)",
                [(c.citizen_id, c.name, c.age, c.gender, c.household_id, c.occupation) for c in citizens],
            )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return {"fact_events": len(events), "dim_citizen": len(citizens)}


def query_warehouse(sql: str) -> list[dict]:
    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()
