"""Tests for review response generator API."""
import json


def test_review_response_requires_text(client):
    """Test that review response API requires review text."""
    r = client.post('/api/generate-review-response', json={})
    assert r.status_code == 400
    j = r.get_json()
    assert j['ok'] is False
    assert 'required' in j['error'].lower()


def test_review_response_empty_text(client):
    """Test that review response API rejects empty review text."""
    r = client.post('/api/generate-review-response', json={'review_text': ''})
    assert r.status_code == 400
    j = r.get_json()
    assert j['ok'] is False


def test_review_response_positive_review(client):
    """Test generating response for positive review."""
    review = "Great service! The team was very professional and helpful. Highly recommend!"
    r = client.post('/api/generate-review-response', json={
        'review_text': review,
        'tone': 'professional'
    })
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True
    assert 'response' in j
    assert len(j['response']) > 0
    # Should use template method unless OpenAI is configured
    assert 'method' in j


def test_review_response_negative_review(client):
    """Test generating response for negative review."""
    review = "Terrible experience. Very disappointed with the service. Never coming back."
    r = client.post('/api/generate-review-response', json={
        'review_text': review,
        'tone': 'apologetic'
    })
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True
    assert 'response' in j
    assert len(j['response']) > 0
    # Response should contain apology
    assert 'sorry' in j['response'].lower() or 'apolog' in j['response'].lower()


def test_review_response_neutral_review(client):
    """Test generating response for neutral review."""
    review = "Service was okay. Nothing special but got the job done."
    r = client.post('/api/generate-review-response', json={
        'review_text': review,
        'tone': 'professional'
    })
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True
    assert 'response' in j
    assert len(j['response']) > 0


def test_review_response_with_company_name(client):
    """Test generating response with company name."""
    review = "Great service from the team!"
    r = client.post('/api/generate-review-response', json={
        'review_text': review,
        'tone': 'grateful',
        'company_name': 'Acme Corp'
    })
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True
    assert 'response' in j
    # Company name should appear in template-based response
    if j.get('method') == 'template':
        assert 'Acme Corp' in j['response']


def test_review_response_different_tones(client):
    """Test that different tones produce different responses."""
    review = "Nice experience overall."
    
    tones = ['professional', 'grateful', 'apologetic', 'friendly']
    responses = []
    
    for tone in tones:
        r = client.post('/api/generate-review-response', json={
            'review_text': review,
            'tone': tone
        })
        assert r.status_code == 200
        j = r.get_json()
        assert j['ok'] is True
        responses.append(j['response'])
    
    # Responses should be different for different tones (at least some variation)
    unique_responses = set(responses)
    assert len(unique_responses) >= 2  # At least 2 different responses


def test_review_response_sentiment_detection(client):
    """Test sentiment detection in template-based responses."""
    positive_review = "Amazing service! Love it!"
    negative_review = "Worst experience ever. Terrible!"
    
    r1 = client.post('/api/generate-review-response', json={
        'review_text': positive_review,
        'tone': 'professional'
    })
    r2 = client.post('/api/generate-review-response', json={
        'review_text': negative_review,
        'tone': 'professional'
    })
    
    j1 = r1.get_json()
    j2 = r2.get_json()
    
    # Both should succeed
    assert j1['ok'] is True
    assert j2['ok'] is True
    
    # If using template method, check sentiment detection
    if j1.get('method') == 'template':
        assert 'detected_sentiment' in j1
        assert j1['detected_sentiment'] == 'positive'
    
    if j2.get('method') == 'template':
        assert 'detected_sentiment' in j2
        assert j2['detected_sentiment'] == 'negative'


def test_review_response_page_accessible(client):
    """Test that review response page is accessible."""
    r = client.get('/review-response')
    assert r.status_code == 200
    assert b'Review Response Generator' in r.data or b'review' in r.data.lower()
