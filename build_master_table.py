"""Regenerate the site's master table from the match database. See portal/master_table.py."""

import sys

from db.rating_history import rating_history_from_db
from portal import master_table

sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    master_table.main(rating_history_from_db())
