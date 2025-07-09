from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession
import structlog
from typing import List, Optional, Literal
from .database import get_session, get_db
from .models import AgentRun, Feedback, VisitedUrl, EvaluatedSnippet
from fastapi.responses import StreamingResponse
import pandas as pd
import io
import zipfile
from sqlmodel import select


router = APIRouter()
admin_router = APIRouter(prefix="/admin", tags=["Admin"])
log = structlog.get_logger()


class FeedbackPayload(BaseModel):
    run_id: int = Field(..., description="Agent run ID")
    feedback: str = Field(..., pattern="^(yes|no)$", description="yes or no")


async def _store_feedback(session: AsyncSession, run_id: int, feedback: str) -> None:
    run = await session.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="AgentRun not found")
    fb = Feedback(run_id=run_id, value=feedback.lower())
    session.add(fb)
    await session.commit()
    log.info("Feedback received", run_id=run_id, feedback=feedback)

@router.post("/feedback")
async def receive_feedback(payload: FeedbackPayload, session: AsyncSession = Depends(get_session)):
    """Record yes/no feedback for a run via POST."""
    await _store_feedback(session, payload.run_id, payload.feedback)
    return {"message": "Feedback recorded"}


@router.get("/feedback")
async def receive_feedback_get(
    run_id: int = Query(..., description="Agent run ID"),
    feedback: str = Query(..., pattern="^(yes|no)$", description="yes or no"),
    session: AsyncSession = Depends(get_session),
):
    """Record yes/no feedback for a run via GET (from email links)."""
    await _store_feedback(session, run_id, feedback)
    return {"message": "Feedback recorded"}

@router.get("/runs/{run_id}/results")
async def get_run_results(run_id: int, session: AsyncSession = Depends(get_session)):
    """Retrieve the detailed results (outputs and search terms) for a specific agent run."""
    run = await session.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="AgentRun not found")
    
    if run.result is None:
        return {"message": "Results not yet available or run failed", "status": run.status}

    return {
        "run_id": run.id,
        "status": run.status,
        "completed_at": run.completed_at,
        "results": run.result
    }

@router.get("/runs")
async def get_all_runs(
    limit: int = Query(10, description="Limit the number of runs returned"),
    offset: int = Query(0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session)
):
    """Retrieve a list of all agent runs, optionally with limit and offset."""
    statement = select(AgentRun).order_by(AgentRun.started_at.desc()).offset(offset).limit(limit)
    runs = (await session.exec(statement)).all()
    
    return [
        {
            "id": run.id,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "status": run.status,
            "error_message": run.error_message,
            "has_results": run.result is not None # Indicate if results exist without sending full JSON
        }
        for run in runs
    ]

@admin_router.get("/download-database-csv", response_class=StreamingResponse)
async def download_database_csv(session: AsyncSession = Depends(get_session)):
    """
    Downloads all database tables as a single ZIP file containing multiple CSVs.
    """
    log.info("Database download requested.")
    
    zip_buffer = io.BytesIO()

    tables = {
        "agent_runs": AgentRun,
        "feedback": Feedback,
        "visited_urls": VisitedUrl,
        "evaluated_snippets": EvaluatedSnippet,
    }

    # CORRECTED: Use a standard 'with' context manager for zipfile, not 'async with'
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for table_name, model in tables.items():
            try:
                statement = select(model)
                results = await session.exec(statement)
                data = results.all()

                if data:
                    # CORRECTED: Use .dict() for better compatibility with SQLModel versions
                    dict_data = [row.dict() for row in data]
                    
                    df = pd.DataFrame(dict_data)
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False)
                    csv_buffer.seek(0)
                    
                    zipf.writestr(f"{table_name}.csv", csv_buffer.getvalue())
                    log.info(f"Added {table_name} to download archive.", record_count=len(data))
                else:
                    log.info(f"No data in {table_name} to download.")
                    zipf.writestr(f"{table_name}.csv", "")

            except Exception as e:
                log.error(f"Failed to process table {table_name} for download.", error=str(e))
                zipf.writestr(f"{table_name}_error.txt", f"Failed to export table: {e}")

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=database_export.zip"},
    )

@admin_router.post("/reset-database")
async def reset_database(
    tables_to_reset: List[Literal["agent_runs", "feedback", "visited_urls", "evaluated_snippets", "all"]] = Query(..., description="Specify which tables to reset, or 'all' to reset everything."),
    session: AsyncSession = Depends(get_session)
):
    """
    Deletes all data from the specified database tables.
    **This is a destructive operation.**
    """
    log.warning("Database reset requested.", tables=tables_to_reset)

    models_map = {
        "agent_runs": AgentRun,
        "feedback": Feedback,
        "visited_urls": VisitedUrl,
        "evaluated_snippets": EvaluatedSnippet
    }

    if "all" in tables_to_reset:
        target_models = list(models_map.values())
    else:
        target_models = [models_map[table_name] for table_name in tables_to_reset if table_name in models_map]

    if not target_models:
        raise HTTPException(status_code=400, detail="No valid tables specified for reset.")

    deleted_counts = {}
    try:
        for model in target_models:
            statement = select(model)
            results = await session.exec(statement)
            records_to_delete = results.all()
            
            count = 0
            for record in records_to_delete:
                await session.delete(record)
                count += 1
            
            deleted_counts[model.__tablename__] = count
        
        await session.commit()
        log.info("Database tables reset successfully.", deleted_counts=deleted_counts)

        return {"message": "Database reset successfully.", "details": deleted_counts}
    except Exception as e:
        await session.rollback()
        log.error("Failed to reset database.", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to reset database: {e}")
