#!/usr/bin/env python3
"""Slurm-only endgame runtime audit: schema on/off and silent fallback counters.

Every worker loads a fresh candidate module for each mode. jsonschema.validate
is restored in finally, and each process handles only one paired diagnostic.
The frozen policies are never changed. Results do not estimate ladder strength.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import contextlib
import hashlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import time
import traceback


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def error_counters(fn):
    values = dict(getattr(fn, 'telemetry', {}))
    chassis = getattr(fn.__globals__.get('_IMPL'), 'chassis', None)
    if chassis is not None:
        values.update({'chassis_' + k: v for k, v in chassis.diagnostics.items()})
    for name, value in fn.__globals__.items():
        if isinstance(value, dict) and ('REPORT' in name or 'STATS' in name):
            for key, count in value.items():
                if isinstance(count, (int, float)) and any(tag in key.lower() for tag in ('error', 'fallback', 'shortfall', 'failed', 'unresolved')):
                    values[name + '.' + key] = count
    return {str(k): v for k, v in values.items() if isinstance(v, (int, float)) and
            any(tag in str(k).lower() for tag in ('error', 'fallback', 'shortfall', 'failed', 'unresolved'))}


def one_episode(candidate, opponent, seed, seat, fast, monitor_layers=()):
    # Import warnings about unrelated optional Kaggle games are not relevant.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
        import jsonschema
        from tournament import _digest, _fast_env
    original_validate = jsonschema.validate
    schema_calls = [0]
    schema_errors = [0]

    def checked_validate(*args, **kwargs):
        schema_calls[0] += 1
        try:
            return original_validate(*args, **kwargs)
        except Exception:
            schema_errors[0] += 1
            raise

    if fast:
        _fast_env()
    else:
        jsonschema.validate = checked_validate
    policy = get_last_callable(Path(candidate).read_text(), path=str(Path(candidate).resolve()))
    # Public exports may bind `agent` to a semantically named function. Identity
    # checks the framework-selected callable without rejecting valid aliases.
    if policy is not policy.__globals__.get('agent'):
        raise RuntimeError(f'Framework did not select the exported agent: {policy.__name__}')
    caught_layer_exceptions = []
    for symbol in monitor_layers:
        original_layer = policy.__globals__[symbol]

        def monitored_layer(*args, _original=original_layer, _symbol=symbol, **kwargs):
            try:
                return _original(*args, **kwargs)
            except Exception as exc:
                observation = args[0] if args else {}
                caught_layer_exceptions.append({
                    'symbol': _symbol, 'step': int(observation.get('step', -1)),
                    'type': type(exc).__name__, 'message': str(exc),
                    'frames': [{'name': f.name, 'line': f.lineno, 'file': f.filename}
                               for f in traceback.extract_tb(exc.__traceback__)[-8:]]})
                # Preserve the exact exception and let the original parent run
                # its own fallback. This diagnostic never supplies an action.
                raise

        policy.__globals__[symbol] = monitored_layer
    timings = []
    counter_events = []
    prior = error_counters(policy)
    whole_pass_steps = []
    action_hasher = hashlib.sha256()

    def observed_policy(observation, configuration):
        nonlocal prior
        started = time.perf_counter()
        action = policy(observation, configuration)
        elapsed = time.perf_counter() - started
        action_hasher.update(json.dumps(action, sort_keys=True, separators=(',', ':')).encode())
        action_hasher.update(b'\n')
        step = int(observation.get('step', -1))
        timings.append((elapsed, step))
        current = error_counters(policy)
        increased = {key: value - prior.get(key, 0) for key, value in current.items()
                     if value > prior.get(key, 0)}
        if increased:
            counter_events.append({'step': step, 'increased': increased})
        prior = current
        if isinstance(action, dict) and not action.get('market'):
            commands = [action.get('farmer', ['PASS']), *(action.get('hands') or [])]
            if all(command == ['PASS'] for command in commands):
                whole_pass_steps.append(step)
        return action

    started = time.perf_counter()
    try:
        env = make('kaggriculture', configuration={'episodeSteps': 720, 'seed': seed})
        pair = [opponent, opponent]
        pair[seat] = observed_policy
        env.run(pair)
        final = env.steps[-1]
        raw_reports = {key: json_safe(value) for key, value in policy.__globals__.items()
                       if isinstance(value, dict) and ('REPORT' in key or 'STATS' in key)}
        chassis = getattr(policy.__globals__.get('_IMPL'), 'chassis', None)
        result = {'seed': seed, 'seat': seat, 'opponent': opponent, 'fast_env': fast,
                  'candidate_sha256': sha(candidate), 'opponent_sha256': sha(opponent),
                  'callable_name': policy.__name__,
                  'action_sha256': action_hasher.hexdigest(),
                  'caught_layer_exceptions': caught_layer_exceptions,
                  'money': [float(s.reward or 0) for s in final],
                  'status': [str(s.status) for s in final],
                  'digest': [_digest(env, p) for p in (0, 1)],
                  'schema_calls': schema_calls[0], 'schema_errors': schema_errors[0],
                  'telemetry': json_safe(getattr(policy, 'telemetry', {})),
                  'raw_reports': raw_reports,
                  'chassis_diagnostics': json_safe(chassis.diagnostics if chassis else {}),
                  'error_counters': error_counters(policy), 'counter_events': counter_events,
                  'whole_pass_steps': whole_pass_steps,
                  'worst_turn_seconds': max((x[0] for x in timings), default=0),
                  'slowest_turns': [{'step': step, 'seconds': elapsed}
                                    for elapsed, step in sorted(timings, reverse=True)[:8]],
                  'callback_count': len(timings), 'wall_seconds': time.perf_counter() - started}
        return result
    finally:
        jsonschema.validate = original_validate


def paired_job(job):
    candidate, opponent, seed, seat = job
    normal = one_episode(candidate, opponent, seed, seat, False)
    fast = one_episode(candidate, opponent, seed, seat, True)
    comparison = {key: normal[key] == fast[key] for key in ('status', 'money', 'digest')}
    return {'normal': normal, 'fast': fast, 'same': comparison,
            'schema_gate': normal['schema_calls'] > 0 and normal['schema_errors'] == 0 and fast['schema_calls'] == 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', default='data/endgame-20260929-screen/agents/public_rank.py')
    p.add_argument('--opponent', action='append')
    p.add_argument('--seed0', type=int, default=814000)
    p.add_argument('--seeds', type=int, default=4)
    p.add_argument('-j', '--jobs', type=int, default=24)
    p.add_argument('--output', default='data/endgame-20260929-diagnostics/result.json')
    args = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise SystemExit('Run this diagnostic through Slurm; it executes full episodes.')
    opponents = args.opponent or [
        'data/endgame-20260929-screen/agents/state_router.py',
        'data/endgame-20260929-screen/agents/n04.py',
        'data/endgame-public/shop-router-0913/output/main.py']
    source_hashes = {path: sha(path) for path in [args.candidate, *opponents]}
    jobs = [(args.candidate, opponent, seed, seat) for opponent in opponents
            for seed in range(args.seed0, args.seed0 + args.seeds) for seat in (0, 1)]
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise SystemExit(f'Refusing to overwrite {target}')
    rows = []
    print(f'job={os.environ["SLURM_JOB_ID"]} pairs={len(jobs)} episodes={2*len(jobs)} seeds={args.seed0}..{args.seed0+args.seeds-1}', flush=True)
    with ProcessPoolExecutor(max_workers=args.jobs, mp_context=multiprocessing.get_context('spawn'),
                             max_tasks_per_child=1) as pool, target.with_suffix('.jsonl').open('w') as log:
        for future in as_completed([pool.submit(paired_job, job) for job in jobs]):
            row = future.result()
            rows.append(row)
            log.write(json.dumps(row, separators=(',', ':')) + '\n')
            log.flush()
            normal = row['normal']
            nonzero = {k: v for k, v in normal['error_counters'].items() if v}
            print(f'{len(rows)}/{len(jobs)} {Path(normal["opponent"]).stem} seed={normal["seed"]} seat={normal["seat"]} same={all(row["same"].values())} schema={row["schema_gate"]} worst={normal["worst_turn_seconds"]:.4f}s nonzero={nonzero}', flush=True)
    for path, expected in source_hashes.items():
        if sha(path) != expected:
            raise RuntimeError(f'Strategy artifact changed during diagnostic: {path}')
    summary = {'job_id': os.environ['SLURM_JOB_ID'], 'source_hashes': source_hashes,
               'pairs': len(rows), 'episodes': len(rows) * 2,
               'all_status_done': all(x[mode]['status'] == ['DONE', 'DONE'] for x in rows for mode in ('normal', 'fast')),
               'all_modes_identical': all(all(x['same'].values()) for x in rows),
               'all_schema_gates_pass': all(x['schema_gate'] for x in rows),
               'worst_turn_seconds': max(x[mode]['worst_turn_seconds'] for x in rows for mode in ('normal', 'fast')),
               'schema_on_nonzero_events': sum(bool(x['normal']['counter_events']) for x in rows),
               'rows': rows}
    target.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'rows'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
