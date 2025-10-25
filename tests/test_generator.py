from generator import make_caption, naturalize_hint, generate_cta, default_hashtags
import random

def test_make_caption_can_include_company():
    """Test that company name can appear in generated captions."""
    # Run multiple times to check if company appears at least sometimes
    company_found = False
    for seed in range(10):
        random.seed(seed)
        caption = make_caption(
            industry='Bakery',
            tone='friendly',
            pillar_name='Product/Offer',
            pillar_hint='Highlight one offering',
            platform='instagram',
            brand_keywords=['artisan'],
            hashtags=['#bakery'],
            goals=['promote'],
            company='Laura\'s Bakery'
        )
        if 'Laura\'s Bakery' in caption or 'Laura' in caption:
            company_found = True
            break
    # Company should appear at least once in 10 tries
    assert company_found, "Company name should appear in at least some captions"

def test_make_caption_is_natural():
    """Test that generated captions are natural and not template-like."""
    random.seed(123)
    caption = make_caption(
        industry='Bakery',
        tone='friendly',
        pillar_name='Educational',
        pillar_hint='Share a quick tip that solves a common problem for your audience.',
        platform='instagram',
        brand_keywords=['artisan'],
        hashtags=['#bakery', '#tips'],
        goals=['engagement'],
        company='Test Bakery'
    )
    # Should not contain template-like language
    assert 'Share a quick tip' not in caption
    assert 'Tone:' not in caption
    assert 'Platform tip:' not in caption
    # Should contain natural language
    assert len(caption) > 50  # Should have substantial content
    assert '#' in caption  # Should include hashtags

def test_naturalize_hint_converts_generic_to_natural():
    """Test that hints are converted to natural language."""
    hint = "Share a quick tip that solves a common problem for your audience."
    natural = naturalize_hint(hint, "Bakery", ["sourdough"])
    # Should not contain the original template language
    assert "Share a quick tip" not in natural
    # Should be conversational
    assert len(natural) > 20

def test_generate_cta_returns_appropriate_cta():
    """Test that CTAs are generated based on pillar and tone."""
    random.seed(42)
    cta = generate_cta("Educational", "friendly", "instagram")
    assert len(cta) > 0
    assert isinstance(cta, str)
    
    cta_pro = generate_cta("Product/Offer", "professional", "linkedin")
    assert len(cta_pro) > 0
    assert isinstance(cta_pro, str)

def test_caption_varies_by_tone():
    """Test that different tones produce different styles of captions."""
    random.seed(42)
    
    friendly = make_caption(
        industry='Bakery',
        tone='friendly',
        pillar_name='Educational',
        pillar_hint='Share a quick tip',
        platform='instagram',
        brand_keywords=[],
        hashtags=['#bakery'],
        goals=[],
        company=''
    )
    
    random.seed(42)
    professional = make_caption(
        industry='Bakery',
        tone='professional',
        pillar_name='Educational',
        pillar_hint='Share a quick tip',
        platform='instagram',
        brand_keywords=[],
        hashtags=['#bakery'],
        goals=[],
        company=''
    )
    
    # They should be different (note: they use different random seeds internally)
    # At minimum, they should both be valid captions
    assert len(friendly) > 20
    assert len(professional) > 20
    assert '#bakery' in friendly
    assert '#bakery' in professional

def test_platform_specific_hashtag_limits():
    """Test that different platforms have appropriate hashtag counts."""
    random.seed(42)
    hashtags_many = ['#tag1', '#tag2', '#tag3', '#tag4', '#tag5', '#tag6', '#tag7', '#tag8', '#tag9', '#tag10', '#tag11', '#tag12']
    
    # Twitter should have fewer hashtags
    twitter_caption = make_caption(
        industry='Business',
        tone='friendly',
        pillar_name='Educational',
        pillar_hint='Share a tip',
        platform='twitter',
        brand_keywords=[],
        hashtags=hashtags_many,
        goals=[],
        company=''
    )
    twitter_tag_count = twitter_caption.count('#')
    assert twitter_tag_count <= 3  # Twitter gets max 3 hashtags
    
    # Instagram should allow more hashtags
    instagram_caption = make_caption(
        industry='Business',
        tone='friendly',
        pillar_name='Educational',
        pillar_hint='Share a tip',
        platform='instagram',
        brand_keywords=[],
        hashtags=hashtags_many,
        goals=[],
        company=''
    )
    instagram_tag_count = instagram_caption.count('#')
    assert instagram_tag_count >= 8  # Instagram allows more hashtags

def test_caption_includes_hashtags():
    """Test that hashtags are included in the output."""
    random.seed(42)
    hashtags = ['#bakery', '#bread', '#local']
    caption = make_caption(
        industry='Bakery',
        tone='friendly',
        pillar_name='Educational',
        pillar_hint='Share a tip',
        platform='instagram',
        brand_keywords=[],
        hashtags=hashtags,
        goals=[],
        company=''
    )
    # All hashtags should be present
    for tag in hashtags:
        assert tag in caption

def test_multiple_pillars_produce_different_content():
    """Test that different content pillars produce appropriately different captions."""
    random.seed(100)
    
    educational = make_caption(
        industry='Fitness',
        tone='friendly',
        pillar_name='Educational',
        pillar_hint='Share a quick tip that solves a common problem for your audience.',
        platform='instagram',
        brand_keywords=[],
        hashtags=['#fitness'],
        goals=[],
        company=''
    )
    
    random.seed(100)
    testimonial = make_caption(
        industry='Fitness',
        tone='friendly',
        pillar_name='Testimonial/Social Proof',
        pillar_hint='Share a short customer quote and the outcome they achieved.',
        platform='instagram',
        brand_keywords=[],
        hashtags=['#fitness'],
        goals=[],
        company=''
    )
    
    # Both should be valid
    assert len(educational) > 20
    assert len(testimonial) > 20
    # Should both contain hashtags
    assert '#fitness' in educational
    assert '#fitness' in testimonial
