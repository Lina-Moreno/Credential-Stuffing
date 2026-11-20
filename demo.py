"""Generate virtual events, train once, evaluate held-out runs, save evidence."""

import csv
import math
import pickle
import random
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

from app import DB, RESULTS, connect, hasher, init_db
from detector import anomaly_scores, extract

TRAIN_SEEDS = (110, 111, 112, 113, 114)
VALIDATION_SEEDS = (210, 211)
TEST_SEEDS = (310, 311, 312)
FOREST_SEED = 42
DEMO_PASSWORD = "ClaveDemo2026!"
ACCOUNTS = [f"usuario_{i:02d}" for i in range(1, 11)]
# IPv4 ficticias de laboratorio. Cada dirección identifica el mismo origen
# durante una corrida; jamás se usa como destino de una solicitud.
LEGITIMATE_IPS = tuple(f"192.0.2.{i}" for i in range(1, 25))
SHARED_IP = "192.0.2.200"
DISTRIBUTED_IPS = tuple(f"198.51.100.{i}" for i in range(1, 7))


def generate_run(seed, attacks=False):
    rng = random.Random(seed)
    run_id = f"{'test' if attacks else 'normal'}_{seed}"
    base = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=seed)
    ordinary = []
    while len(ordinary) < 320:
        if rng.random() < 0.17:
            source = SHARED_IP
            account = rng.choice(ACCOUNTS[:8])
            success = rng.random() < 0.83
        else:
            source_number = rng.randrange(24)
            source = LEGITIMATE_IPS[source_number]
            account = ACCOUNTS[source_number % len(ACCOUNTS)]
            success = rng.random() < 0.91
        ordinary.append((source, account, success, 0))
        if not success and rng.random() < 0.55 and len(ordinary) < 320:
            ordinary.append((source, account, True, 0))
    mixed = []
    attack_positions = set(rng.sample(range(65, 280), 100)) if attacks else set()
    for i, event in enumerate(ordinary):
        mixed.append(event)
        if i in attack_positions:
            # Six fictional IPv4 origins overlap on six accounts. Success can occur.
            mixed.append((DISTRIBUTED_IPS[rng.randrange(6)],
                          rng.choice(ACCOUNTS[:6]), rng.random() < 0.16, 1))
    events = []
    for i, (source, account, success, truth) in enumerate(mixed):
        events.append({"run_id": run_id,
                       "time": (base + timedelta(seconds=3 * i)).isoformat(),
                       "account": account, "source": source,
                       "success": success, "truth": truth})
    return events


def baseline_counts(events):
    counts = []
    prior = []
    for event in events:
        t = datetime.fromisoformat(event["time"])
        counts.append(sum(p["run_id"] == event["run_id"]
                          and p["source"] == event["source"]
                          and not p["success"]
                          and timedelta(0) < t - datetime.fromisoformat(p["time"]) <= timedelta(minutes=5)
                          for p in prior))
        prior.append(event)
    return counts


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def measures(truth, predicted, method):
    tp = sum(a == 1 and b == 1 for a, b in zip(truth, predicted))
    fp = sum(a == 0 and b == 1 for a, b in zip(truth, predicted))
    tn = sum(a == 0 and b == 0 for a, b in zip(truth, predicted))
    fn = sum(a == 1 and b == 0 for a, b in zip(truth, predicted))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {"metodo": method, "TP": tp, "FP": fp, "TN": tn, "FN": fn,
            "precision": precision, "recall": recall, "F1": f1}


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    RESULTS.mkdir(exist_ok=True)
    init_db()
    with connect() as db:
        for i, account in enumerate(ACCOUNTS):
            if not db.execute("SELECT 1 FROM users WHERE username=?", (account,)).fetchone():
                password = DEMO_PASSWORD if i == 0 else f"Ficticia-{i:02d}-2026!"
                db.execute("INSERT INTO users VALUES (?,?)", (account, hasher.hash(password)))

    train = [event for seed in TRAIN_SEEDS for event in generate_run(seed)]
    validation = [event for seed in VALIDATION_SEEDS for event in generate_run(seed)]
    testing = [event for seed in TEST_SEEDS for event in generate_run(seed, attacks=True)]
    model = IsolationForest(n_estimators=150, random_state=FOREST_SEED, n_jobs=1)
    model.fit(extract(train))
    threshold = percentile(anomaly_scores(model, extract(validation)), 0.95)
    baseline_threshold = math.ceil(percentile(baseline_counts(validation), 0.95))
    rows = extract(testing)
    scores = anomaly_scores(model, rows)
    baseline = [int(value > baseline_threshold) for value in baseline_counts(testing)]
    alerts = [int(score > threshold) for score in scores]
    truth = [event["truth"] for event in testing]
    metrics = [measures(truth, baseline, "contador_origen"),
               measures(truth, alerts, "isolation_forest")]
    predictions = []
    for event, feature, score, simple, alert in zip(testing, rows, scores, baseline, alerts):
        predictions.append({"corrida": event["run_id"], "hora": event["time"],
                            "cuenta": event["account"], "origen": event["source"],
                            "verificacion": "aceptada" if event["success"] else "rechazada",
                            "real": event["truth"], "alerta_contador": simple,
                            "puntaje": float(score), "alerta_bosque": alert,
                            "origenes_cuenta": feature[2], "otros_origenes_comunes": feature[4]})
    write_csv(RESULTS / "predicciones.csv", predictions, list(predictions[0]))
    write_csv(RESULTS / "metricas.csv", metrics, list(metrics[0]))
    with (RESULTS / "modelo.pkl").open("wb") as file:
        pickle.dump({"model": model, "threshold": threshold}, file)

    with connect() as db:
        db.execute("DELETE FROM simulated_attempts")
        db.executemany("""INSERT INTO simulated_attempts
            (run_id, time, account, source, success, score, alert,
             origins_account, related_origins, truth, baseline_alert)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            [(e["run_id"], e["time"], e["account"], e["source"], int(e["success"]),
              float(score), alert, feature[2], feature[4], e["truth"], simple)
             for e, feature, score, alert, simple in zip(testing, rows, scores, alerts, baseline)])

    result = metrics[1]
    matrix = [[result["TN"], result["FP"]], [result["FN"], result["TP"]]]
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], ["Legítimo", "Sospechoso"])
    ax.set_yticks([0, 1], ["Legítimo", "Sospechoso"])
    ax.set_xlabel("Predicho")
    ax.set_ylabel("Real")
    ax.set_title("Matriz de confusión: Isolation Forest")
    for y in range(2):
        for x in range(2):
            ax.text(x, y, matrix[y][x], ha="center", va="center")
    fig.tight_layout()
    fig.savefig(RESULTS / "matriz_confusion.png", dpi=140)
    plt.close(fig)
    print(f"Eventos de prueba: {len(testing)}; umbral bosque: {threshold:.4f}; umbral contador: >{baseline_threshold} fallos anteriores")
    for metric in metrics:
        print(metric)
    print(f"Evidencias: {RESULTS}")


if __name__ == "__main__":
    main()
