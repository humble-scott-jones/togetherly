from datetime import date, timedelta
from typing import Optional

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

def make_caption(industry: str, tone: str, pillar_name: str, pillar_hint: str,
                 platform: str, brand_keywords: list[str], hashtags: list[str], goals: list[str], company: str = ""):
    tone_blurb = {
        "friendly": "Warm, encouraging, and conversational.",
        "professional": "Clear, confident, and value-focused.",
        "playful": "Upbeat, witty, and a bit cheeky.",
        "inspirational": "Uplifting, thoughtful, and mission-driven."
    }.get(tone.lower(), "Conversational and helpful.")

    platform_hint = PLATFORM_HINTS.get(platform.lower(), "Make it concise and useful.")
    brand_line = f" ({', '.join(brand_keywords)})" if brand_keywords else ""
    goal_line = f"Focus: {', '.join(goals)}." if goals else ""

    company_line = f"From {company}." if company else ""
    body = (
        f"{pillar_name} • {industry}{brand_line}\n"
        f"{pillar_hint}\n\n"
        f"{company_line}\n"
        f"{goal_line}\n"
        f"Tone: {tone_blurb}\n"
        f"Platform tip: {platform_hint}\n\n"
        f"CTA: Tell us what you think below 👇"
    )

    tags = " ".join(hashtags)
    return f"{body}\n\n{tags}"

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
