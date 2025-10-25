from datetime import date, timedelta
from typing import Optional
import os
import random

# Optional OpenAI integration for enhanced post generation
USE_OPENAI_FOR_POSTS = bool(os.getenv("OPENAI_API_KEY")) and os.getenv("USE_OPENAI_FOR_POSTS", "0") == "1"
if USE_OPENAI_FOR_POSTS:
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception:
        USE_OPENAI_FOR_POSTS = False
        _openai_client = None
else:
    _openai_client = None

PILLARS_BY_DEFAULT = [
    ("Educational", "Share a quick tip that solves a common problem for your audience."),
    ("Behind-the-Scenes", "Show a candid look at your process, team, or workspace."),
    ("Testimonial/Social Proof", "Share a short customer quote and the outcome they achieved."),
    ("Product/Offer", "Highlight one offering with benefits, price (optional), and CTA."),
    ("Engagement", "Ask a question or run a simple poll to spark comments."),
    ("Story", "Tell a brief story of a challenge → action → result."),
]

PLATFORM_HINTS = {
    "instagram": "Keep it visual, 1–2 short paragraphs, 8–12 niche hashtags.",
    "facebook": "Conversational tone, 2–3 short paragraphs. Invite replies.",
    "linkedin": "Value-forward, concise, 1–2 actionable insights, 3–6 hashtags.",
    "tiktok": "Hook in first sentence, keep lines punchy, suggest a shot list.",
    "twitter": "Short & punchy. 1–2 tweets per post; avoid walls of text.",
}

# Natural language templates for different content pillars
NATURAL_TEMPLATES = {
    "Educational": {
        "friendly": [
            "Hey friends! 👋 Quick tip for you: {hint}",
            "Here's something we've learned: {hint}",
            "Pro tip alert! 🎯 {hint}",
        ],
        "professional": [
            "{hint}",
            "Industry insight: {hint}",
            "Best practice: {hint}",
        ],
        "playful": [
            "Psst... want to know a secret? 🤫 {hint}",
            "Plot twist! {hint}",
            "Hot take: {hint}",
        ],
        "inspirational": [
            "Here's something powerful: {hint}",
            "Let's talk growth: {hint}",
            "Wisdom worth sharing: {hint}",
        ],
    },
    "Behind-the-Scenes": {
        "friendly": [
            "Pulling back the curtain today! 🎬 {hint}",
            "Ever wondered how we do it? {hint}",
            "Sneak peek time! {hint}",
        ],
        "professional": [
            "Transparency is key to trust. {hint}",
            "Our process matters. {hint}",
            "Inside look at our operations: {hint}",
        ],
        "playful": [
            "Ready for a backstage pass? 🎭 {hint}",
            "Shhh, we're letting you in on our secrets! {hint}",
            "BTS magic happening here! ✨ {hint}",
        ],
        "inspirational": [
            "The journey matters as much as the destination. {hint}",
            "Real work, real passion. {hint}",
            "Behind every result is a story. {hint}",
        ],
    },
    "Testimonial/Social Proof": {
        "friendly": [
            "Love hearing success stories! 💙 {hint}",
            "This made our day! {hint}",
            "When our customers shine, we all shine! ⭐ {hint}",
        ],
        "professional": [
            "Client success spotlight: {hint}",
            "Proven outcomes: {hint}",
            "Case study highlight: {hint}",
        ],
        "playful": [
            "Bragging rights incoming! 🏆 {hint}",
            "Plot twist: We have the coolest customers! {hint}",
            "Mic drop moment! 🎤 {hint}",
        ],
        "inspirational": [
            "Nothing inspires us more than your success. {hint}",
            "Your story, our pride. {hint}",
            "Success leaves clues. {hint}",
        ],
    },
    "Product/Offer": {
        "friendly": [
            "Excited to share this with you! {hint}",
            "Something special for you! ✨ {hint}",
            "We've been working on something great! {hint}",
        ],
        "professional": [
            "Introducing a solution designed with you in mind. {hint}",
            "New offering available: {hint}",
            "Enhance your results with: {hint}",
        ],
        "playful": [
            "Ta-da! 🎉 {hint}",
            "We made a thing! {hint}",
            "New drop alert! 🚨 {hint}",
        ],
        "inspirational": [
            "Created to empower you. {hint}",
            "Every solution starts with understanding your needs. {hint}",
            "Innovation meets purpose. {hint}",
        ],
    },
    "Engagement": {
        "friendly": [
            "We want to hear from YOU! {hint}",
            "Let's chat! {hint}",
            "Quick question for you! {hint}",
        ],
        "professional": [
            "Your input shapes our direction. {hint}",
            "Industry discussion: {hint}",
            "We value your expertise. {hint}",
        ],
        "playful": [
            "Okay, settle a debate! {hint}",
            "Pop quiz! 📝 {hint}",
            "Spill the tea! ☕ {hint}",
        ],
        "inspirational": [
            "Your voice creates change. {hint}",
            "Together we learn, together we grow. {hint}",
            "Every perspective adds value. {hint}",
        ],
    },
    "Story": {
        "friendly": [
            "Story time! 📖 {hint}",
            "Let us tell you about something that happened... {hint}",
            "Here's a little story from us: {hint}",
        ],
        "professional": [
            "Case in point: {hint}",
            "Learning from experience: {hint}",
            "Real-world application: {hint}",
        ],
        "playful": [
            "Buckle up for this one! 🎢 {hint}",
            "No joke, this actually happened! {hint}",
            "Storytime with a twist! {hint}",
        ],
        "inspirational": [
            "Every setback is a setup for a comeback. {hint}",
            "From challenge to triumph: {hint}",
            "The journey taught us everything. {hint}",
        ],
    },
}

def default_hashtags(industry: str, niche_keywords: list[str]):
    base = [f"#{industry.replace(' ', '')[:18]}", "#SmallBusiness", "#LocalBiz", "#BehindTheScenes", "#Tips"]
    extra = [f"#{k.strip().replace(' ', '')[:18]}" for k in niche_keywords if k.strip()]
    seen = set()
    tags = []
    for t in base + extra:
        t_low = t.lower()
        if t_low not in seen:
            tags.append(t)
            seen.add(t_low)
    return tags[:12]

def to_sentence_case(s: str):
    if not s: return s
    return s[0].upper() + s[1:]

def naturalize_hint(hint: str, industry: str, brand_keywords: list[str]) -> str:
    """Convert a generic hint into a more natural, industry-specific suggestion."""
    # Map generic hints to more natural, actionable language
    hint = hint.strip()
    
    # Create more natural conversational phrases
    if "Share a quick tip" in hint or "solves a common problem" in hint:
        options = [
            f"did you know this trick can really transform your {industry.lower()} game?",
            f"here's something that's been a total game-changer for our {industry.lower()} work!",
            f"this simple hack makes such a difference!",
            f"we discovered this recently and had to share!",
        ]
        return random.choice(options)
    
    elif "candid look" in hint or "process, team" in hint:
        options = [
            "we're pulling back the curtain and showing you exactly how we do what we do!",
            "ever wondered what goes on behind the scenes? Here's a peek!",
            "this is what a typical day looks like for us!",
            "the real magic happens when you're not looking – check this out!",
        ]
        return random.choice(options)
    
    elif "customer quote" in hint or "outcome they achieved" in hint:
        options = [
            "one of our amazing customers shared this and we just had to tell you!",
            "seeing results like this never gets old – here's what happened!",
            "this testimonial made our whole week!",
            "when our customers win, we ALL win!",
        ]
        return random.choice(options)
    
    elif "Highlight one offering" in hint or "benefits, price" in hint:
        options = [
            "we're excited to share something special with you!",
            "this is one of our favorites and we think you're going to love it too!",
            "ready for something amazing?",
            "let us introduce you to something we've been working on!",
        ]
        return random.choice(options)
    
    elif "question" in hint or "poll" in hint or "spark comments" in hint:
        options = [
            "we have a question for you and we're really curious to hear what you think!",
            "let's settle this once and for all – we need your opinion!",
            "we're polling our community – what's YOUR take?",
            "your input would be super valuable here!",
        ]
        return random.choice(options)
    
    elif "story" in hint or "challenge" in hint or "action → result" in hint:
        options = [
            "let us tell you about something that happened recently!",
            "so this happened and we learned something important!",
            "here's a quick story we think you'll relate to!",
            "we faced a challenge recently – here's what we learned!",
        ]
        return random.choice(options)
    
    else:
        # Fallback: make it more conversational
        return f"we wanted to share something about {industry.lower()} with you!"

def generate_cta(pillar_name: str, tone: str, platform: str) -> str:
    """Generate a natural call-to-action based on pillar and tone."""
    ctas = {
        "Educational": {
            "friendly": ["Try this and let us know how it works!", "Have you tried something similar?", 
                        "Share your tips below!", "What's worked for you?"],
            "professional": ["What strategies have you implemented?", "Share your insights below.",
                           "Connect with us to discuss further.", "What are your thoughts?"],
            "playful": ["Give it a shot! 🚀", "Your turn – what do you think?", 
                       "Tag someone who needs this!", "Try it and report back! 😄"],
            "inspirational": ["What will you try today?", "Share your journey below.", 
                            "Let's grow together.", "What's your next step?"],
        },
        "Behind-the-Scenes": {
            "friendly": ["What would you like to see next?", "Want more behind-the-scenes content?",
                        "Drop a 👋 if you enjoyed this peek!", "Questions? We're here!"],
            "professional": ["Want to learn more about our process?", "Connect with our team for details.",
                           "Follow us for more insights.", "Reach out with questions."],
            "playful": ["Cool, right?! 😎", "Mind. Blown. 🤯", "More of this? Say yes!",
                       "Bet you didn't know that! 🎉"],
            "inspirational": ["This is the work that matters.", "Behind every success is dedication.",
                            "What's your behind-the-scenes story?", "The process is beautiful."],
        },
        "Testimonial/Social Proof": {
            "friendly": ["What's your success story?", "Share your experience below!",
                        "We'd love to celebrate your wins too!", "Tell us how it went!"],
            "professional": ["Ready for similar results?", "Connect with us to get started.",
                           "Schedule your consultation.", "Learn how we can help you."],
            "playful": ["Your turn to shine! ⭐", "Drop your success story!", "Brag a little – we won't judge! 😉",
                       "You could be next! 🎯"],
            "inspirational": ["Your success inspires others.", "Share your story, inspire someone.",
                            "What did you overcome?", "Every journey matters."],
        },
        "Product/Offer": {
            "friendly": ["Interested? DM us!", "Check it out at the link in bio!",
                        "Want to learn more? Just ask!", "Questions? Drop them below!"],
            "professional": ["Contact us for details.", "Schedule a consultation today.",
                           "Learn more at [link].", "Reach out to discuss pricing."],
            "playful": ["Grab yours now! 🔥", "Don't sleep on this! ⚡", "You know you want it! 😄",
                       "Link in bio – go go go! 🏃"],
            "inspirational": ["Ready to transform your results?", "Take the next step today.",
                            "Your success starts here.", "Invest in yourself."],
        },
        "Engagement": {
            "friendly": ["Tell us in the comments!", "We're curious – what do YOU think?",
                        "Comment below! 👇", "Let's discuss!"],
            "professional": ["Share your perspective.", "Join the discussion.",
                           "We value your input.", "What's your take?"],
            "playful": ["Spill! We're waiting! ☕", "Comment or forever hold your peace! 😄",
                       "Don't be shy – speak up! 💬", "All answers welcome! 🎉"],
            "inspirational": ["Your voice matters.", "Contribute to the conversation.",
                            "Share your wisdom.", "Let's learn together."],
        },
        "Story": {
            "friendly": ["Have a similar story?", "Can you relate?",
                        "What happened in your situation?", "Share your story!"],
            "professional": ["What lessons have you learned?", "Share your experience.",
                           "How have you handled similar situations?", "Your insights welcome."],
            "playful": ["Top that! 😄", "Your turn – story time! 📖",
                       "What's YOUR wild story?", "Beat this! 🎭"],
            "inspirational": ["What challenge did you overcome?", "Share your transformation.",
                            "Your journey inspires.", "What did you learn?"],
        },
    }
    
    # Get tone-specific CTAs for this pillar, with fallback
    pillar_ctas = ctas.get(pillar_name, {})
    tone_ctas = pillar_ctas.get(tone, pillar_ctas.get("friendly", ["Let us know what you think!"]))
    
    # Return a random CTA from the list
    return random.choice(tone_ctas)

def enhance_caption_with_ai(caption_draft: str, industry: str, tone: str, platform: str, company: str = "") -> str:
    """
    Optionally enhance a caption using OpenAI for more sophisticated, natural language.
    Falls back to the original caption if OpenAI is not available or fails.
    """
    if not USE_OPENAI_FOR_POSTS or not _openai_client:
        return caption_draft
    
    try:
        # Create a prompt for OpenAI to enhance the caption
        system_prompt = f"""You are an expert social media copywriter specializing in {platform} content.
Your task is to enhance social media captions to be more engaging, natural, and effective while maintaining the core message.
Keep the tone {tone} and preserve any hashtags provided."""
        
        company_context = f" for {company}" if company else ""
        user_prompt = f"""Enhance this {industry} social media caption{company_context}:

{caption_draft}

Requirements:
- Keep it natural and engaging
- Maintain the {tone} tone
- Keep it appropriate for {platform}
- Preserve all hashtags at the end
- Keep the length similar (don't make it much longer)
- Make it feel more human and less template-like

Enhanced caption:"""
        
        response = _openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        enhanced = response.choices[0].message.content.strip()
        
        # Basic validation: if the enhanced version is too different or broken, use original
        if enhanced and len(enhanced) > 20 and '#' in enhanced:
            return enhanced
        else:
            return caption_draft
            
    except Exception as e:
        # If anything fails, just return the original caption
        return caption_draft

def make_caption(industry: str, tone: str, pillar_name: str, pillar_hint: str,
                 platform: str, brand_keywords: list[str], hashtags: list[str], goals: list[str], company: str = ""):
    """Generate a natural, engaging social media caption using template-based NLP approach."""
    
    # Naturalize the hint to make it more conversational
    natural_hint = naturalize_hint(pillar_hint, industry, brand_keywords)
    # Capitalize first letter if needed
    if natural_hint and natural_hint[0].islower():
        natural_hint = natural_hint[0].upper() + natural_hint[1:]
    
    # Generate contextual CTA
    cta = generate_cta(pillar_name, tone, platform)
    
    # Get appropriate templates for pillar and tone
    templates = NATURAL_TEMPLATES.get(pillar_name, NATURAL_TEMPLATES["Educational"])
    tone_templates = templates.get(tone, templates.get("friendly", templates["friendly"]))
    
    # Select a random template
    template = random.choice(tone_templates)
    
    # Fill in the template with the natural hint
    body = template.format(hint=natural_hint)
    
    # Add CTA on a new line for better readability
    body = f"{body}\n\n{cta}"
    
    # Add company mention as a signature line
    if company:
        # Vary how we mention the company based on tone
        if tone.lower() == "professional":
            company_line = f"\n\n– {company}" if random.random() > 0.5 else ""
        elif tone.lower() == "playful":
            emoji_options = ["✨", "💙", "🎉", ""]
            emoji = random.choice(emoji_options)
            company_line = f"\n\n{emoji} {company}".strip() if random.random() > 0.6 else ""
        else:
            # Friendly, inspirational
            company_line = f"\n\n💙 {company}" if random.random() > 0.5 else ""
        
        body = f"{body}{company_line}"
    
    # Add platform-specific formatting and hashtags
    if platform.lower() == "twitter":
        # Keep it shorter for Twitter
        if len(body) > 240:
            body = body[:237] + "..."
        tags = " ".join(hashtags[:3])
    elif platform.lower() == "linkedin":
        tags = " ".join(hashtags[:5])
    elif platform.lower() == "instagram":
        tags = " ".join(hashtags[:12])
    elif platform.lower() == "facebook":
        tags = " ".join(hashtags[:8])
    else:
        tags = " ".join(hashtags[:8])
    
    # Create the final caption
    final_caption = f"{body}\n\n{tags}".strip()
    
    # Optionally enhance with AI if enabled
    if USE_OPENAI_FOR_POSTS:
        final_caption = enhance_caption_with_ai(final_caption, industry, tone, platform, company)
    
    return final_caption

def image_prompt(industry: str, pillar_name: str, brand_keywords: list[str], company: str = ""):
    kw = ", ".join(brand_keywords) if brand_keywords else "on-brand colors"
    company_part = f"Company: {company}. " if company else ""
    return (f"High-quality photo for social post. {company_part}Industry: {industry}. "
            f"Content pillar: {pillar_name}. Style: natural light, minimal background, {kw}.")

def make_reel_plan(industry: str, pillar_name: str, brand_keywords: list[str], tone: str, company: str = "", reel_style: Optional[str] = None):
    # structured reel plan; supports a basic `reel_style` preference when provided
    style = (reel_style or "Face-camera tips")
    # pick some hooks based on style
    hooks_map = {
        "Face-camera tips": [
            "3 mistakes costing you customers 👇",
            "Try this before your next post…",
            "The 30-second fix for engagement"
        ],
        "Property b-roll + captions": [
            f"Inside this {industry} feature in 30s 🏡",
            "3 features you’ll miss if you scroll fast…",
            "Before/After: tiny changes, big feel"
        ],
        "Product b-roll + captions": [
            f"Check out this {pillar_name} in 30s ✨",
            "3 reasons customers love this…",
            "Quick tour: what makes it special"
        ],
        "Local hotspot montage": [
            f"Spend a perfect morning in {pillar_name} ☀️",
            "Hidden gem you’ve gotta try…",
            "Locals know this trick 🤫"
        ],
        "Story + before/after": [
            "From idea → launch in 30s",
            "We almost gave up—then this happened",
            "Tiny change → big result"
        ],
        "Workout montage": [
            "Quick 3-move sequence to level up your routine",
            "Try this superset for max results",
            "Short challenge: do 3 rounds"
        ]
    }

    chosen_hooks = hooks_map.get(style) or hooks_map.get("Face-camera tips")
    if not chosen_hooks:
        chosen_hooks = hooks_map["Face-camera tips"]
    hook = chosen_hooks[0]

    # script beats: timestamps for a ~30–40s reel
    beats = [
        {"t": "0-3s",  "osd": "Hook", "line": hook},
        {"t": "3-10s", "osd": "Point 1", "line": "Problem your audience feels + quick promise."},
        {"t": "10-20s","osd": "Point 2", "line": "One actionable tip aligned to your goals."},
        {"t": "20-30s","osd": "Point 3", "line": "Example or mini story to make it real."},
        {"t": "30-40s","osd": "CTA", "line": "Comment a question / DM for help / Check link in bio."}
    ]

    shot_map = {
        "Face-camera tips": [
            "Front-facing A-roll, eye-level, natural light",
            "Cutaways: screen recording, product close-up",
            "End with CTA text overlay"
        ],
        "Property b-roll + captions": [
            "Exterior wide → entry → kitchen → feature highlight",
            "Quick pans, 0.8x speed ramp between rooms",
            "On-screen captions for each highlight"
        ],
        "Product b-roll + captions": [
            "Wide shot → detail close-ups → demo",
            "Match edits to beat; short clips per feature",
            "Add caption overlays for key specs"
        ],
        "Local hotspot montage": [
            "Sign → interior → hero item → smiling staff → crowd",
            "Match cuts to beat; 0.5s–1.0s per clip",
            "End with text: name + location"
        ],
        "Story + before/after": [
            "Talking head intro",
            "B-roll: before clip/photos",
            "After reveal with text overlay"
        ],
        "Workout montage": [
            "Demonstration A-roll",
            "Close-ups on form",
            "Speed ramps and finishing CTA"
        ]
    }

    shot_list = shot_map.get(style, ["Talking head + a few cutaways, end with CTA"])

    hashtags = default_hashtags(industry, brand_keywords)
    thumb_prompt = f"Portrait thumbnail: {industry} • {style}. Clean bold text, high contrast, subject centered."

    return {
        "style": style,
        "hook": hook,
        "beats": beats,
        "script_beats": [b.get('line') if isinstance(b, dict) else b for b in beats],
        "shot_list": shot_list,
        "on_screen_text": [b.get('osd') for b in beats],
        "hashtags": hashtags,
        "cta": "Comment / DM / Link in bio",
        "thumbnail_prompt": thumb_prompt,
        "srt_prompt": f"Generate SRT subtitles for a ~30-40s reel about {pillar_name} in {industry}. Tone: {tone}."
    }

def unsplash_link(industry: str, pillar_name: str):
    q = f"{industry} {pillar_name}".replace(" ", "+")
    return f"https://source.unsplash.com/featured/?{q}"

def rolling_pillars():
    while True:
        for name, hint in PILLARS_BY_DEFAULT:
            yield (name, hint)

def generate_posts(days: int, start_day, industry: str, tone: str,
                   platforms: list[str], brand_keywords: list[str],
                   include_images: bool, niche_keywords: list[str], goals: list[str], company: str = "", details: Optional[dict] = None):
    posts = []
    pillar_stream = rolling_pillars()
    hashtags = default_hashtags(industry, niche_keywords)

    for i in range(days):
        day = start_day + timedelta(days=i)
        pillar_name, pillar_hint = next(pillar_stream)
        for p in platforms:
            caption = make_caption(
                industry=to_sentence_case(industry.strip() or "Business"),
                tone=tone,
                pillar_name=pillar_name,
                pillar_hint=pillar_hint,
                platform=p,
                brand_keywords=brand_keywords,
                hashtags=hashtags,
                goals=goals,
                company=company
            )
            iprompt = image_prompt(industry, pillar_name, brand_keywords, company)
            img_url = unsplash_link(industry, pillar_name) if include_images else None

            reel_obj = None
            if p.lower() in ["instagram", "tiktok", "short_video"]:
                reel_style = None
                try:
                    reel_style = (details or {}).get('reel_style')
                except Exception:
                    reel_style = None
                reel_obj = make_reel_plan(industry, pillar_name, brand_keywords, tone, company, reel_style)

            posts.append({
                "date": day.isoformat(),
                "day_index": i + 1,
                "platform": p,
                "pillar": pillar_name,
                "caption": caption,
                "image_prompt": iprompt,
                "image_url": img_url,
                "reel": reel_obj
            })
    return posts
