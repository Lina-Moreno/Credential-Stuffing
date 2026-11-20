"""Local teaching login and read-only view of the latest simulation."""

import csv
import pickle
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from flask import Flask, render_template, request

from detector import anomaly_scores, features_for_event

ROOT = Path(__file__).resolve().parent
DB = ROOT / "demo.sqlite3"
RESULTS = ROOT / "resultados"
MODEL = RESULTS / "modelo.pkl"
app = Flask(__name__)
hasher = PasswordHasher()
UI_JS = ROOT / "static" / "ui" / "app.js"
UI_CSS = ROOT / "static" / "ui" / "app.css"


@contextmanager
def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def init_db():
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS manual_attempts (
                id INTEGER PRIMARY KEY, time TEXT NOT NULL, account TEXT NOT NULL,
                source TEXT NOT NULL, success INTEGER NOT NULL,
                score REAL, alert INTEGER
            );
            CREATE TABLE IF NOT EXISTS simulated_attempts (
                id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, time TEXT NOT NULL,
                account TEXT NOT NULL, source TEXT NOT NULL, success INTEGER NOT NULL,
                score REAL NOT NULL, alert INTEGER NOT NULL,
                origins_account INTEGER NOT NULL, related_origins INTEGER NOT NULL,
                truth INTEGER NOT NULL, baseline_alert INTEGER NOT NULL
            );
        """)


def read_csv(name):
    path = RESULTS / name
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def ui_version():
    """Refresh local compiled assets after a rebuild without a second server."""
    return max((path.stat().st_mtime_ns for path in (UI_JS, UI_CSS) if path.exists()), default=0)


def metric_rows():
    rows = []
    for row in read_csv("metricas.csv"):
        rows.append({"method": row["metodo"],
                     **{key: int(row[key]) for key in ("TP", "FP", "TN", "FN")},
                     **{key: float(row[key]) if row[key] else None
                        for key in ("precision", "recall", "F1")}})
    return rows


def attempt(row, simulated=False):
    item = {"id": f"{'sim' if simulated else 'manual'}-{row['id']}",
            "time": row["time"], "account": row["account"],
            "source": row["source"], "success": bool(row["success"]),
            "score": row["score"],
            "alert": None if row["alert"] is None else bool(row["alert"])}
    if simulated:
        item["origins_account"] = row["origins_account"]
        item["related_origins"] = row["related_origins"]
    return item


@app.route("/", methods=["GET", "POST"])
def login():
    message = None
    if request.method == "POST":
        account = request.form.get("username", "").strip()[:80]
        password = request.form.get("password", "")
        with connect() as db:
            user = db.execute("SELECT password_hash FROM users WHERE username=?",
                              (account,)).fetchone()
            try:
                success = bool(user and hasher.verify(user["password_hash"], password))
            except (VerifyMismatchError, VerificationError):
                success = False
            now = datetime.now().astimezone().isoformat(timespec="microseconds")
            event = {"run_id": "manual", "time": now,
                     "account": account, "source": "localhost", "success": success}
            previous = [dict(row) | {"run_id": "manual"} for row in db.execute(
                "SELECT time, account, source, success FROM manual_attempts ORDER BY time")]
            feature_row = features_for_event(event, previous)
            score = alert = None
            if MODEL.exists():
                with MODEL.open("rb") as file:
                    saved = pickle.load(file)  # local artifact produced by demo.py
                score = float(anomaly_scores(saved["model"], [feature_row])[0])
                alert = int(score > saved["threshold"])
            db.execute("INSERT INTO manual_attempts "
                       "(time, account, source, success, score, alert) VALUES (?,?,?,?,?,?)",
                       (now, account, "localhost", int(success), score, alert))
        message = "Acceso concedido" if success else "Acceso rechazado"
    return render_template("login.html", version=ui_version(),
                           bootstrap={"page": "login", "message": message})


@app.route("/resultados")
def results():
    with connect() as db:
        manual = db.execute("SELECT id, time, account, source, success, score, alert "
                            "FROM manual_attempts ORDER BY id DESC").fetchall()
        simulated = db.execute("SELECT id, time, account, source, success, score, alert, "
                               "origins_account, related_origins FROM simulated_attempts "
                               "ORDER BY id DESC").fetchall()
    metrics = metric_rows()
    forest = next((row for row in metrics if row["method"] == "isolation_forest"), None)
    summary = ({"evaluated": sum(forest[key] for key in ("TP", "FP", "TN", "FN")),
                "alerts": forest["TP"] + forest["FP"], "false_alerts": forest["FP"]}
               if forest else None)
    threshold = None
    if MODEL.exists():
        with MODEL.open("rb") as file:
            threshold = pickle.load(file)["threshold"]
    return render_template("resultados.html", version=ui_version(),
                           bootstrap={"page": "monitor", "manual": [attempt(row) for row in manual],
                                      "simulated": [attempt(row, True) for row in simulated],
                                      "metrics": metrics, "summary": summary,
                                      "threshold": threshold,
                                      "has_image": (RESULTS / "matriz_confusion.png").exists()})


@app.route("/matriz_confusion.png")
def confusion_image():
    from flask import send_from_directory
    return send_from_directory(RESULTS, "matriz_confusion.png")


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
