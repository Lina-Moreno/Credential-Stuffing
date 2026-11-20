import csv
import ipaddress
import json
import re
import tempfile
import unittest
from pathlib import Path

import app
from detector import extract, features_for_event


def event(minute, source, account, success=False, run="r"):
    return {"run_id": run, "time": f"2026-01-01T00:{minute:02d}:00+00:00",
            "source": source, "account": account, "success": success}


class FeatureTests(unittest.TestCase):
    def test_overlap_counts_unique_other_origins(self):
        history = [event(0, "A", "1"), event(1, "A", "2"),
                   event(2, "B", "2"), event(3, "B", "2"),
                   event(4, "C", "3")]
        self.assertEqual(features_for_event(event(5, "A", "1"), history)[4], 1)

    def test_future_and_other_runs_are_excluded(self):
        history = [event(1, "A", "1"), event(4, "B", "1", run="other"),
                   event(6, "C", "1")]
        self.assertEqual(features_for_event(event(5, "A", "1"), history),
                         (1, 1, 1, 1.0, 0))

    def test_current_result_is_not_used(self):
        events = [event(0, "A", "1", False), event(1, "A", "1", True)]
        first, second = extract(events)
        self.assertEqual(first, (0, 0, 0, 0.0, 0))
        self.assertEqual(second[3], 1.0)


class SyntheticIPTests(unittest.TestCase):
    def test_sources_are_stable_fictional_ipv4_addresses(self):
        from demo import DISTRIBUTED_IPS, LEGITIMATE_IPS, SHARED_IP, generate_run

        events = generate_run(310, attacks=True)
        self.assertEqual(events, generate_run(310, attacks=True))
        normal = {e["source"] for e in events if not e["truth"]}
        suspicious = {e["source"] for e in events if e["truth"]}
        self.assertTrue(normal <= set(LEGITIMATE_IPS) | {SHARED_IP})
        self.assertEqual(suspicious, set(DISTRIBUTED_IPS))
        self.assertFalse(normal & suspicious)
        self.assertTrue(all(ipaddress.ip_address(e["source"]).version == 4 for e in events))


class LoginTests(unittest.TestCase):
    def test_valid_invalid_and_no_password_in_attempts(self):
        original_db = app.DB
        original_model = app.MODEL
        with tempfile.TemporaryDirectory() as directory:
            app.DB = Path(directory) / "test.sqlite3"
            app.MODEL = Path(directory) / "missing.pkl"
            try:
                app.init_db()
                secret = "test-secret-123"
                with app.connect() as db:
                    db.execute("INSERT INTO users VALUES (?,?)",
                               ("usuario_01", app.hasher.hash(secret)))
                client = app.app.test_client()
                self.assertIn(b"Acceso concedido", client.post("/", data={
                    "username": "usuario_01", "password": secret}).data)
                self.assertIn(b"Acceso rechazado", client.post("/", data={
                    "username": "usuario_01", "password": "incorrecta"}).data)
                with app.connect() as db:
                    rows = db.execute("SELECT * FROM manual_attempts ORDER BY id").fetchall()
                    self.assertEqual([r["success"] for r in rows], [1, 0])
                    self.assertTrue(all(r["score"] is None for r in rows))
                    self.assertNotIn(secret, str([tuple(r) for r in rows]))
                    columns = [r[1] for r in db.execute("PRAGMA table_info(manual_attempts)")]
                    self.assertNotIn("password", columns)
            finally:
                app.DB = original_db
                app.MODEL = original_model

    def test_monitor_summary_and_safe_frontend_payload(self):
        original_db, original_results, original_model = app.DB, app.RESULTS, app.MODEL
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app.DB, app.RESULTS, app.MODEL = root / "test.sqlite3", root, root / "missing.pkl"
            try:
                app.init_db()
                (root / "metricas.csv").write_text(
                    "metodo,TP,FP,TN,FN,precision,recall,F1\n"
                    "isolation_forest,3,2,6,1,0.6,0.75,0.667\n", encoding="utf-8")
                secret = "test-secret-123"
                password_hash = app.hasher.hash(secret)
                with app.connect() as db:
                    db.execute("INSERT INTO users VALUES (?,?)", ("usuario_01", password_hash))
                    db.execute("""INSERT INTO simulated_attempts
                        (run_id, time, account, source, success, score, alert,
                         origins_account, related_origins, truth, baseline_alert)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        ("test", "2026-01-01T00:00:00+00:00", "usuario_01", "198.51.100.1",
                         1, 0.18, 1, 3, 4, 1, 0))
                client = app.app.test_client()
                client.post("/", data={"username": "usuario_01", "password": secret})
                client.post("/", data={"username": "usuario_01", "password": "incorrecta"})
                html = client.get("/resultados").data.decode()
                payload = re.search(r'<script type="application/json" id="app-data">(.*?)</script>', html)
                self.assertIsNotNone(payload)
                data = json.loads(payload.group(1))
                self.assertEqual(data["summary"], {"evaluated": 12, "alerts": 5, "false_alerts": 2})
                self.assertEqual([row["success"] for row in data["manual"]], [False, True])
                self.assertEqual(data["simulated"][0]["origins_account"], 3)
                self.assertIsNone(data["manual"][0]["alert"])
                self.assertNotIn(secret, html)
                self.assertNotIn(password_hash, html)
                self.assertNotIn("truth", payload.group(1))
            finally:
                app.DB, app.RESULTS, app.MODEL = original_db, original_results, original_model


if __name__ == "__main__":
    unittest.main()
