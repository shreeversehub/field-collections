from datetime import date


def score_loan(loan, not_reachable, today):
    """Explainable 0-100 priority score. Weights are assumptions (see README)."""
    pd, st = loan["promise_date"], loan["promise_status"]
    prom = {"broken": 25, "none": 8, "kept": 0}.get(st, 0)
    why = {"broken": f"Promise broken on {pd}", "none": "No payment promise yet",
           "kept": "Last promise kept", "pending": f"Promise due {pd}"}[st]
    if st == "pending":
        prom = 12 if (date.fromisoformat(pd) - today).days <= 1 else 3
    parts = [
        (min(loan["dpd"], 30) / 30 * 40, f"{loan['dpd']} days overdue"),
        (min(loan["outstanding"] / 700000, 1) * 25, f"Rs {loan['outstanding']:,} outstanding"),
        (prom, why),
        (min(not_reachable * 4, 10), f"{not_reachable} failed contact attempts"),
    ]
    top = sorted(parts, key=lambda p: -p[0])
    return round(sum(p[0] for p in parts), 1), [p[1] for p in top if p[0] > 0][:3]
