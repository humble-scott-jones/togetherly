# AI-Powered Natural Language Generation for Social Media Posts

## Overview

The Togetherly app now uses sophisticated natural language processing to generate engaging, authentic social media posts instead of template-based content. The system includes both a robust template-based approach and optional OpenAI integration for even more refined results.

## Features

### 1. Natural Language Templates

The generator uses a comprehensive library of natural language templates that adapt based on:

- **Content Pillar**: Educational, Behind-the-Scenes, Testimonial/Social Proof, Product/Offer, Engagement, Story
- **Tone**: Friendly, Professional, Playful, Inspirational
- **Platform**: Instagram, Facebook, LinkedIn, Twitter, TikTok

### 2. Smart Hint Naturalizer

Converts generic content instructions into natural, conversational language:

**Before:**
```
"Share a quick tip that solves a common problem for your audience."
```

**After:**
```
"Did you know this trick can really transform your bakery game?"
```

### 3. Context-Aware CTAs

Generates appropriate calls-to-action based on content type and tone:

- Educational: "Try this and let us know how it works!"
- Engagement: "We'd love to hear your thoughts on this!"
- Product: "Interested? DM us!"

### 4. Platform-Specific Optimization

- **Twitter**: Max 3 hashtags, 240 character limit
- **LinkedIn**: 5 hashtags, professional formatting
- **Instagram**: Up to 12 hashtags, visual-focused
- **Facebook**: 8 hashtags, conversational tone

## Usage

### Basic Usage (Template-Based)

The system works out of the box with no additional configuration:

```python
from generator import make_caption, default_hashtags

caption = make_caption(
    industry='Bakery',
    tone='friendly',
    pillar_name='Educational',
    pillar_hint='Share a quick tip that solves a common problem for your audience.',
    platform='instagram',
    brand_keywords=['artisan', 'sourdough'],
    hashtags=default_hashtags('Bakery', ['bread', 'baking']),
    goals=['engagement'],
    company='Laura\'s Bakery'
)
```

**Output:**
```
Pro tip alert! 🎯 Did you know this trick can really transform your bakery game?

Try this and let us know how it works!

#Bakery #SmallBusiness #LocalBiz #BehindTheScenes #Tips #artisan #sourdough
```

### Advanced Usage (OpenAI Enhancement)

For even more sophisticated posts, enable OpenAI integration:

1. Set environment variables:
   ```bash
   export OPENAI_API_KEY="sk-proj-your-api-key"
   export USE_OPENAI_FOR_POSTS="1"
   ```

2. The system will automatically enhance captions using GPT-3.5-turbo while maintaining:
   - The intended tone
   - Platform appropriateness
   - All hashtags
   - Core message

3. Fallback: If OpenAI is unavailable or fails, the system automatically falls back to the template-based approach.

## Example Outputs

### Friendly Educational Post
```
Hey friends! 👋 Quick tip for you: Did you know this trick can really transform your bakery game?

Share your tips below!

💙 Laura's Bakery

#Bakery #SmallBusiness #LocalBiz #Tips #artisan #sourdough
```

### Professional Product Offer
```
New offering available: Let us introduce you to something we've been working on!

Contact us for details.

– Prime Properties

#RealEstate #SmallBusiness #LocalBiz #BehindTheScenes #Tips
```

### Playful Behind-the-Scenes
```
Ready for a backstage pass? 🎭 We're pulling back the curtain and showing you exactly how we do what we do!

More of this? Say yes!

✨ Bean There Cafe

#CoffeeShop #SmallBusiness #LocalBiz #BehindTheScenes #organic #locally-roasted
```

### Inspirational Story
```
From challenge to triumph: We faced a challenge recently – here's what we learned!

What did you learn?

#Fitness #SmallBusiness #LocalBiz #transformation #strength
```

## Technical Details

### Architecture

1. **Template Selection**: Chooses from 144+ unique template variations (6 pillars × 4 tones × 6+ variations)
2. **Hint Naturalization**: Converts generic instructions to natural language
3. **CTA Generation**: Selects contextually appropriate calls-to-action
4. **Platform Formatting**: Applies platform-specific rules
5. **Optional AI Enhancement**: Refines the output using GPT-3.5-turbo (if enabled)

### Randomization

The system uses seeded randomization to:
- Vary template selection
- Add natural variation to company mentions
- Prevent repetitive content
- Maintain authenticity

### Performance

- **Template-based**: Instant generation (~10ms)
- **AI-enhanced**: ~1-2 seconds (dependent on OpenAI API response time)
- **Fallback**: Automatic to template-based if AI fails

## Testing

Run the test suite:

```bash
python3 -m pytest tests/test_generator.py -v
```

Tests cover:
- Natural language verification (no template markers)
- Platform-specific hashtag limits
- Tone variation
- Company name inclusion
- CTA generation
- Multi-pillar content support

## Benefits

1. **More Engaging**: Posts sound human-written, not template-generated
2. **Platform-Optimized**: Each post is tailored for its target platform
3. **Tone-Appropriate**: Content matches brand voice consistently
4. **Flexible**: Works with or without AI enhancement
5. **Reliable**: Automatic fallback ensures posts are always generated

## Future Enhancements

Potential improvements:
- Support for additional AI models (Claude, Llama, etc.)
- A/B testing framework for caption variants
- Industry-specific vocabulary enhancement
- Multi-language support
- Emoji recommendation engine
- Sentiment analysis for tone matching

## Configuration

### Environment Variables

```bash
# Required for basic functionality
# (No special configuration needed - works out of the box)

# Optional: Enable AI enhancement
OPENAI_API_KEY=sk-proj-your-api-key-here
USE_OPENAI_FOR_POSTS=1  # Set to "1" to enable
```

### Customization

To add custom templates or modify the natural language:

1. Edit `generator.py`
2. Update `NATURAL_TEMPLATES` dictionary
3. Add new entries following the existing pattern
4. Test with `test_generator.py`

## Support

For issues or questions:
- Check the test suite for usage examples
- Review `generator.py` for implementation details
- See `.env.example` for configuration options
