from datetime import datetime, timedelta
import structlog
from fastapi import Depends
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import EvaluatedSnippet, AgentRun
from .openai_evaluator import evaluate_snippets_for_brand_fit
from .email_sender import send_email

log = structlog.get_logger()

async def compile_and_send_daily_email(db: Session = Depends(get_db)) -> None:
    """Compile top evaluated snippets from the last day and send via email."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)

    brand_snippets = (
        db.query(EvaluatedSnippet)
        .filter(
            EvaluatedSnippet.timestamp >= start_time,
            EvaluatedSnippet.timestamp <= end_time,
            EvaluatedSnippet.category == "brand_health",
        )
        .order_by(EvaluatedSnippet.relevance_score.desc())
        .limit(10)
        .all()
    )

    market_snippets = (
        db.query(EvaluatedSnippet)
        .filter(
            EvaluatedSnippet.timestamp >= start_time,
            EvaluatedSnippet.timestamp <= end_time,
            EvaluatedSnippet.category == "market_intelligence",
        )
        .order_by(EvaluatedSnippet.relevance_score.desc())
        .limit(10)
        .all()
    )

    lines = ["Top Brand Health Snippets:"]
    for snip in brand_snippets:
        summary = await evaluate_snippets_for_brand_fit(snip.url, snip.content_summary)
        if summary:
            lines.append(f"- {summary.emoji} {summary.headline} {summary.link}")
        else:
            lines.append(f"- {snip.title or snip.url} {snip.url}")

    lines.append("\nTop Market Intelligence Snippets:")
    for snip in market_snippets:
        summary = await evaluate_snippets_for_brand_fit(snip.url, snip.content_summary)
        if summary:
            lines.append(f"- {summary.emoji} {summary.headline} {summary.link}")
        else:
            lines.append(f"- {snip.title or snip.url} {snip.url}")

    settings = get_settings()
    latest_run = db.query(AgentRun).order_by(AgentRun.completed_at.desc()).first()
    run_id = latest_run.id if latest_run else 0
    yes_url = f"{settings.app_base_url.rstrip('/')}/feedback?run_id={run_id}&feedback=yes"
    no_url = f"{settings.app_base_url.rstrip('/')}/feedback?run_id={run_id}&feedback=no"
    lines.append("")
    lines.append(f"Was this email helpful? Yes: {yes_url} | No: {no_url}")

    body = "\n".join(lines)
    subject = f"Daily Summary {end_time.strftime('%Y-%m-%d')}"

    try:
        send_email(subject, body)
        log.info("Daily email compiled and sent")
    except Exception as exc:  # pragma: no cover - runtime safety
        log.error("Failed to send daily email", error=str(exc), exc_info=True)
