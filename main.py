import os
import argparse
import mysql.connector
from dotenv import load_dotenv

from sites.momentum import run

load_dotenv(dotenv_path="app/config/.env")

def get_all_sites():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute(
        "SELECT url_name FROM sites"
    )
    result = cursor.fetchall()
    cursor.close()
    conn.close()

    if not result:
        raise Exception(
            "Inga uppgifter hittades för alla sites")

    print(result)
    return result

def main():
    parser = argparse.ArgumentParser(
        description="Run housing queue login & point check for a given site."
    )
    parser.add_argument(
        "--site",
        type=str,
        required=True,
        help="Which site to run (e.g. 'kbab')"
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
