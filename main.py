import argparse
import sys

from sites.kbab import run_kbab
from sites.obo import run_obo
from sites.abbostader import run_ab_bostader


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

    if site == "kbab":
        run_kbab()
    elif site == "obo":
        run_obo()
    elif site == "abbostader":
        run_ab_bostader()
    else:
        print(f"❌ Unknown site: {site}")
        sys.exit(1)


if __name__ == "__main__":
    main()
