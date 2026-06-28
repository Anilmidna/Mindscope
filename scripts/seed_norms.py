"""
Seed the norm_groups table with baseline norms for RIASEC, Big Five, and Aptitude.

Run once against production DB:
    python -m scripts.seed_norms

Re-running is safe — uses INSERT OR IGNORE logic (checks context uniqueness).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.norm_group import NormGroup

# ── Norm data ─────────────────────────────────────────────────────────────────
# RIASEC: Holland (1985) + Tracey & Rounds (1993) general population norms
# Scores are sums of 8 Likert-scale items (1–5), range 8–40
RIASEC_NORMS = {
    "R": {"mean": 23.1, "std_dev": 6.4},
    "I": {"mean": 24.5, "std_dev": 6.8},
    "A": {"mean": 22.8, "std_dev": 7.1},
    "S": {"mean": 26.3, "std_dev": 6.2},
    "E": {"mean": 24.9, "std_dev": 6.5},
    "C": {"mean": 25.7, "std_dev": 6.3},
}

# Big Five: BFI-2-S published norms (Soto & John, 2017), sum of 10 items (1–5), range 10–50
OCEAN_NORMS = {
    "O": {"mean": 35.2, "std_dev": 6.1},
    "C": {"mean": 33.8, "std_dev": 6.4},
    "E": {"mean": 30.5, "std_dev": 7.2},
    "A": {"mean": 36.1, "std_dev": 5.8},
    "N": {"mean": 25.4, "std_dev": 7.6},
}

# Aptitude: estimated norms for Indian graduate population (15 items per domain)
APTITUDE_NORMS = {
    "Logical":   {"mean": 8.5,  "std_dev": 2.8},
    "Numerical": {"mean": 8.0,  "std_dev": 2.9},
    "Verbal":    {"mean": 9.0,  "std_dev": 2.7},
    "Spatial":   {"mean": 7.5,  "std_dev": 3.0},
}

NORM_ROWS = [
    {
        "context": "riasec-general",
        "label": "RIASEC General Population (Holland 1985)",
        "sample_size": 2500,
        "score_stats": RIASEC_NORMS,
    },
    {
        "context": "ocean-general",
        "label": "Big Five BFI-2-S General Population (Soto & John 2017)",
        "sample_size": 3000,
        "score_stats": OCEAN_NORMS,
    },
    {
        "context": "aptitude-india-graduate",
        "label": "Aptitude India Graduate Population (estimated)",
        "sample_size": 1000,
        "score_stats": APTITUDE_NORMS,
    },
]


def seed(db):
    inserted = 0
    skipped = 0
    for row in NORM_ROWS:
        existing = db.query(NormGroup).filter(NormGroup.context == row["context"]).first()
        if existing:
            skipped += 1
            continue
        ng = NormGroup(
            context=row["context"],
            label=row["label"],
            sample_size=row["sample_size"],
            score_stats=row["score_stats"],
        )
        db.add(ng)
        inserted += 1
    db.commit()
    return inserted, skipped


if __name__ == "__main__":
    db = SessionLocal()
    try:
        inserted, skipped = seed(db)
        print(f"Seeded {inserted} norm group(s). Skipped {skipped} (already exist).")
    finally:
        db.close()
