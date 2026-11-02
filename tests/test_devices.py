import copy,json,tempfile,unittest
from pathlib import Path
from anomaly_data_pipeline.generation.devices import DeviceHistory
from anomaly_data_pipeline.generation.pipeline import generate
from anomaly_data_pipeline.config import GenerationConfig,load_pipeline_config
ROOT=Path(__file__).resolve().parents[1]

class DeviceContextTests(unittest.TestCase):
    def options(self):return dict(new_device_probability=0.,max_known_devices=3,mobile_platforms=['android'],mobile_platform_weights=[1])

    def test_repeat_new_identity_scope_and_reproducibility(self):
        first=DeviceHistory(42,self.options());second=DeviceHistory(42,self.options())
        sequence=[('A','mobile'),('A','mobile'),('B','mobile'),('A','web'),('A','desktop')]
        rows=[first.next(*args) for args in sequence]
        self.assertEqual(rows,[second.next(*args) for args in sequence])
        self.assertEqual(rows[0]['device_id'],rows[1]['device_id'])
        self.assertNotEqual(rows[0]['device_id'],rows[2]['device_id'])
        self.assertEqual([r['platform'] for r in rows],['android','android','android','web','desktop'])
        options=self.options();options['new_device_probability']=1
        changed=DeviceHistory(42,options)
        self.assertEqual(len({changed.next('A','mobile')['device_id'] for _ in range(10)}),10)

    def test_device_changes_do_not_change_transaction_labels_or_amounts(self):
        pipeline=load_pipeline_config(ROOT/'configs/pipeline.toml');disabled=copy.deepcopy(pipeline)
        for stage in disabled['stages']:
            if stage['name']=='transactions':stage['options']['device']['enabled']=False
        config=GenerationConfig(seed=42,customers=12,transactions_per_customer=100,days=181,anomaly_rate=.2)
        read=lambda p,n:[json.loads(line) for line in (p/(n+'.jsonl')).read_text().splitlines()]
        with tempfile.TemporaryDirectory() as temp:
            enabled,without=Path(temp)/'enabled',Path(temp)/'without'
            generate(config,enabled,pipeline);generate(config,without,disabled)
            self.assertEqual(read(enabled,'labels'),read(without,'labels'))
            a,b=read(enabled,'transactions'),read(without,'transactions')
            for x,y in zip(a,b):
                self.assertIsNotNone(x.pop('device'));y.pop('device');self.assertEqual(x,y)
            events=read(enabled,'events');snapshots={tx['transaction_id']:tx['device'] for tx in read(enabled,'transactions')}
            for e in events:
                if e['event_type'] in ('TransferCreated','TransactionRequested'):
                    self.assertEqual(e['payload']['device_id'],snapshots[e['aggregate_id']]['device_id'])
                    self.assertEqual(e['payload']['platform'],snapshots[e['aggregate_id']]['platform'])
                elif e['aggregate_type']=='transaction':self.assertNotIn('device_id',e['payload'])

if __name__=='__main__':unittest.main()
