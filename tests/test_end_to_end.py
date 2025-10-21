import json
from app import app


def test_save_and_generate_includes_company():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['profile_id'] = 'test-profile-1'

    profile = {
        'industry': 'bakery',
        'tone': 'friendly',
        'platforms': ['instagram'],
        'brand_keywords': ['artisan'],
        'niche_keywords': ['sourdough'],
        'goals': ['promote'],
        'include_images': False,
        'company': "Laura's Bakery"
    }

    # save profile
    r = client.post('/api/profile?content_version=2025.01', json=profile)
    assert r.status_code == 200
    # generate
    r2 = client.post('/api/generate', json={**profile, 'days': 1})
    assert r2.status_code == 200
    data = r2.get_json()
    assert data and 'posts' in data
    posts = data['posts']
    assert len(posts) == 1
    caption = posts[0]['caption']
    assert "Laura's Bakery" in caption or "From Laura's Bakery" in caption
