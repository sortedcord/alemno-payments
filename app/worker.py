import asyncio
from typing import Any, Dict, List
from celery import Celery
from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.repositories.job_repository import JobRepository

# Define Celery app
celery_app = Celery(
    "alemno_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Optional configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


def run_async(coro):
    """Helper to run async functions synchronously in Celery worker context"""
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(name="tasks.process_transaction_job")
def process_transaction_job(job_id: str, transactions: List[Dict[str, Any]]):
    """
    Background job to clean transactions, detect anomalies, calculate spend breakdown,
    generate narrative summary, and persist results.
    """
    logger.info(f"Starting Celery task to process job_id: {job_id}")
    return run_async(_process_job_async(job_id, transactions))


async def _process_job_async(job_id: str, transactions: List[Dict[str, Any]]):
    async with AsyncSessionLocal() as db:
        repo = JobRepository(db)
        job = await repo.get_by_id(job_id)
        if not job:
            logger.error(f"Job with ID {job_id} not found in database.")
            return

        try:
            # Update status to processing
            await repo.update(job, status="processing")
            await db.commit()

            # 1. Clean transactions
            cleaned_transactions = []
            total_amount = 0.0
            categories = {}
            for t in transactions:
                # Clean description and category
                desc = t["description"].strip()
                cat = t["category"].strip().capitalize()
                amount = float(t["amount"])

                total_amount += amount
                categories[cat] = categories.get(cat, 0.0) + amount

                cleaned_transactions.append(
                    {
                        "transaction_id": t["transaction_id"],
                        "date": t["date"],
                        "amount": amount,
                        "category": cat,
                        "description": desc,
                    }
                )

            # 2. Flag anomalies (Heuristic: > $5,000, or containing suspicious keywords)
            anomalies = []
            for t in cleaned_transactions:
                is_anomaly = False
                reasons = []

                if t["amount"] > 5000.0:
                    is_anomaly = True
                    reasons.append("High value transaction (> $5,000)")

                desc_lower = t["description"].lower()
                if any(
                    k in desc_lower
                    for k in ["suspend", "hack", "error", "unknown", "fraud"]
                ):
                    is_anomaly = True
                    reasons.append("Suspicious keyword found in description")

                if is_anomaly:
                    anomalies.append({**t, "reasons": reasons})

            # 3. Spend breakdown (percentage & absolute)
            spend_breakdown = {}
            for cat, amount in categories.items():
                pct = (amount / total_amount * 100) if total_amount > 0 else 0
                spend_breakdown[cat] = {
                    "total_spend": round(amount, 2),
                    "percentage": round(pct, 2),
                }

            # 4. Generate LLM Narrative Summary (Mocked / simulated intelligence)
            top_category = max(categories, key=categories.get) if categories else "None"
            anomaly_pct = (
                (len(anomalies) / len(transactions) * 100) if transactions else 0
            )
            narrative = (
                f"Successfully parsed and processed {len(transactions)} transaction records. "
                f"Total spend across all transactions is ${total_amount:,.2f}. "
                f"We identified '{top_category}' as the largest spending category, amounting to "
                f"${categories.get(top_category, 0):,.2f} ({spend_breakdown.get(top_category, {}).get('percentage', 0)}% of total). "
                f"A scan for transactional anomalies flagged {len(anomalies)} records ({anomaly_pct:.1f}% of total). "
                f"Most anomalies were triggered by high transaction limits or unrecognized transaction descriptions. "
                f"Recommendation: Review flagged anomalies to prevent potential leakages."
            )

            # Build full structured output
            results = {
                "cleaned_transactions": cleaned_transactions,
                "flagged_anomalies": anomalies,
                "spend_breakdown": spend_breakdown,
                "narrative_summary": narrative,
            }

            # Build high-level stats for status summary
            summary = {
                "total_rows": len(transactions),
                "total_amount": round(total_amount, 2),
                "anomalies_count": len(anomalies),
                "top_category": top_category,
            }

            # Update job in DB
            await repo.update(
                job,
                status="completed",
                row_count=len(transactions),
                summary=summary,
                results=results,
            )
            await db.commit()
            logger.info(f"Job {job_id} processing completed successfully.")

        except Exception as e:
            logger.exception(f"Error processing job {job_id}")
            await repo.update(job, status="failed")
            await db.commit()
            raise e
