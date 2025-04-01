"""
QueuePilot - Main Entry Script

This script is the main entry point for the QueuePilot system.
It retrieves queue points from various Momentum-based housing platforms 
by logging in as specific customers and running the scraping logic per site.

Usage:
    python main.py --site kbab
    python main.py --site all

Requires a connected MariaDB database with:
  - `sites` table: defines url_name and API details
  - `credentials` table: defines login credentials per customer and site
"""

import argparse
from typing import List, Dict
from sites.momentum import run
from utils.db import get_connection


def get_all_sites() -> List[Dict[str, str]]:
    """
    Retrieve all site entries from the database.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing 'url_name' for each site.

    Raises:
        Exception: If no site data is found in the database.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute(
        "SELECT url_name FROM sites"
    )
    result = cursor.fetchall()
    cursor.close()
    conn.close()

    if not result:
        raise LookupError("No data found for all sites")

    return result


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
    site = args.site.lower()

    sites = get_all_sites()

    if site == "all":
        for site in sites:
            run(site["url_name"])
    else:
        run(site)


if __name__ == "__main__":
    main()
