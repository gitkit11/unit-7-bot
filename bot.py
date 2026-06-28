import requests
import random
import os
from datetime import datetime, timezone

# === НАСТРОЙКИ ===
BLUESKY_HANDLE = "logging-humans.bsky.social"
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

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
- Always under 280 characters total

Write ONE single post (tweet-style) about the given topic.
Output only the post text, nothing else."""

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

    text = data["choices"][0]["message"]["content"].strip()
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
