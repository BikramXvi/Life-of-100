"""Analytical warehouse pipeline. SRS §18, §19 — DuckDB stand-in for Snowflake.

No real Snowflake account was available for this submission (see SCOPE.md).
DuckDB plays the same architectural role: it is built from the Postgres
operational store on demand (`build_warehouse`), never on the simulation's
critical path, and structured as a small fact/dimension star schema exactly
like SRS §19 describes. Swapping in real Snowflake later means changing
where this module *writes*, not how it reads.
"""

from __future__ import annotations

import os

import duckdb
import pandas as pd
from sqlalchemy import select

from life100.db.models import CitizenRow, EventRow
from life100.db.session import make_engine, make_session_factory

EVENTS_COLUMNS = [
    "event_id",
    "event_type",
    "schema_version",
    "simulation_id",
    "simulation_tick",
    "simulation_time",
    "source_entity",
    "source_type",
    "city_id",
    "payload_json",
    "received_at",
]
CITIZENS_COLUMNS = ["citizen_id", "name", "age", "gender", "household_id", "occupation"]
DATES_COLUMNS = ["simulation_time", "year", "month", "day"]


def _parse_sim_time(sim_time: str) -> tuple[int, int, int]:
    # "YEAR_01_MONTH_02_DAY_15" -> (1, 2, 15)
    parts = sim_time.split("_")
    return int(parts[1]), int(parts[3]), int(parts[5])


def build_warehouse(database_url: str | None = None, duckdb_path: str | None = None) -> dict[str, int]:
    """(Re)build fact_events / dim_citizen / dim_date from Postgres.

    Returns a row-count summary. Safe to call repeatedly (a full rebuild,
    not an incremental append) — cheap enough at this population/event scale
    and much simpler to reason about for a 2-day submission.
    """
    duckdb_path = duckdb_path or os.environ.get("DUCKDB_PATH", "./warehouse.duckdb")
    engine = make_engine(database_url)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        events = list(session.scalars(select(EventRow)))
        citizens = list(session.scalars(select(CitizenRow)))

    events_df = pd.DataFrame(
        [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "schema_version": e.schema_version,
                "simulation_id": e.simulation_id,
                "simulation_tick": e.simulation_tick,
                "simulation_time": e.simulation_time,
                "source_entity": e.source_entity,
                "source_type": e.source_type,
                "city_id": e.city_id,
                "payload_json": str(e.payload),
                "received_at": e.received_at,
            }
            for e in events
        ],
        columns=EVENTS_COLUMNS,
    )

    citizens_df = pd.DataFrame(
        [
            {
                "citizen_id": c.citizen_id,
                "name": c.name,
                "age": c.age,
                "gender": c.gender,
                "household_id": c.household_id,
                "occupation": c.occupation,
            }
            for c in citizens
        ],
        columns=CITIZENS_COLUMNS,
    )

    date_rows = []
    for sim_time in sorted({e.simulation_time for e in events}):
        year, month, day = _parse_sim_time(sim_time)
        date_rows.append({"simulation_time": sim_time, "year": year, "month": month, "day": day})
    dates_df = pd.DataFrame(date_rows, columns=DATES_COLUMNS)

    con = duckdb.connect(duckdb_path)
    try:
        con.register("events_view", events_df)
        con.execute("CREATE OR REPLACE TABLE fact_events AS SELECT * FROM events_view")
        con.register("citizens_view", citizens_df)
        con.execute("CREATE OR REPLACE TABLE dim_citizen AS SELECT * FROM citizens_view")
        con.register("dates_view", dates_df)
        con.execute("CREATE OR REPLACE TABLE dim_date AS SELECT * FROM dates_view")
    finally:
        con.close()

    return {"fact_events": len(events_df), "dim_citizen": len(citizens_df), "dim_date": len(dates_df)}


def query_warehouse(sql: str, duckdb_path: str | None = None) -> list[dict]:
    """Run a read-only analytical query against the built warehouse."""
    duckdb_path = duckdb_path or os.environ.get("DUCKDB_PATH", "./warehouse.duckdb")
    con = duckdb.connect(duckdb_path, read_only=True)
    try:
        return con.execute(sql).fetch_df().to_dict(orient="records")
    finally:
        con.close()
