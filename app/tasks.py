import logging
from celery_app import celery
from sites import momentum, kjellberg

HANDLERS = {
    "momentum": momentum.run,
    "vitec": kjellberg.run,
    "kjellberg": kjellberg.run,
}


@celery.task(bind=True, max_retries=3, default_retry_delay=120)
def login_credential(self, site: str, customer_id: int, system_type: str) -> str:
    """
    Logs in to a single housing queue site for a specific user credential.

    Retries up to 3 times with a 120-second delay on failure.

    Args:
        site: The site url_name (e.g. 'kbab').
        customer_id: The credential owner's ID.
        system_type: 'momentum', 'vitec', or 'kjellberg'.

    Returns:
        A status string logged on completion.
    """
    handler = HANDLERS.get(system_type)
    if not handler:
        raise ValueError(f"Unknown system_type '{system_type}' for site '{site}'")

    try:
        handler(site, customer_id)
        return f"ok:{site}:{customer_id}"
    except Exception as exc:
        logging.exception("login_credential failed for %s customer %s", site, customer_id)
        raise self.retry(exc=exc)
