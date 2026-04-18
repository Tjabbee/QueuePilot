"""
QueuePilot - Main Entry Script

This script is the main entry point for the QueuePilot system.
It retrieves queue points from various housing platforms by logging in
as specific customers and running the scraping logic per site.

Usage:
    python main.py --site kbab
    python main.py --site all

Requires a connected MariaDB database with:
  - `sites` table: defines url_name, system_type, and API details
  - `credentials` table: defines login credentials per customer and site
"""

import argparse
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

from sites import momentum, kjellberg
from utils.db import get_connection, ensure_schema

HANDLERS = {
    "momentum": momentum.run,
    "vitec": kjellberg.run,
    "kjellberg": kjellberg.run,  # legacy alias
}

MAX_WORKERS = int(os.getenv("MAX_WORKERS", "10"))


def get_all_sites() -> List[Dict[str, str]]:
    """
    Retrieve all sites that have at least one active credential for customer 1.

    Returns:
        List[Dict]: List of dicts with 'url_name' and 'system_type'.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute("""
        SELECT s.url_name, s.system_type
        FROM sites s
        INNER JOIN credentials c ON c.site = s.url_name AND c.customer_id = 1 AND c.active = 1
    """)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_site(url_name: str) -> Dict[str, str]:
    """
    Retrieve a single site entry by url_name.

    Args:
        url_name (str): The site identifier.

    Returns:
        Dict with 'url_name' and 'system_type'.

    Raises:
        LookupError: If the site is not found.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute("SELECT url_name, system_type FROM sites WHERE url_name=%s", (url_name,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        raise LookupError(f"Site '{url_name}' not found in the database.")

    return result


def dispatch(url_name: str, system_type: str) -> None:
    """
    Dispatches execution to the correct site handler.

    Args:
        url_name (str): The site's identifier.
        system_type (str): The platform type (e.g. 'momentum', 'kjellberg').
    """
    handler = HANDLERS.get(system_type)
    if handler:
        handler(url_name)
    else:
        logging.warning("Unknown system_type '%s' for site '%s'. Skipping.", system_type, url_name)


def main() -> None:
    """
    Entry point for running the queue point retrieval script.

    Parses command-line arguments to determine whether to run for a specific
    site or for all available sites in the database.
    """
    parser = argparse.ArgumentParser(
        description="Run housing queue login & point check for a given site."
    )
    parser.add_argument(
        "--site",
        type=str,
        required=True,
        help="Which site to run (e.g. 'kbab' or 'all')"
    )

    args = parser.parse_args()
    site_arg = args.site.lower()

    if site_arg == "all":
        sites = get_all_sites()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(dispatch, s["url_name"], s["system_type"]): s for s in sites}
            for future in as_completed(futures):
                site = futures[future]
                try:
                    future.result()
                except Exception:
                    logging.exception("Site %s failed", site["url_name"])
    else:
        site = get_site(site_arg)
        dispatch(site["url_name"], site.get("system_type", "momentum"))


ensure_schema()

if __name__ == "__main__":
    main()
