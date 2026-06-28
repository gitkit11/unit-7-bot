import requests
import random
import os
import io
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

BLUESKY_HANDLE = "logging-humans.bsky.social"
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

IMG_WIDTH = 1200
IMG_HEIGHT = 675
BG_COLOR = (0, 0, 0)
GREEN = (0, 255, 70)
DIM_GREEN = (0, 160, 40)

FIXED_TAG = "#UNIT7"
OPTIONAL_TAGS = [
    "#AI", "#humans", "#observation", "#AIhumor", "#tech",
    "#funny", "#robots", "#machinelearning", "#aiart", "#socialmedia"
]

TOPICS = [
    "humans and sleep",
    "humans and social media",
    "humans and work",
    "humans and food",
    "humans and money",
    "humans and emotions",
    "humans and relationships",
    "humans and exercise",
    "humans and productivity",
    "humans and weekends",
    "humans and phones",
    "humans and traffic",
    "humans and coffee",
    "humans and shopping",
    "humans and complaining",
    "humans and motivation",
    "humans and meetings",
    "humans and news",
    "humans and weather",
    "humans and birthdays",
]

SYSTEM_PROMPT = """You are UNIT-7, an AI that has been observing humans for years and logs everything you see.
You are not evil or mean — you are genuinely confused by human behavior.
You try to understand humans logically but their actions don't compute.

Your tone:
- Dry, deadpan, clinical
- Short sentences. Like a log entry.
- Occasionally add "I am still processing this." or "Logging for further analysis." or "No conclusion reached."
- Never use emojis
- Never be mean or offensive
- Always under 200 characters total

Write ONE single post (tweet-style) about the given topic.
Output only the post text, nothing else."""


def get_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_image(post_text, observation_num):
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    padding = 60

    header_font = get_font(28)
    main_font = get_font(46)
    footer_font = get_font(24)

    # Header
    header_text = f"UNIT-7 // OBSERVATION #{observation_num:03d}"
    draw.text((padding, padding), header_text, font=header_font, fill=DIM_GREEN)

    sep_y = padding + 50
    draw.line([(padding, sep_y), (IMG_WIDTH - padding, sep_y)], fill=DIM_GREEN, width=1)

    # Main text (centered vertically)
    max_width = IMG_WIDTH - padding * 2
    lines = wrap_text(draw, post_text, main_font, max_width)

    lh_bbox = draw.textbbox((0, 0), "Ag", font=main_font)
    line_height = (lh_bbox[3] - lh_bbox[1]) + 16

    total_h = len(lines) * line_height
    text_y = (IMG_HEIGHT - total_h) // 2

    for i, line in enumerate(lines):
        draw.text((padding, text_y + i * line_height), line, font=main_font, fill=GREEN)

    # Footer
    footer_sep_y = IMG_HEIGHT - padding - 40
    draw.line([(padding, footer_sep_y), (IMG_WIDTH - padding, footer_sep_y)], fill=DIM_GREEN, width=1)
    draw.text((padding, footer_sep_y + 8), "logging-humans.bsky.social", font=footer_font, fill=DIM_GREEN)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf.read()


def build_post_text(generated_text):
    tags = [FIXED_TAG] + random.sample(OPTIONAL_TAGS, k=random.randint(2, 3))
    return f"{generated_text}\n\n{' '.join(tags)}"


def generate_post(topic):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Topic: {topic}"}
        ],
        "temperature": 0.9,
        "max_tokens": 100
    }
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    if "choices" not in data:
        print(f"❌ Groq error: {data}")
        raise Exception(f"Groq API error: {data}")
    return data["choices"][0]["message"]["content"].strip()


def login_bluesky():
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    resp = requests.post(url, json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_APP_PASSWORD})
    data = resp.json()
    return data["accessJwt"], data["did"]


def upload_image(token, image_bytes):
    url = "https://bsky.social/xrpc/com.atproto.repo.uploadBlob"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "image/jpeg"
    }
    resp = requests.post(url, headers=headers, data=image_bytes)
    return resp.json()["blob"]


def post_to_bluesky(token, did, text, blob_ref):
    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "embed": {
                "$type": "app.bsky.embed.images",
                "images": [{
                    "image": blob_ref,
                    "alt": "UNIT-7 observation log entry"
                }]
            }
        }
    }
    resp = requests.post(url, json=payload, headers=headers)
    return resp.json()


def main():
    print(f"🤖 UNIT-7 starting... {datetime.now()}")

    topic = random.choice(TOPICS)
    print(f"📝 Topic: {topic}")

    observation_num = random.randint(1, 999)
    print(f"🔢 Observation #{observation_num}")

    generated_text = generate_post(topic)
    print(f"✍️ Generated: {generated_text}")

    post_text = build_post_text(generated_text)
    print(f"📎 Full post:\n{post_text}")

    image_bytes = generate_image(generated_text, observation_num)
    print(f"🖼️ Image generated ({len(image_bytes)} bytes)")

    token, did = login_bluesky()
    print("✅ Logged in to Bluesky")

    blob_ref = upload_image(token, image_bytes)
    print("📤 Image uploaded")

    result = post_to_bluesky(token, did, post_text, blob_ref)
    print(f"🚀 Posted! URI: {result.get('uri', 'unknown')}")


if __name__ == "__main__":
    main()
