import pytest
from generator import default_hashtags, make_reel_plan


def test_default_hashtags_basic():
    tags = default_hashtags('Bakery', ['sourdough', 'artisan'])
    assert isinstance(tags, list)
    assert any(t.lower().startswith('#bakery') for t in tags)
    assert any('#sourdough' in t.lower() for t in tags)


def test_make_reel_plan_structure():
    plan = make_reel_plan('bakery', 'Pillar', ['brand'], 'friendly', company='Co', reel_style='Face-camera tips', length_seconds=30)
    assert isinstance(plan, dict)
    assert plan.get('length_seconds') == 30
    assert 'beats' in plan and isinstance(plan['beats'], list) and len(plan['beats']) >= 1
    assert 'srt' in plan and isinstance(plan['srt'], str) and len(plan['srt']) > 0
    assert 'thumbnail_prompt' in plan
