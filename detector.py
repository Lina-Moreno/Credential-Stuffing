"""Causal five-minute features shared by the browser login and simulation."""

from datetime import datetime, timedelta

FEATURE_NAMES = (
    "intentos_origen", "cuentas_origen", "origenes_cuenta",
    "fraccion_fallos_cuenta", "otros_origenes_cuentas_comunes",
)
WINDOW = timedelta(minutes=5)


def features_for_event(event, previous):
    """Use only prior events from this run and the five minutes before event."""
    now = datetime.fromisoformat(event["time"])
    recent = [p for p in previous
              if p["run_id"] == event["run_id"]
              and now - WINDOW <= datetime.fromisoformat(p["time"]) <= now]
    # Only the supplied prior list is examined, so equal-time earlier events count.
    source = event["source"]
    account = event["account"]
    by_source = [p for p in recent if p["source"] == source]
    by_account = [p for p in recent if p["account"] == account]
    visited = {p["account"] for p in by_source}
    related = {p["source"] for p in recent
               if p["source"] != source and p["account"] in visited}
    return (
        len(by_source),
        len(visited),
        len({p["source"] for p in by_account}),
        sum(not p["success"] for p in by_account) / len(by_account)
        if by_account else 0.0,
        len(related),
    )


def extract(events):
    """Return features in event order; never inspect the current result/label."""
    prior = []
    rows = []
    for event in events:
        rows.append(features_for_event(event, prior))
        prior.append(event)
    return rows


def anomaly_scores(model, rows):
    """Higher means more anomalous; these values are not probabilities."""
    return -model.decision_function(rows)
