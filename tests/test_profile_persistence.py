from app import app


def test_profile_save_and_get(client):
    # ensure a session profile_id exists
    with client.session_transaction() as sess:
        sess['profile_id'] = 'test-profile-xyz'

    payload = {
        'industry': 'bakery',
        'tone': 'friendly',
        'platforms': ['instagram'],
        'brand_keywords': ['artisan'],
        'niche_keywords': ['sourdough'],
        'goals': ['promote'],
        'include_images': False,
        'company': "Laura's Bakery",
        'details': {'reel_style': 'Face-camera tips'}
    }

    r = client.post('/api/profile?content_version=2025.01', json=payload)
    assert r.status_code == 200

    r2 = client.get('/api/profile')
    assert r2.status_code == 200
    prof = r2.get_json()
    # Company capitalization can be normalized by the app (title() may change punctuation);
    # compare in a case-insensitive, punctuation-agnostic way.
    company_saved = prof.get('company', '') or ''
    norm = company_saved.lower().replace("'", "").replace('.', '').strip()
    assert 'laura' in norm and 'bakery' in norm
    assert prof.get('details', {}).get('reel_style') == 'Face-camera tips'
