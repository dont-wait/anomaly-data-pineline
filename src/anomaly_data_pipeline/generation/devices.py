"""Observable client devices, generated without reading anomaly labels/scenarios."""
import random
from collections import defaultdict
from .ids import stable_id


class DeviceHistory:
    def __init__(self,seed,options):
        self.seed=seed;self.options=options
        self.rng=random.Random(f"{seed}:client-devices-v1")
        self.known=defaultdict(list);self.counter=0
        probability=options['new_device_probability'];limit=options['max_known_devices']
        if type(probability) not in (int,float) or not 0<=probability<=1:
            raise ValueError('new_device_probability must be in [0,1]')
        if type(limit) is not int or limit<1:raise ValueError('max_known_devices must be positive')
        platforms=options['mobile_platforms'];weights=options['mobile_platform_weights']
        if not platforms or len(set(platforms))!=len(platforms) or set(platforms)-{'android','ios'} or len(weights)!=len(platforms) or any(type(w) not in (int,float) or w<0 for w in weights) or sum(weights)<=0:
            raise ValueError('Invalid mobile platform distribution')

    def next(self,account,channel):
        if channel=='mobile':platform=self.rng.choices(self.options['mobile_platforms'],self.options['mobile_platform_weights'])[0]
        elif channel in ('web','desktop'):platform=channel
        else:raise ValueError('Unsupported channel')
        pool=self.known[(account,platform)]
        if pool and self.rng.random()>=self.options['new_device_probability']:
            identity=self.rng.choice(pool)
        else:
            identity=stable_id(self.seed,'client-device',f'{account}:{platform}:{self.counter}')
            self.counter+=1;pool.append(identity)
            del pool[:-self.options['max_known_devices']]
        return {'device_id':identity,'platform':platform}
