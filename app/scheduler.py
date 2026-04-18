"""
Celery beat scheduler for QueuePilot.

Periodically queries the database for stale credentials and enqueues
login_credential tasks for each one. Runs daily at 03:00.
"""

import logging
import os
from celery.schedules import crontab

from celery_app import celery
from utils.db import get_connection

REFRESH_INTERVAL_DAYS = int(os.getenv("REFRESH_INTERVAL_DAYS", "90"))


@celery.task
def enqueue_stale_credentials() -> str:
    """
    Finds all active credentials not refreshed within REFRESH_INTERVAL_DAYS
    and dispatches a login_credential task for each one.

    Runs daily via Celery beat at 03:00 Stockholm time.

    Returns:
        A summary string with the number of tasks enqueued.
    """
    from tasks import login_credential

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT c.site, c.customer_id, s.system_type
        FROM credentials c
        JOIN sites s ON s.url_name = c.site
        WHERE c.active = 1
          AND (
            c.last_login IS NULL
            OR c.last_login < NOW() - INTERVAL %s DAY
          )
        """,
        (REFRESH_INTERVAL_DAYS,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    for row in rows:
        login_credential.delay(row["site"], row["customer_id"], row["system_type"])
        logging.info(
            "Enqueued %s / customer_id=%s (system: %s)",
            row["site"], row["customer_id"], row["system_type"]
        )

    logging.info("Enqueued %d stale credentials", len(rows))
    return f"enqueued:{len(rows)}"


# Beat schedule — runs daily at 03:00
celery.conf.beat_schedule = {
    "refresh-stale-queues": {
        "task": "scheduler.enqueue_stale_credentials",
        "schedule": crontab(hour=3, minute=0),
    }
}
