import subprocess
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TMP = ROOT / 'tmp'


def test_e2e_script_runs_and_generates():
    # run the e2e script (it will start the server, run checks, and stop it)
    p = subprocess.run([str(ROOT / 'scripts' / 'e2e_run.sh')], cwd=str(ROOT), capture_output=True, text=True)
    print(p.stdout)
    print(p.stderr)
    assert p.returncode == 0, f"e2e script failed: {p.returncode}\nstdout:{p.stdout}\nstderr:{p.stderr}"

    gen = TMP / 'generate.json'
    assert gen.exists(), 'generate.json missing from tmp/'
    data = json.loads(gen.read_text(encoding='utf-8'))
    assert 'posts' in data and len(data['posts']) > 0
    for post in data['posts']:
        reel = post.get('reel')
        assert reel is not None
        for key in ('ranked_hooks','beats','shot_list','srt','thumbnail_prompt'):
            assert key in reel
