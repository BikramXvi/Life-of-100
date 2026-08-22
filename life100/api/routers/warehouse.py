from __future__ import annotations

from fastapi import APIRouter, HTTPException

from life100.warehouse.duckdb_pipeline import build_warehouse, query_warehouse

router = APIRouter(prefix="/warehouse", tags=["warehouse"])


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
