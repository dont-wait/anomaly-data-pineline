"""Customer activity, preferred counterparties and recurring income (no labels)."""
from __future__ import annotations
from datetime import datetime, timedelta
import math


def build_profiles(context, options):
    rng = context.rng
    size = len(context.accounts)
    total = size * context.config.transactions_per_customer
    weights = [max(options['activity_min'], min(options['activity_max'], rng.lognormvariate(0, options['activity_sigma']))) for _ in range(size)]
    weight_sum = sum(weights)
    counts = [int(total * w / weight_sum) for w in weights]
    for i in sorted(range(size), key=lambda i: total * weights[i] / weight_sum - counts[i], reverse=True)[:total - sum(counts)]:
        counts[i] += 1
    profiles = []
    for i, account in enumerate(context.accounts):
        peers = [j for j in range(size) if j != i]
        preferred = rng.sample(peers, min(options['preferred_receivers'], len(peers)))
        hours = rng.choice(options['hour_profiles'])
        income = context.customers[i]['profile']['demographics']['monthly_income']
        # Scale spending to activity and income instead of unrelated global amount.
        typical = max(options['typical_amount_floor'], int(income * options['spending_fraction'] / max(1, counts[i] / context.config.days * 30)))
        profile = dict(index=i, peer_ids=[context.accounts[j]['_id'] for j in peers], favorite_ids=[context.accounts[j]['_id'] for j in preferred], count=counts[i], typical_amount=typical, monthly_income=income,
                       preferred_receivers=preferred, preferred_hours=hours,
                       preferred_channel=rng.choices(options['channels'], options['channel_weights'])[0],
                       payday=rng.choice(options['paydays']), merchant=rng.randrange(options['merchant_count']),
                       cash=rng.randrange(options['cash_counterparty_count']))
        profiles.append(profile)
        context.write('behavior_profiles', {'account_id': account['_id'], 'monthly_income': income,
            'preferred_hours': hours, 'preferred_channel': profile['preferred_channel'], 'payday': profile['payday'],
            'typical_amount': typical, 'activity_weight': weights[i]})
    return profiles


def ordinary_time(context, profile, options):
    rng = context.rng
    day = rng.choices(context.simulation_days, weights=context.date_weights)[0]
    hours = profile['preferred_hours'] if rng.random() >= options['off_hours_probability'] else [h for h in range(24) if h not in profile['preferred_hours']]
    moment = datetime.combine(day[0], datetime.min.time(), tzinfo=context.start.tzinfo) + timedelta(hours=rng.choice(hours), seconds=rng.randrange(3600))
    return max(context.start, moment)


def unusual_time(context, profile):
    rng = context.rng
    day = rng.choices(context.simulation_days, weights=context.date_weights)[0]
    outside = [h for h in range(24) if h not in profile['preferred_hours']]
    hour = rng.choice(outside)
    return max(context.start, datetime.combine(day[0], datetime.min.time(), tzinfo=context.start.tzinfo) + timedelta(hours=hour, minutes=rng.randrange(40)))


def anomaly_time(context, profile, options):
    if context.rng.random() < options['anomaly_off_hours_probability']:
        return unusual_time(context, profile)
    # Keep sequence starts early enough in the hour for burst/graph followers.
    rng = context.rng
    day = rng.choices(context.simulation_days, weights=context.date_weights)[0]
    return max(context.start, datetime.combine(day[0], datetime.min.time(), tzinfo=context.start.tzinfo)
               + timedelta(hours=rng.choice(profile['preferred_hours']), minutes=rng.randrange(40)))


def channel(context, profile, options, unusual=False):
    if unusual or context.rng.random() > options['preferred_channel_probability']:
        return context.rng.choice([c for c in options['channels'] if c != profile['preferred_channel']])
    return profile['preferred_channel']


def validate_options(options):
    for key in ('repeat_receiver_probability', 'preferred_channel_probability', 'off_hours_probability', 'anomaly_off_hours_probability', 'normal_large_probability'):
        if not 0 <= options[key] <= 1:
            raise ValueError(f'{key} must be in [0,1]')
    if len(options['scenario_weights']) != 3 or any(v < 0 for v in options['scenario_weights']) or not math.isclose(sum(options['scenario_weights']), 1):
        raise ValueError('scenario_weights must contain three nonnegative weights summing to 1')
    for key in ('normal_multipliers', 'cash_in_multipliers', 'legitimate_large_multipliers', 'outlier_multipliers'):
        if len(options[key]) != 2 or not 0 < options[key][0] <= options[key][1]:
            raise ValueError(f'Invalid amount interval {key}')
    if not options['hour_profiles'] or any(not h or len(set(h)) >= 24 or any(type(v) is not int or not 0 <= v <= 23 for v in h) for h in options['hour_profiles']):
        raise ValueError('Hour profiles require normal hours and at least one off hour')
    if not options['paydays'] or any(type(d) is not int or not 1 <= d <= 28 for d in options['paydays']):
        raise ValueError('Paydays must be calendar-safe days 1..28')
    if len(options['channels']) < 2 or len(options['channel_weights']) != len(options['channels']) or any(v < 0 for v in options['channel_weights']) or sum(options['channel_weights']) <= 0:
        raise ValueError('Invalid channel vocabulary/weights')
    if not 0 < options['activity_min'] <= options['activity_max'] or options['activity_sigma'] < 0 or options['typical_amount_floor'] <= 0 or not 0 < options['spending_fraction'] <= 1:
        raise ValueError('Invalid activity/income scaling')
    for size, warmup in [('burst_size', 'burst_warmup_requests'), ('fan_in_sources', 'fan_in_warmup_sources')]:
        if not 1 <= options[warmup] < options[size]:
            raise ValueError(f'{warmup} must be positive and smaller than {size}')
    if options['burst_warmup_requests'] < 2 or options['fan_in_warmup_sources'] < 3 or options['burst_gap_seconds'] * options['burst_warmup_requests'] > 120 or options['graph_gap_seconds'] * options['fan_in_warmup_sources'] > 600:
        raise ValueError('Scenario warmup must fit the 120s/600s observable windows')
    if options['burst_gap_seconds'] <= 0 or options['graph_gap_seconds'] <= 0 or not 0 < options['forward_fraction'] <= 1:
        raise ValueError('Invalid scenario timing/forward fraction')
