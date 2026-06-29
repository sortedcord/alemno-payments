import asyncio
from datetime import datetime, date
from typing import Any, Dict, List
from celery import Celery
from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.repositories.job_repository import JobRepository
from app.db.models.transaction import Transaction
from app.db.models.job_summary import JobSummary
from app.clients.exchange_rate_client import ExchangeRateClient

exchange_rate_client = ExchangeRateClient()


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
    generate narrative summary, and persist results to Transaction and JobSummary tables.
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

            db_transactions = []
            total_spend_inr = 0.0
            total_spend_usd = 0.0
            merchant_spends: Dict[str, float] = {}
            anomaly_count = 0

            USD_TO_INR = await exchange_rate_client.get_usd_to_inr_rate()

            for t in transactions:
                txn_id = t["txn_id"]
                raw_date = t["date"]
                # Parse date string to datetime.date object
                parsed_date = (
                    date.fromisoformat(raw_date)
                    if isinstance(raw_date, str)
                    else raw_date
                )
                merchant = t["merchant"].strip()
                amount = float(t["amount"])
                currency = t.get("currency", "INR").strip().upper()
                category = t.get("category", "General")
                account_id = t.get("account_id")

                # Spend calculation and currency conversion
                if currency == "USD":
                    amt_usd = amount
                    amt_inr = amount * USD_TO_INR
                else:
                    amt_inr = amount
                    amt_usd = amount / USD_TO_INR

                total_spend_inr += amt_inr
                total_spend_usd += amt_usd

                # Aggregate merchant spend (in USD for standardization)
                merchant_spends[merchant] = merchant_spends.get(merchant, 0.0) + amt_usd

                # Heuristic Anomaly detection
                is_anomaly = False
                anomaly_reason = None
                if amt_usd > 5000.0:
                    is_anomaly = True
                    anomaly_reason = "High value transaction (> $5,000 USD equivalent)"
                else:
                    desc_lower = merchant.lower()
                    if any(
                        k in desc_lower
                        for k in ["suspend", "hack", "error", "unknown", "fraud"]
                    ):
                        is_anomaly = True
                        anomaly_reason = "Suspicious merchant keyword"

                if is_anomaly:
                    anomaly_count += 1

                # Mock
                llm_failed = False
                llm_category = category.capitalize() if category else "General"
                llm_raw_response = f'{{"category": "{llm_category}", "confidence": 0.95, "status": "processed"}}'

                db_txn = Transaction(
                    job_id=job_id,
                    txn_id=txn_id,
                    date=parsed_date,
                    merchant=merchant,
                    amount=amount,
                    currency=currency,
                    status="cleaned",
                    category=category,
                    account_id=account_id,
                    is_anomaly=is_anomaly,
                    anomaly_reason=anomaly_reason,
                    llm_category=llm_category,
                    llm_raw_response=llm_raw_response,
                    llm_failed=llm_failed,
                )
                db_transactions.append(db_txn)

            await repo.add_transactions(db_transactions)

            top_merchant = (
                max(merchant_spends, key=merchant_spends.get)
                if merchant_spends
                else "None"
            )
            risk_level = "Low"
            if anomaly_count > 2:
                risk_level = "High"
            elif anomaly_count > 0:
                risk_level = "Medium"

            narrative = (
                f"Successfully parsed and clean-processed {len(transactions)} transaction records. "
                f"Total spend is INR {total_spend_inr:,.2f} (${total_spend_usd:,.2f} USD). "
                f"Top merchant by spend volume is '{top_merchant}' with total of ${merchant_spends.get(top_merchant, 0):,.2f} USD. "
                f"Scan flagged {anomaly_count} potential anomalies, resulting in a overall risk level of '{risk_level}'."
            )

            # Build top merchants dict sorted by spend limit (keep top 5)
            sorted_merchants = sorted(
                merchant_spends.items(), key=lambda x: x[1], reverse=True
            )[:5]
            top_merchants_json = {
                merchant: round(spend, 2) for merchant, spend in sorted_merchants
            }

            # Create job summary
            summary = JobSummary(
                job_id=job_id,
                total_spend_inr=round(total_spend_inr, 2),
                total_spend_usd=round(total_spend_usd, 2),
                top_merchants=top_merchants_json,
                anomaly_count=anomaly_count,
                narrative=narrative,
                risk_level=risk_level,
            )
            await repo.add_summary(summary)

            # Update job state
            await repo.update(
                job,
                status="completed",
                row_count_raw=len(transactions),
                row_count_clean=len(db_transactions),
                completed_at=datetime.utcnow(),
            )
            await db.commit()
            logger.info(f"Job {job_id} processing completed successfully.")

        except Exception as e:
            logger.exception(f"Error processing job {job_id}")
            await repo.update(
                job,
                status="failed",
                error_message=str(e),
                completed_at=datetime.utcnow(),
            )
            await db.commit()
            raise e
