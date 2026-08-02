from dataclasses import dataclass

DEFAULT_NEGATIVE_PROMPT = (
    "blurry, distorted, extra limbs, extra fingers, mutated hands, disfigured, "
    "low quality, worst quality, watermark, text, logo, deformed face, bad anatomy"
)


@dataclass(frozen=True)
class Style:
    id: str
    label: str
    emoji: str
    prompt: str
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT
    strength: float = 0.65
    guidance_scale: float = 7.0


STYLES = [
    Style(
        id="royal",
        label="Royal Portrait",
        emoji="\U0001F451",
        prompt=(
            "a majestic royal portrait painting of the person, ornate golden crown, "
            "luxurious velvet robes, renaissance oil painting style, dramatic lighting, "
            "highly detailed, museum quality"
        ),
    ),
    Style(
        id="cyberpunk",
        label="Cyberpunk",
        emoji="\U0001F306",
        prompt=(
            "cyberpunk portrait of the person, neon lights, futuristic city background, "
            "glowing highlights, cinematic, highly detailed digital art"
        ),
    ),
    Style(
        id="anime",
        label="Anime Hero",
        emoji="⚔️",
        prompt=(
            "anime style portrait of the person, vibrant colors, dynamic hero pose, "
            "studio ghibli inspired, highly detailed illustration"
        ),
    ),
    Style(
        id="watercolor",
        label="Watercolor",
        emoji="\U0001F3A8",
        prompt=(
            "soft watercolor painting portrait of the person, pastel colors, "
            "delicate brush strokes, artistic, gentle lighting"
        ),
    ),
    Style(
        id="astronaut",
        label="Space Explorer",
        emoji="\U0001F680",
        prompt=(
            "portrait of the person as an astronaut, detailed space suit, stars and "
            "galaxy background, cinematic lighting, highly detailed"
        ),
    ),
    Style(
        id="noir",
        label="Film Noir",
        emoji="\U0001F3AC",
        prompt=(
            "black and white film noir portrait of the person, dramatic shadows, "
            "vintage 1940s style, moody cinematic lighting"
        ),
    ),
]

_STYLES_BY_ID = {style.id: style for style in STYLES}


def get_style(style_id: str) -> Style:
    if style_id not in _STYLES_BY_ID:
        raise ValueError(f"Unknown style id: {style_id}")
    return _STYLES_BY_ID[style_id]
