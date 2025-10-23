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

def make_reel_plan(industry: str, pillar_name: str, brand_keywords: list[str], tone: str, company: str = "", reel_style: Optional[str] = None, goals: Optional[list[str]] = None, niche_keywords: Optional[list[str]] = None):
    # structured reel plan; tailor suggestions by industry and an optional `reel_style` preference
    style = (reel_style or "Face-camera tips")
    goals = goals or []
    niche_keywords = niche_keywords or []

    # industry-specific modifiers to make outputs more relevant to the professional
    industry_key = (industry or "").lower()
    industry_mods = {
        "realtor": {
            "cta": "Schedule a showing or DM for details.",
            "thumb_extra": "Show a room or exterior with bold feature text",
            "hook_pfx": "House tip:"
        },
        "restaurant": {
            "cta": "Reserve a table or check the menu link.",
            "thumb_extra": "Close-up of dish with appetizing colors",
            "hook_pfx": "Chef's secret:"
        },
        "retail": {
            "cta": "Shop now or visit us in-store.",
            "thumb_extra": "Product shot with clear price/text",
            "hook_pfx": "New in:"
        },
        "fitness": {
            "cta": "Try this move & tag us in your video.",
            "thumb_extra": "Action shot with energetic typography",
            "hook_pfx": "Quick workout:"
        },
        "artisan": {
            "cta": "Shop the collection or visit the studio.",
            "thumb_extra": "Close-up of hands at work",
            "hook_pfx": "Behind the craft:"
        },
        "coach": {
            "cta": "Book a consult or grab the free worksheet.",
            "thumb_extra": "Headshot with clear value statement",
            "hook_pfx": "Quick tip:"
        },
        "nonprofit": {
            "cta": "Learn how to help or donate today.",
            "thumb_extra": "Impact photo with short stat overlay",
            "hook_pfx": "Impact story:"
        },
        "home_services": {
            "cta": "Book an estimate or ask for a quote.",
            "thumb_extra": "Before/after split with clear label",
            "hook_pfx": "Before & after:"
        },
        "healthcare": {
            "cta": "Book a consult or learn more on our site.",
            "thumb_extra": "Friendly staff or clinic photo with clear text",
            "hook_pfx": "Health tip:"
        }
    }

    mods = industry_mods.get(industry_key, {"cta": "Comment / DM / Link in bio", "thumb_extra": "Clean bold text, subject centered", "hook_pfx": "Quick tip:"})

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

    # allow fallback to a style-agnostic set if exact match not found
    chosen_hooks = hooks_map.get(style) or hooks_map.get("Face-camera tips")
    if not chosen_hooks:
        chosen_hooks = hooks_map["Face-camera tips"]
    # combine industry prefix with the chosen hook to make it specific
    raw_hook = chosen_hooks[0]
    hook = f"{mods.get('hook_pfx','Quick tip:')} {raw_hook}"

    # script beats: timestamps for a ~30–40s reel
    # Compose script beats and customize lines using goals/company/context
    problem_line = "A common pain point your audience has and why it matters." 
    if goals:
        problem_line = f"Pain point related to: {', '.join(goals[:2])}."
    tip_line = "One actionable tip the viewer can try right away."
    example_line = f"Quick example or result — mention {company} if relevant." if company else "Quick example or result to make it real."
    cta_line = mods.get('cta')

    beats = [
        {"t": "0-3s",  "osd": "Hook", "line": hook},
        {"t": "3-10s", "osd": "Problem", "line": problem_line},
        {"t": "10-20s","osd": "Tip", "line": tip_line},
        {"t": "20-30s","osd": "Example", "line": example_line},
        {"t": "30-40s","osd": "CTA", "line": cta_line}
    ]

    # combine style-based shot guidance with industry-specific suggestions
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

    style_shots = shot_map.get(style, ["Talking head + a few cutaways, end with CTA"])
    # add industry-specific shot hints to the start of the list where helpful
    industry_shots = []
    if industry_key == 'realtor':
        industry_shots = ["Start with exterior wide, show hero room, highlight value props"]
    elif industry_key == 'restaurant':
        industry_shots = ["Close-up of dish, plating, hands prepping"]
    elif industry_key == 'fitness':
        industry_shots = ["Full-body demo shot, side view for form"]
    elif industry_key == 'artisan':
        industry_shots = ["Hands-on process close-ups, product reveal"]

    shot_list = industry_shots + style_shots

    hashtags = default_hashtags(industry, brand_keywords + niche_keywords)
    thumb_prompt = f"Portrait thumbnail: {industry} • {style}. {mods.get('thumb_extra')}"

    # SRT prompt should include style, company and the beats for better auto-subtitle generation
    srt_context = f"Generate SRT subtitles for a 30-40s {style} reel about {pillar_name} in {industry}."
    if company: srt_context += f" Mention company: {company}."
    if goals: srt_context += f" Focus: {', '.join(goals[:3])}."

    return {
        "style": style,
        "hook": hook,
        "beats": beats,
        "script_beats": [b.get('line') if isinstance(b, dict) else b for b in beats],
        "shot_list": shot_list,
        "on_screen_text": [b.get('osd') for b in beats],
        "hashtags": hashtags,
        "cta": cta_line,
        "thumbnail_prompt": thumb_prompt,
        "srt_prompt": srt_context
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
                reel_obj = make_reel_plan(industry, pillar_name, brand_keywords, tone, company, reel_style, goals=goals, niche_keywords=niche_keywords)

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
