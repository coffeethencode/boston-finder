#!/usr/bin/env python3
"""
Rate a venue after you've been there.

Usage:
    python3 rate_venue.py "Row 34" 5 "Perfect Duxbury, great bar scene"
    python3 rate_venue.py "Loco Taqueria" skip "Too chaotic, not my scene"
    python3 rate_venue.py --list
"""

import sys
sys.path.insert(0, "/Users/brian/python-projects")
from boston_finder.ratings import rate, summary

if len(sys.argv) == 2 and sys.argv[1] == "--list":
    print("\nYour venue ratings:\n")
    print(summary())
    print()
    sys.exit(0)

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

venue = sys.argv[1]
raw_rating = sys.argv[2]
note = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""

if raw_rating == "skip":
    rate(venue, "skip", note)
else:
    try:
        r = int(raw_rating)
        if not 1 <= r <= 5:
            raise ValueError
        rate(venue, r, note)
    except ValueError:
        print("Rating must be 1-5 or 'skip'")
        sys.exit(1)
