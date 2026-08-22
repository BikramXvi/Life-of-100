from __future__ import annotations

from fastapi import APIRouter, HTTPException

from life100.warehouse.duckdb_pipeline import build_warehouse, query_warehouse

router = APIRouter(prefix="/warehouse", tags=["warehouse"])


@router.post("/build-snowflake")
def rebuild_warehouse_snowflake() -> dict:
    """Real Snowflake path (SRS §18-19) — opt-in alternative to the DuckDB
    stand-in below; see SCOPE.md. Requires SNOWFLAKE_* env vars."""
    from life100.warehouse.snowflake_pipeline import build_warehouse as build_snowflake

    try:
        return build_snowflake()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Snowflake warehouse build failed: {exc}") from exc


@router.get("/summary-snowflake")
def warehouse_summary_snowflake() -> dict:
    from life100.warehouse.snowflake_pipeline import query_warehouse as query_snowflake

    try:
        counts = query_snowflake(
            "SELECT event_type, COUNT(*) AS n FROM fact_events GROUP BY event_type ORDER BY n DESC"
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Snowflake warehouse not built yet: {exc}") from exc
    return {"event_type_counts": counts}


@router.post("/build")
def rebuild_warehouse() -> dict:
    """(Re)build the DuckDB analytical warehouse from Postgres (SRS §18-19,
    Snowflake stand-in — see SCOPE.md)."""
    try:
        return build_warehouse()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Warehouse build failed: {exc}") from exc


@router.get("/summary")
def warehouse_summary() -> dict:
    try:
        counts = query_warehouse(
            "SELECT event_type, COUNT(*) AS n FROM fact_events GROUP BY event_type ORDER BY n DESC"
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Warehouse not built yet: {exc}") from exc
    return {"event_type_counts": counts}
