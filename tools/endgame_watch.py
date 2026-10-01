#!/usr/bin/env python3
"""Read-only ladder snapshots. Run repeated observations inside a Slurm job."""

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def eligible_public(episode, submission):
    return (episode['state'] == 'COMPLETED'
            and episode['type'] == 'EPISODE_TYPE_PUBLIC'
            and len(episode['agents']) == 2
            and sum(a['submission'] == submission for a in episode['agents']) == 1
            and len({a['seat'] for a in episode['agents']}) == 2)


def outcome_counts(episodes, submission):
    counts = dict(wins=0, ties=0, losses=0, errors=0, opponent_errors=0,
                  unreported_agent_states=0, missing_reward=0, nonfinite_reward=0,
                  completed=0)
    for episode in episodes:
        if not eligible_public(episode, submission):
            continue
        ours = [a for a in episode['agents'] if a['submission'] == submission]
        us = ours[0]
        them = next(a for a in episode['agents'] if a['seat'] != us['seat'])
        counts['completed'] += 1
        us_error = us['state'].startswith('EPISODE_AGENT_STATE_ERROR_')
        them_error = them['state'].startswith('EPISODE_AGENT_STATE_ERROR_')
        counts['errors'] += us_error
        counts['opponent_errors'] += them_error
        counts['unreported_agent_states'] += any(a['state'] in (
            'EPISODE_AGENT_STATE_UNSPECIFIED', 'EPISODE_AGENT_STATE_PENDING')
            for a in (us, them))
        if us_error or them_error:
            continue
        if us['reward'] is None or them['reward'] is None:
            counts['missing_reward'] += 1
            continue
        if not all(math.isfinite(a['reward']) for a in (us, them)):
            counts['nonfinite_reward'] += 1
            continue
        key = 'wins' if us['reward'] > them['reward'] else 'losses' if us['reward'] < them['reward'] else 'ties'
        counts[key] += 1
    return counts


def enum_name(value):
    return getattr(value, 'name', str(value).rsplit('.', 1)[-1])


def snapshot(submission):
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    subs = api.competition_submissions('kaggriculture')
    episodes_by_id = {}
    for e in api.competition_list_episodes(submission):
        episode = dict(id=e.id, created=str(e.create_time), ended=str(e.end_time),
            state=enum_name(e.state), type=enum_name(e.type),
            # The SDK reward property turns missing rewards into 0.0.
            agents=[dict(submission=a.submission_id, seat=a.index,
                         reward=a.to_dict(ignore_defaults=False)['reward'],
                         state=enum_name(a.state)) for a in e.agents])
        if e.id in episodes_by_id and episodes_by_id[e.id] != episode:
            raise ValueError(f'Conflicting duplicate episode {e.id}')
        episodes_by_id[e.id] = episode
    episodes = sorted(episodes_by_id.values(), key=lambda e: (e['ended'], e['id']), reverse=True)
    ranking = [e for e in episodes if eligible_public(e, submission)]
    return dict(fetched_utc=utc_now(), submission_id=submission,
        latest_submissions=[dict(id=int(s.ref), status=enum_name(s.status), date=str(s.date),
                                 score=s.public_score, error=s.error_description) for s in subs[:3]],
        listed_ranking=outcome_counts(episodes, submission),
        recent_18=outcome_counts(ranking[:18], submission), episodes=episodes,
        note='API-listed public episodes only, ordered by end time. W/T/L compares finite reported rewards without reported agent errors; it excludes known errors and missing rewards. Missing agent states require replay inspection. Recent loss fraction alone does not prove convergence.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submission', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=1)
    parser.add_argument('--interval', type=int, default=600)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if args.once:
        result = snapshot(args.submission)
        args.output.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        text = json.dumps(result, indent=2) + '\n'
        (args.output / (stamp + '.json')).write_text(text)
        temporary = args.output / 'latest.json.partial'
        temporary.write_text(text)
        temporary.replace(args.output / 'latest.json')
        print(json.dumps({k: v for k, v in result.items() if k != 'episodes'}), flush=True)
        return
    if args.samples < 1 or args.interval < 60:
        parser.error('Use positive samples and intervals of at least 60 seconds')
    if args.samples > 1 and not os.environ.get('SLURM_JOB_ID'):
        parser.error('Repeated observations must run in a Slurm job')
    command = [sys.executable, str(Path(__file__).resolve()), '--once', '--submission',
               str(args.submission), '--output', str(args.output)]
    for index in range(args.samples):
        started = time.monotonic()
        try:
            result = subprocess.run(command, timeout=180, check=False)
            if result.returncode:
                print(json.dumps(dict(time=utc_now(), snapshot_exit=result.returncode)), flush=True)
        except subprocess.TimeoutExpired:
            print(json.dumps(dict(time=utc_now(), error='snapshot timed out')), flush=True)
        if index + 1 < args.samples:
            time.sleep(max(1, args.interval - (time.monotonic() - started)))


if __name__ == '__main__':
    main()
