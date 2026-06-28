import requests
import random
import os
from datetime import datetime, timezone

# === НАСТРОЙКИ ===
BLUESKY_HANDLE = "logging-humans.bsky.social"
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# === ТЕМЫ ДЛЯ ПОСТОВ ===
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
- Always under 280 characters total

Write ONE single post (tweet-style) about the given topic.
Output only the post text, nothing else."""

def generate_post(topic):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": f"{SYSTEM_PROMPT}\n\nTopic: {topic}"
            }]
        }],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 100
        }
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    # Показываем полный ответ если ошибка
    if "candidates" not in data:
        print(f"❌ Gemini error: {data}")
        raise Exception(f"Gemini API error: {data}")
    
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    return text

def login_bluesky():
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {
        "identifier": BLUESKY_HANDLE,
        "password": BLUESKY_APP_PASSWORD
    }
    response = requests.post(url, json=payload)
    data = response.json()
    return data["accessJwt"], data["did"]

def post_to_bluesky(token, did, text):
    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": {
            "text": text,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def main():
    print(f"🤖 UNIT-7 starting... {datetime.now()}")
    
    topic = random.choice(TOPICS)
    print(f"📝 Topic: {topic}")
    
    post_text = generate_post(topic)
    print(f"✍️ Generated: {post_text}")
    
    token, did = login_bluesky()
    print("✅ Logged in to Bluesky")
    
    result = post_to_bluesky(token, did, post_text)
    print(f"🚀 Posted! URI: {result.get('uri', 'unknown')}")

if __name__ == "__main__":
    main()
