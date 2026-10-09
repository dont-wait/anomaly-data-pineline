import copy
import json
import tempfile
import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_OID, uuid5

from anomaly_data_pipeline.analysis import analyze
from anomaly_data_pipeline.config import GenerationConfig, load_pipeline_config
from anomaly_data_pipeline.generation.pipeline import generate

ROOT = Path(__file__).resolve().parents[1]


def read(root, name):
    return [json.loads(line) for line in (root / f"{name}.jsonl").read_text().splitlines()]


class TransactionPipelineTests(unittest.TestCase):
    def test_chronological_ledger_contract_labels_and_reproducibility(self):
        config = GenerationConfig(customers=12, transactions_per_customer=100, days=30,
                                  anomaly_rate=0.2, seed=42)
        pipeline = load_pipeline_config(ROOT / "configs/pipeline.toml")
        options = next(s["options"] for s in pipeline["stages"] if s["name"] == "transactions")
        options["fee"] = 1000
        with tempfile.TemporaryDirectory() as temp:
            root, repeat = Path(temp) / "first", Path(temp) / "second"
            generate(config, root, pipeline)
            generate(config, repeat, pipeline)
            for file in root.glob("*.jsonl"):
                self.assertEqual(file.read_bytes(), (repeat / file.name).read_bytes())
            txs, events, labels = read(root, "transactions"), read(root, "events"), read(root, "labels")
            self.assertEqual(len(txs), 1200)
            dates = [datetime.fromisoformat(t["created_at"]) for t in txs]
            self.assertEqual(dates, sorted(set(dates)))
            balances = {a["_id"]: a["balance"]["current"] for a in read(root, "accounts")}
            counterparties = {r["_id"] for r in read(root, "counterparties")}
            tx_events = [e for e in events if e["aggregate_type"] == "transaction"]
            self.assertEqual(len(tx_events), len(txs) * 2)
            lookup = {t["transaction_id"]: t for t in txs}
            requests = {}
            for e in tx_events:
                p = e["payload"]
                source, dest = p["sourceAccountId"], p["destinationAccountId"]
                tx = lookup[e["aggregate_id"]]
                self.assertNotIn("risk", tx)
                self.assertNotIn("risk", p)
                if e["sequence"] == 1:
                    requests[e["event_id"]] = e
                    self.assertNotIn("sourceBalanceAfter", p)
                    self.assertNotIn("destinationBalanceAfter", p)
                    self.assertNotIn("is_anomaly", p)
                    continue
                self.assertEqual(e["sequence"], 2)
                self.assertEqual(p["sourceBalanceBefore"], balances[source])
                if e["event_type"] in {"TransferCompleted", "TransferCancelled"}:
                    self.assertIn(dest, balances)
                    self.assertNotEqual(dest, source)
                    self.assertEqual(p["destinationBalanceBefore"], balances[dest])
                    if e["event_type"] == "TransferCompleted":
                        self.assertEqual(p["sourceBalanceAfter"], balances[source] - p["amount"] - p["fee"])
                        self.assertEqual(p["destinationBalanceAfter"], balances[dest] + p["amount"])
                    else:
                        self.assertEqual(p["sourceBalanceAfter"], balances[source])
                        self.assertEqual(p["destinationBalanceAfter"], balances[dest])
                    balances[dest] = p["destinationBalanceAfter"]
                else:
                    self.assertIn(dest, counterparties)
                    expected = balances[source]
                    if e["event_type"] == "TransactionPosted":
                        expected += p["amount"] if tx["type"] == "CASH_IN" else -p["amount"] - p["fee"]
                    self.assertEqual(p["sourceBalanceAfter"], expected)
                balances[source] = p["sourceBalanceAfter"]
                self.assertGreaterEqual(balances[source], 0)
                self.assertEqual(tx["posted_at"] is None, tx["status"] == "failed")
            self.assertEqual(len(labels), len(requests))
            for label in labels:
                self.assertIn(label["event_id"], requests)
                self.assertEqual(label["transaction_id"], requests[label["event_id"]]["aggregate_id"])
            native = read(root, "transfer_events")
            self.assertTrue(native)
            for e in native:
                self.assertEqual(set(e), {"eventId", "transactionId", "eventType", "schemaVersion", "sequence", "occurredAt", "payload"})
                self.assertEqual(e["eventId"], str(uuid5(NAMESPACE_OID, f"{e['transactionId']}:{e['eventType']}")))
                self.assertIn(e["payload"]["channel"], {"web", "mobile", "desktop"})
                self.assertGreater(e["payload"]["amount"], 0)
                self.assertEqual(e["schemaVersion"], 1)
            receivers = Counter(t["destination"]["account_id"] for t in txs)
            self.assertLess(len(receivers), len(txs))
            anomaly_ids = {l["transaction_id"] for l in labels if l["is_anomaly"]}
            normal = [t["amount"] for t in txs if t["transaction_id"] not in anomaly_ids]
            anomaly = [t["amount"] for t in txs if t["transaction_id"] in anomaly_ids]
            self.assertLess(min(anomaly), max(normal))
            analyze(root, Path(temp) / "reports")
            dashboard = json.loads((Path(temp) / "reports/dashboard.json").read_text())
            self.assertNotIn('Risk score', json.dumps(dashboard))

    def test_single_account_transfer_fails_explicitly(self):
        pipeline = load_pipeline_config(ROOT / "configs/pipeline.toml")
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "at least two accounts"):
                generate(GenerationConfig(customers=1), Path(temp), pipeline)


if __name__ == "__main__":
    unittest.main()
