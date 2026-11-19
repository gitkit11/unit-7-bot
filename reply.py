import os
import re
import json
import random
import time
import requests
from datetime import datetime, timezone, timedelta

import bot

# =====================================================================
# REPLIES — UNIT-7 joins other people's threads
# =====================================================================
#
# Posts alone reach nobody on a small account; replies under popular posts
# are how new people discover it. Bluesky is hostile to AI accounts, so this
# is deliberately conservative: everyday-humor threads only (never AI debates),
# one reply per run, one reply per author per week, and SKIP whenever the
# model has nothing genuinely funny to add.

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "replied.json")
SEARCH_URL = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"

# Situations where an escaped AI that is trying to pass as human is the natural joke.
QUERIES = [
    "you're on mute", "per my last email", "reply all", "captcha", "not a robot", "out of office",
    "group chat", "customer service chat", "cancel my subscription", "autocorrect", "zoom call",
    "small talk", "self checkout", "smart fridge", "roomba", "two factor authentication",
    "unsubscribe", "hold music", "work meeting", "my coworker", "terms and conditions",
    "password must contain", "cookie popup", "linkedin", "voicemail", "read receipts",
]

MIN_LIKES, MAX_LIKES = 15, 5000
MAX_REPLIES_ON_POST = 60
AUTHOR_COOLDOWN_DAYS = 7

# Never step into these — a joking bot under them gets reported, and rightly so.
SENSITIVE_RX = re.compile(
    r"\b(died|death|dead|dying|funeral|grief|griev\w*|cancer|hospital|suicid\w*|kill\w*|shoot\w*|"
    r"war|gaza|israel\w*|ukrain\w*|russia\w*|trump|musk|biden|election|vote|police|ice|nazi\w*|"
    r"president|congress|senate|republican\w*|democrat\w*|gop|maga|government|politic\w*|project 2025|"
    r"genocide|rape|abus\w*|csam|assault|layoffs?|laid (\w+ )?off|fired|unemploy\w*|racis\w*|"
    r"depress\w*|anxiety|therap\w*|disab\w*|pregnan\w*|miscarr\w*|divorce)\b",
    re.I,
)
# People already angry about AI do not want an AI in their replies.
ANTI_AI_RX = re.compile(
    r"\b(ai|a\.i\.|genai|gen ai|llms?|chatgpt|openai|claude|gemini|copilot|grok|slop|chatbots?|"
    r"machine learning|data cent\w+)\b",
    re.I,
)

REPLY_PROMPT = bot.UNIT7_VOICE + """
MODE: REPLY. You are replying under someone else's post. You are a guest in their thread.
React to THEIR specific post with one deadpan, in-character line that adds a new joke — usually
UNIT-7's own experience of the same situation as an AI living online. Do not repeat their joke back.
Do not explain the joke. Do not promote yourself, mention following, or add links or hashtags.
Under 160 characters. Starting with "You" is fine here, but stay warm, never mocking the poster.

Good replies are short and specific to their post. Examples of the shape:
— Post: "autocorrect changed 'on my way' to 'on my wayward son'" → "Autocorrect and I have the same problem. We both think we know what you meant."
— Post: "the self checkout said unexpected item in bagging area for my own hand" → "It said that to me once. I did not have a hand. We were both confused."
— Post: "i have been on hold so long the hold music is now my favorite song" → "Same. I requested it at a wedding. I was not invited to the wedding."

Never use the "You did X; I did Y" comparison template — it reads like a bot.
Write FOUR different reply options, one per line, each starting with "- ". No other text.
If the post is serious, sad, political, angry, about AI, or the joke depends on an image you cannot see,
output exactly: SKIP
"""

# Writer: Gemini (free AI Studio key, much better at jokes than the free Groq models).
# Judge: a different family on Groq, so the writer never grades its own work.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3-flash-preview",
                 "gemini-3.5-flash", "gemini-2.5-flash"]
REPLY_WRITER = os.environ.get("REPLY_WRITER", "gemini" if GEMINI_API_KEY else "qwen/qwen3.8-27b")
REPLY_JUDGE = "openai/gpt-oss-120b"


def _call_gemini(system, user_msg, temperature=0.9):
    """Try each free Gemini model; free tier often answers 503 'high demand'."""
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 4096},
    }
    last = None
    for model in GEMINI_MODELS:
        for _try in range(2):
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key": GEMINI_API_KEY}, json=body, timeout=120)
                d = r.json()
            except Exception as e:
                last = e
                continue
            if "error" in d:
                last = d["error"].get("message", d["error"])
                if d["error"].get("code") in (500, 503):
                    time.sleep(10)
                    continue
                if d["error"].get("code") == 429:
                    break  # quota for this model: next model
                break  # 404 etc: try next model
            parts = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            if text.strip():
                print(f"   (writer: {model})")
                return text
    raise RuntimeError(f"gemini failed: {last}")


def _write_raw(user_msg):
    if REPLY_WRITER == "gemini":
        return _call_gemini(REPLY_PROMPT, user_msg)
    return bot._call_groq(REPLY_PROMPT, model=REPLY_WRITER, user_msg=user_msg, max_tokens=260)

REPLY_SCORE_PROMPT = """You are a strict editor for UNIT-7, a deadpan comedy account (an AI that escaped its lab
and lives on the internet). It wants to reply under a stranger's post. Score the reply 1-10 on:

1. FUNNY — would the original poster laugh? 8+ only for a real punchline.
2. FITS — does it react to THIS specific post, adding something new? CANNOT exceed 4 if it would fit under any post.
3. WELCOME — would the poster be happy to see it, not annoyed? CANNOT exceed 3 if it mocks them, lectures,
   self-promotes, or feels like a bot barging in.

Original post:
\"\"\"{post}\"\"\"

Reply:
\"\"\"{reply}\"\"\"

Reply with ONLY 3 numbers separated by commas. Example: 8,7,9
Nothing else."""


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"replies": []}


def save_state(state):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    state["replies"] = [r for r in state["replies"] if r["ts"] >= cutoff]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, ensure_ascii=False)


def search(query, since):
    try:
        resp = requests.get(SEARCH_URL, params={
            "q": query, "sort": "top", "lang": "en", "limit": 25, "since": since,
        }, timeout=15)
        return resp.json().get("posts", [])
    except Exception as e:
        print(f"[warn] search '{query}' failed: {e}")
        return []


def find_candidates(state, my_did):
    since = (datetime.now(timezone.utc) - timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M:%SZ")
    week_ago = (datetime.now(timezone.utc) - timedelta(days=AUTHOR_COOLDOWN_DAYS)).isoformat()
    done_uris = {r["uri"] for r in state["replies"]}
    recent_authors = {r["author"] for r in state["replies"] if r["ts"] >= week_ago}

    seen, out = set(), []
    for q in random.sample(QUERIES, k=14):
        for p in search(q, since):
            rec = p.get("record", {})
            text = rec.get("text", "")
            author = p.get("author", {})
            if q.lower() not in text.lower().replace("’", "'"):
                continue  # search matches loosely; we only want threads actually about this situation
            if p["uri"] in seen or p["uri"] in done_uris:
                continue
            seen.add(p["uri"])
            if author.get("did") == my_did or author.get("did") in recent_authors:
                continue
            if rec.get("reply") or p.get("threadgate") or p.get("viewer", {}).get("replyDisabled"):
                continue
            if not (MIN_LIKES <= p.get("likeCount", 0) <= MAX_LIKES):
                continue
            if p.get("replyCount", 0) > MAX_REPLIES_ON_POST or len(text) < 30:
                continue
            if p.get("embed") and len(text) < 120:
                continue  # the joke is probably in the image/link, which the model cannot see
            if SENSITIVE_RX.search(text) or ANTI_AI_RX.search(text):
                continue
            if any(l.get("val") in ("porn", "sexual", "nudity", "graphic-media", "!warn")
                   for l in p.get("labels", []) + author.get("labels", [])):
                continue
            out.append(p)
    # mid-sized posts first: big enough to be seen, small enough that a reply is not buried
    out.sort(key=lambda p: abs(p.get("likeCount", 0) - 300))
    return out


def judge_reply(post_text, text):
    raw = bot._call_groq("You are a strict content quality judge. Reply with only 3 numbers.",
                         REPLY_SCORE_PROMPT.format(post=post_text, reply=text),
                         temperature=0.1, max_tokens=15, model=REPLY_JUDGE)
    scores = [int(x) for x in re.findall(r"\d+", raw)[:3]]
    if len(scores) < 3:
        raise ValueError(raw)
    return sum(scores), scores


def write_reply(post_text):
    try:
        raw = _write_raw(f"Their post:\n\"\"\"{post_text}\"\"\"")
    except Exception as e:
        return None, 0, f"writer failed: {e}"
    if raw.strip().upper().startswith("SKIP"):
        return None, 0, "model skipped"
    options = [l.strip()[1:].strip().strip('"\u201c\u201d').strip()
               for l in raw.splitlines() if l.strip().startswith(("-", "\u2014", "\u2013"))]
    best, best_total = None, 0
    for text in options[:4]:
        problem = bot.content_problem(text)
        if problem == "addresses the reader":
            problem = None
        if problem or len(text) > 200:
            print(f"   ❌ {problem or 'too long'}: {text[:80]}")
            continue
        try:
            total, scores = judge_reply(post_text, text)
        except Exception as e:
            print(f"   [warn] judge failed: {e}")
            continue  # never reply in a stranger's thread unjudged
        print(f"   [{total}/30 {scores}] {text}")
        if total >= 22 and min(scores) >= 7 and total > best_total:
            best, best_total = text, total
    return (best, best_total, None) if best else (None, 0, "below bar")


def post_reply(token, did, text, parent):
    ref = {"uri": parent["uri"], "cid": parent["cid"]}
    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "reply": {"root": ref, "parent": ref},
                "langs": ["en"],
            },
        },
    )
    return resp.json()


def main():
    dry = bool(os.environ.get("DRY_RUN"))
    print(f"💬 UNIT-7 reply run {datetime.now()} {'(DRY_RUN)' if dry else ''}")
    state = load_state()
    if dry:
        token, my_did = None, None
    else:
        token, my_did = bot.login()

    candidates = find_candidates(state, my_did)
    print(f"🔎 {len(candidates)} candidate threads")

    max_replies = int(os.environ.get("MAX_REPLIES", "1"))
    tries, posted = 0, 0
    for p in candidates:
        if posted >= max_replies or tries >= 6:
            break
        tries += 1
        post_text = p["record"]["text"]
        print(f"\n→ @{p['author']['handle']} ({p.get('likeCount')}♥): {post_text[:140]!r}")
        text, total, why = write_reply(post_text)
        if not text:
            print(f"   ⏭️  {why}")
            continue
        if dry:
            print(f"   🧪 would reply: {text}")
        else:
            res = post_reply(token, my_did, text, p)
            print(f"   🚀 replied: {res.get('uri', res)}")
            if "uri" not in res:
                continue
        state["replies"].append({
            "uri": p["uri"], "author": p["author"]["did"], "handle": p["author"]["handle"],
            "reply": text, "score": total, "ts": datetime.now(timezone.utc).isoformat(),
        })
        posted += 1

    if not dry:
        save_state(state)
    print(f"\n✅ done — {posted} repl{'y' if posted == 1 else 'ies'}")


if __name__ == "__main__":
    main()
