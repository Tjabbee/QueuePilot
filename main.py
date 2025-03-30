import argparse
import sys

# AUTOIMPORT
from sites.momentum.nynasbo import run_nynasbo
from sites.momentum.byggvesta import run_byggvesta
from sites.momentum.kbab import run_kbab
from sites.momentum.obo import run_obo
from sites.abbostader import run_ab_bostader
from sites.hemvist import run_hemvist


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

    if site == "all":
        # FUNCTION
        run_ab_bostader()
        run_byggvesta()
        run_hemvist()
        run_kbab()
        run_nynasbo()
        run_obo()
    elif site == "kbab":
        run_kbab()
    # AUTORUN
    elif args.site == 'nynasbo':
        run_nynasbo()
    elif args.site == 'byggvesta':
        run_byggvesta()
    elif site == "obo":
        run_obo()
    elif site == "abbostader":
        run_ab_bostader()
    elif site == "hemvist":
        run_hemvist()
    else:
        print(f"❌ Unknown site: {site}")
        sys.exit(1)


if __name__ == "__main__":
    main()
