from datetime import date, timedelta

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
                 platform: str, brand_keywords: list[str], hashtags: list[str], goals: list[str]):
    tone_blurb = {
        "friendly": "Warm, encouraging, and conversational.",
        "professional": "Clear, confident, and value-focused.",
        "playful": "Upbeat, witty, and a bit cheeky.",
        "inspirational": "Uplifting, thoughtful, and mission-driven."
    }.get(tone.lower(), "Conversational and helpful.")

    platform_hint = PLATFORM_HINTS.get(platform.lower(), "Make it concise and useful.")
    brand_line = f" ({', '.join(brand_keywords)})" if brand_keywords else ""
    goal_line = f"Focus: {', '.join(goals)}." if goals else ""

    body = (
        f"{pillar_name} • {industry}{brand_line}\n"
        f"{pillar_hint}\n\n"
        f"{goal_line}\n"
        f"Tone: {tone_blurb}\n"
        f"Platform tip: {platform_hint}\n\n"
        f"CTA: Tell us what you think below 👇"
    )

    tags = " ".join(hashtags)
    return f"{body}\n\n{tags}"

def image_prompt(industry: str, pillar_name: str, brand_keywords: list[str]):
    kw = ", ".join(brand_keywords) if brand_keywords else "on-brand colors"
    return (f"High-quality photo for social post. Industry: {industry}. "
            f"Content pillar: {pillar_name}. Style: natural light, minimal background, {kw}.")

def unsplash_link(industry: str, pillar_name: str):
    q = f"{industry} {pillar_name}".replace(" ", "+")
    return f"https://source.unsplash.com/featured/?{q}"

def rolling_pillars():
    while True:
        for name, hint in PILLARS_BY_DEFAULT:
            yield (name, hint)

def generate_posts(days: int, start_day, industry: str, tone: str,
                   platforms: list[str], brand_keywords: list[str],
                   include_images: bool, niche_keywords: list[str], goals: list[str]):
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
                goals=goals
            )
            iprompt = image_prompt(industry, pillar_name, brand_keywords)
            img_url = unsplash_link(industry, pillar_name) if include_images else None

            posts.append({
                "date": day.isoformat(),
                "day_index": i + 1,
                "platform": p,
                "pillar": pillar_name,
                "caption": caption,
                "image_prompt": iprompt,
                "image_url": img_url
            })
    return posts
