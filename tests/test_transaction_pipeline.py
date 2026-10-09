import copy
import json
import tempfile
import unittest
from collections import Counter, defaultdict, deque
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


    def test_contextual_scenarios_have_prior_observable_witnesses(self):
        config = GenerationConfig(customers=40, transactions_per_customer=300, days=181, seed=42)
        pipeline = load_pipeline_config(ROOT / 'configs/pipeline.toml')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generate(config, root, pipeline)
            profiles = {p['account_id']: p for p in read(root, 'behavior_profiles')}
            labels = {p['transaction_id']: p for p in read(root, 'labels')}
            recent = defaultdict(deque)
            incoming = defaultdict(deque)
            counts = Counter()
            seen_scenarios = Counter()
            contextual_hours = Counter()
            anomaly_hours = Counter()
            for tx in read(root, 'transactions'):
                at = datetime.fromisoformat(tx['created_at']).timestamp()
                src, dst = tx['source']['account_id'], tx['destination']['account_id']
                while recent[src] and recent[src][0] < at - 120:
                    recent[src].popleft()
                for aid in (src, dst):
                    while incoming[aid] and incoming[aid][0][0] < at - 600:
                        incoming[aid].popleft()
                scenario = labels[tx['transaction_id']]['scenario_id']
                seen_scenarios[scenario] += 1
                if labels[tx['transaction_id']]['is_anomaly']:
                    anomaly_hours[datetime.fromisoformat(tx['created_at']).hour] += 1
                if scenario == 'contextual_amount':
                    p = profiles[src]
                    contextual_hours[datetime.fromisoformat(tx['created_at']).hour in p['preferred_hours']] += 1
                    self.assertNotEqual(tx['channel'], p['preferred_channel'])
                if scenario == 'velocity_burst':
                    self.assertGreaterEqual(len(recent[src]), 2)
                if scenario == 'graph_fan_in':
                    self.assertGreaterEqual(len({s for _, s in incoming[dst]}), 3)
                if scenario == 'rapid_forwarding':
                    self.assertGreaterEqual(len({s for _, s in incoming[src]}), 3)
                recent[src].append(at)
                if tx['type'] == 'TRANSFER':
                    incoming[dst].append((at, src))
                counts[src] += 1
            self.assertGreater(contextual_hours[True], 0)
            self.assertGreater(contextual_hours[False], 0)
            for hour in (14, 15, 16):
                self.assertGreater(anomaly_hours[hour], 0)
            self.assertEqual(sum(counts.values()), 12000)
            self.assertGreater(len(set(counts.values())), 1)
            self.assertTrue({'contextual_amount', 'velocity_burst', 'graph_fan_in', 'rapid_forwarding'} <= set(seen_scenarios))
            self.assertAlmostEqual(sum(l['is_anomaly'] for l in labels.values()) / 12000, .02, delta=.002)

    def test_single_account_transfer_fails_explicitly(self):
        pipeline = load_pipeline_config(ROOT / "configs/pipeline.toml")
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "at least two accounts"):
                generate(GenerationConfig(customers=1), Path(temp), pipeline)


if __name__ == "__main__":
    unittest.main()
