import os
import pathlib
import importlib

# Load .env.dev (if present) into environment for the test run
here = pathlib.Path(__file__).parent.parent
env_dev = here / '.env.dev'
if env_dev.exists():
    with env_dev.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

# now import the module under test
import generator


def test_make_reel_plan_structure():
    plan = generator.make_reel_plan(
        industry='Realtor',
        pillar_name='Story',
        brand_keywords=['listings'],
        tone='friendly',
        company='TestCo',
        reel_style='Property b-roll + captions',
        goals=['New listings'],
        niche_keywords=['condo'],
        length_seconds=30,
        production_tier='solo'
    )

    # basic shape assertions
    assert isinstance(plan, dict)
    for k in ('ranked_hooks', 'hook', 'beats', 'shot_list', 'srt', 'thumbnail_prompt'):
        assert k in plan, f"Missing key {k} in plan"

    # beats should be a non-empty list and have start/end keys
    beats = plan['beats']
    assert len(beats) >= 1
    for b in beats:
        assert 'start_s' in b and 'end_s' in b and 'line' in b
        assert b['end_s'] >= b['start_s']

    # SRT should contain the first beat line
    srt = plan['srt']
    assert isinstance(srt, str)
    assert beats[0]['line'] in srt


if __name__ == '__main__':
    # allow running directly
    test_make_reel_plan_structure()
    print('generator.make_reel_plan smoke test passed')
