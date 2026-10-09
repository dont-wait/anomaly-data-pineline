"""Plan observable request sequences. Scenario names stay in label sidecars."""
from __future__ import annotations
from datetime import datetime, timedelta
from .behavior import channel, ordinary_time, anomaly_time


def schedule(context, profiles, options):
    rng, cfg = context.rng, context.config
    rows = []
    remaining = [p['count'] for p in profiles]
    positives = 0
    def add(index, at, scenario='normal', **overrides):
        nonlocal positives
        if remaining[index] <= 0:
            return False
        remaining[index] -= 1
        positives += scenario != 'normal'
        rows.append(dict(index=index, occurred=at, scenario=scenario, **overrides))
        return True
    # Recurring salary is a real CASH_IN request/result pair inside total budget.
    for p in profiles:
        month = context.start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = context.start + timedelta(days=cfg.days)
        while month < end:
            at = month.replace(day=p['payday'], hour=rng.choice(p['preferred_hours']))
            if context.start <= at < end:
                add(p['index'], at, tx_type='CASH_IN', income=True, amount=p['monthly_income'])
            month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    # Graph fan-in + forwarding: initial donors supply observable prior edges.
    target = round(sum(p['count'] for p in profiles) * cfg.anomaly_rate)
    graph_target = round(target * options['scenario_weights'][2]) if len(profiles) >= options['fan_in_sources'] + 1 else 0
    created = 0
    while created < graph_target:
        candidates = [p['index'] for p in profiles if remaining[p['index']] > 2]
        if len(candidates) < options['fan_in_sources'] + 1:
            break
        actors = rng.sample(candidates, options['fan_in_sources'] + 1)
        hub, donors = actors[0], actors[1:]
        at = anomaly_time(context, profiles[hub], options)
        for n, donor in enumerate(donors):
            anomalous = n >= options['fan_in_warmup_sources']
            add(donor, at + timedelta(seconds=n * options['graph_gap_seconds']),
                scenario='graph_fan_in' if anomalous else 'normal', tx_type='TRANSFER', receiver=hub,
                amount=round(profiles[donor]['typical_amount'] * rng.uniform(*options['normal_multipliers'])))
            created += anomalous
        next_receiver = rng.choice([i for i in candidates if i != hub])
        add(hub, at + timedelta(seconds=len(donors) * options['graph_gap_seconds']),
            scenario='rapid_forwarding', tx_type='TRANSFER', receiver=next_receiver,
            amount=round(sum(profiles[i]['typical_amount'] for i in donors) * options['forward_fraction']))
        created += 1
    # A burst's positives follow two already observable requests. No future-edge labels.
    burst_target = round(target * options['scenario_weights'][1])
    created = 0
    while created < burst_target:
        candidates = [p for p in profiles if remaining[p['index']] >= options['burst_size']]
        if not candidates:
            break
        p = rng.choice(candidates); at = anomaly_time(context, p, options)
        for n in range(options['burst_size']):
            anomalous = n >= options['burst_warmup_requests']
            add(p['index'], at + timedelta(seconds=n * options['burst_gap_seconds']),
                scenario='velocity_burst' if anomalous else 'normal', burst=True,
                forced_channel=channel(context, p, options, unusual=True))
            created += anomalous
    # Contextual amount outliers combine amount, probabilistic time deviation, unusual channel and unfamiliar recipient.
    context_target = max(0, target - positives)
    for _ in range(context_target):
        candidates = [p for p in profiles if remaining[p['index']] > 0]
        if not candidates:
            break
        p = rng.choice(candidates)
        add(p['index'], anomaly_time(context, p, options), scenario='contextual_amount',
            forced_channel=channel(context, p, options, unusual=True))
    for p in profiles:
        while remaining[p['index']]:
            add(p['index'], ordinary_time(context, p, options))
    rows.sort(key=lambda r: (r['occurred'], r['index']))
    previous = None
    end = datetime.combine((context.start.date() + timedelta(days=cfg.days)), datetime.min.time(), tzinfo=context.start.tzinfo)
    for n, row in enumerate(rows):
        if previous is not None and row['occurred'] <= previous:
            row['occurred'] = previous + timedelta(microseconds=1)
        if row['occurred'] >= end:
            raise ValueError('Scenario exceeds simulation period; increase days or reduce scenario duration')
        row['transaction_index'] = n
        previous = row['occurred']
    return rows
