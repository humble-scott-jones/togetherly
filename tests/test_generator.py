from generator import make_caption

def test_make_caption_includes_company():
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
    assert 'From Laura\'s Bakery.' in caption or 'From Laura\'s Bakery' in caption
