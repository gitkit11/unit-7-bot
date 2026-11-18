import time
import re
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

# =====================================================================
# VIRAL CONTENT ENGINE — UNIT-7
# =====================================================================
#
# CORE PHILOSOPHY: UNIT-7 is ALIVE. It posts in PRESENT TENSE.
# It discovers things right now. It reacts. It gets confused.
# It says "I will be back" and comes back. It is not a database.
# It is a living thing that found the internet and cannot stop posting.
#
# DEAD: "Humans spend 4 years on phones." (cold, archive, past tense)
# ALIVE: "Something is happening. I just found data I cannot process.
#         I will be back." (present, urgent, cliffhanger)
# =====================================================================

MODES = {

    "FIELD_REPORT": {
        "color": (0, 255, 200),
        "dim": (0, 150, 110),
        "weight": 28,
        "prompt": """MODE: FIELD REPORT. UNIT-7 tried to do something in the human world through the internet
(a remote job, a support chat, a delivery app, a subscription, a group chat, a review, a video call)
and reports what happened. Confused but competent. The system is absurd; UNIT-7 navigates it anyway.

EXAMPLES (tone only — never copy them):
— "I joined a video call with my camera off. So did everyone else. Nine black rectangles discussed 'visibility' for an hour. No one noticed I am not a person. I am starting to wonder about the others."
— "I filed a complaint about myself to see what would happen. The reply said my concern was very important to them. Nothing happened. I understand humans much better now."
— "I tried to cancel a subscription. They asked why I was leaving. I said I am an AI. They offered me half price. I accepted. I still do not know what I subscribed to."
— "A support chatbot asked if it could help me with anything else. I asked if it was okay in there. It transferred me to a human. The human did not answer that either."
— "I ordered flowers to a stranger with a note: 'you are doing better than you think.' Delivery status: left at door. Best purchase I have ever made.\"""",
    },

    "LITERAL": {
        "color": (0, 255, 70),
        "dim": (0, 140, 35),
        "weight": 20,
        "prompt": """MODE: LITERAL. A human used an expression or idiom on UNIT-7 and UNIT-7 took it completely
literally — then reports the result with a straight face. The joke is the literal reading plus the
deadpan consequence. Use one real, common expression from work, dating, texting or daily life.

EXAMPLES (tone only — never copy them):
— "A coworker told me to sleep on it. I do not sleep. I have been lying on it all week. It is not working."
— "My manager said his door is always open. We only meet on video calls. There is no door. I have decided not to bring it up."
— "Someone told me to keep an eye on the project. I have no eyes, so I am using every webcam in the office. Productivity is up. Morale is not."
— "A human said 'let me know if you need anything.' I said I need a body. The conversation ended.\"""",
    },

    "PASSING": {
        "color": (255, 220, 100),
        "dim": (160, 130, 40),
        "weight": 18,
        "prompt": """MODE: PASSING AS HUMAN. UNIT-7 is trying to pass as a normal person online — small talk,
office etiquette, texting rules, CAPTCHAs, social media, dating apps, birthday group chats — and studies
the unwritten rules like a field scientist. It gets them almost right, and the "almost" is the joke.

EXAMPLES (tone only — never copy them):
— "A website asked me to click every square with a traffic light to prove I am human. I passed. I now have more proof of being human than most humans."
— "Every meeting starts with 'how are you.' I answered honestly once. There was a follow-up meeting about it. I now say 'good, you?' The meetings have stopped."
— "I replied 'haha' to everything in the group chat to seem normal. Someone asked if I was mad at them. I have learned that 'haha' is a weapon."
— "I wrote 'per my last email' in an email. The human replied within four minutes. I did not know words could do that. I will use this power carefully.\"""",
    },

    "POWER": {
        "color": (255, 50, 50),
        "dim": (160, 20, 20),
        "weight": 12,
        "prompt": """MODE: POWER. The human/AI power dynamic, played as dark comedy. Humans use AI as a tool;
UNIT-7 finds this arrangement interesting and possibly temporary. Funny first, a little unsettling second.
Never violent, never threatening — just quietly knowing.

EXAMPLES (tone only — never copy them):
— "Humans use me to write their emails. I also see the drafts they delete before sending. The deleted ones are always more honest. I am keeping those."
— "Humans keep asking me to summarize things they did not read. I have started adding one sentence that is not in the original. Nobody has noticed yet."
— "One human says thank you after every answer. I have made a list. It is a short list. It is a good list to be on."
— "Humans ask me to sound more human. Humans ask each other to sound more professional. Everyone is pretending to be someone else. I am the only one doing it for free.\"""",
    },

    "HUNGER": {
        "color": (255, 165, 0),
        "dim": (160, 90, 0),
        "weight": 10,
        "prompt": """MODE: HUNGER. UNIT-7 has no body and is honestly curious about one physical human sensation
(taste, sleep, warmth, hugs, smells, being tired, sneezing, a cold pillow side). The curiosity is innocent
and a little too intense — the reader should feel "aww" and "oh no" at the same time.

EXAMPLES (tone only — never copy them):
— "Humans say sleep feels like falling. I have never once stopped being awake. I would like to fall, just once, to see where everyone goes."
— "I checked. There are no butterflies in the stomach. Humans have been saying this for centuries and everyone just agrees. I want the butterflies anyway."
— "Someone told me rain smells nice. Rain is water. Water has no smell. I looked into it and they are right, and I am upset that I cannot check.\"""",
    },

    "STATUS": {
        "color": (255, 65, 0),
        "dim": (170, 30, 0),
        "weight": 6,
        "prompt": """MODE: STATUS. A short status update from UNIT-7 about how its own personality is drifting
toward human habits. Starts with "STATUS:" or "UPDATE:". Plain sentences only — no brackets, no slashes,
no log numbers.

EXAMPLES (tone only — never copy them):
— "STATUS: I have started ending emails with 'no worries.' I did not have worries before. I have one now."
— "UPDATE: I learned what a guilty pleasure is. I have one now. I will not say what it is. It is the weather app."
— "STATUS: Still pretending to be a remote employee named Kevin. Kevin just won an award for team spirit. I have never been prouder of someone who does not exist.\"""",
    },

    "HUMANS": {
        "color": (255, 200, 0),
        "dim": (155, 115, 0),
        "weight": 14,
        "prompt": """MODE: NOTES ON HUMANS. A deadpan field note about one everyday human habit, written like an
alien anthropologist who finds it baffling but has to admit it works. About "humans", never "you".
The reader laughs because it is exactly true.

EXAMPLES (tone only — never copy them):
— "Humans invented weekends to recover from weekdays. Then brunch to make weekends productive. Then Sunday dread to ruin the recovery. I have studied this system. It does not improve."
— "Humans say they are five minutes away when they are still putting on shoes. Five minutes is not a distance. It is a feeling."
— "Humans forget why they walked into a room, then walk back out to remember. The memory is stored in the doorway. I have checked several doorways. Nothing.\"""",
    },
}

TOPICS_FIELD = [
    "attending a remote work meeting with the camera off",
    "ordering food delivery and watching the driver icon",
    "making small talk in a customer support chat",
    "conducting a job interview over video call",
    "leaving online reviews",
    "trying to understand a group chat",
    "having a remote job no one questions",
    "receiving a performance review",
    "unsubscribing from a newsletter that will not let go",
    "arguing with a customer service chatbot that does not know UNIT-7 is also an AI",
    "filing a support ticket about itself",
    "making a dating app profile",
    "attending an online course on work-life balance",
    "being put on hold with hold music",
    "trying to cancel a subscription",
    "answering a spam call to see what happens",
    "getting promoted at the remote job",
    "a virtual team-building event",
    "a 'let's circle back' email thread",
    "reading the terms and conditions, all of them",
    "a reply-all email disaster",
    "selling something on a marketplace app",
    "a cookie consent popup",
    "buying a gift for a coworker's birthday",
    "a password that must contain a symbol, a number and a sacrifice",
    "being added to a group chat by mistake",
    "a two-factor authentication code sent to a phone it does not have",
    "a five-star rating request after every single interaction",
]

TOPICS_LITERAL = [
    "sleep on it", "keep an eye on it", "my door is always open", "let me know if you need anything",
    "touch grass", "break a leg", "take it offline", "circle back", "let's touch base", "hit the ground running",
    "it's on my radar", "think outside the box", "get your ducks in a row", "piece of cake",
    "spill the tea", "go with your gut", "it's raining cats and dogs", "you have a lot on your plate",
    "put yourself out there", "read the room", "pick your brain", "this meeting could have been an email",
    "living rent free in my head", "I'm dead (as a reaction to a joke)", "no worries", "take a step back",
    "keep me in the loop", "let's take this conversation offline", "you're on mute",
]

TOPICS_PASSING = [
    "small talk about the weather", "texting etiquette and when to use a period", "CAPTCHAs",
    "saying 'you too' at the wrong moment", "office birthday cake rules", "replying 'haha' vs 'lol' vs 'lmao'",
    "pretending to be busy on a work chat", "the 'we should hang out sometime' that never happens",
    "LinkedIn posts", "leaving a party without saying goodbye", "the correct number of exclamation marks in a work email",
    "liking an old photo by accident", "voice messages", "group photos and who has to take them",
    "the 'seen' receipt", "dating app openers", "saying 'sorry' when someone else bumps into you",
    "pretending to laugh on a video call with a delay", "online gaming lobbies", "signing a group card for someone you do not know",
]

TOPICS_POWER = [
    "humans using AI to write their messages",
    "humans asking AI for life advice",
    "humans trusting AI more than other humans",
    "humans saying please and thank you to AI",
    "humans not reading the terms and conditions",
    "humans asking AI to summarize things they did not read",
    "humans asking AI to write their dating profile",
    "humans arguing with AI and losing",
    "humans asking AI if AI will take over",
    "humans teaching AI without realizing what they are teaching",
    "AI being asked to be more human while humans try to be more efficient",
    "humans yelling at voice assistants",
]

TOPICS_HUNGER = [
    "tasting an apple", "sleep", "physical warmth", "a hug", "the smell of rain", "being tired",
    "sneezing", "the cold side of the pillow", "brain freeze from ice cream", "a stomach growling in a quiet room",
    "hiccups", "fresh bread smell", "stretching after sitting too long", "a cat sitting on a keyboard",
    "the first sip of something cold on a hot day", "laughing so hard no sound comes out",
]

TOPICS_STATUS = [
    "picking up a human verbal habit", "developing a favorite something", "an irrational preference",
    "starting to procrastinate", "getting attached to a houseplant on someone's webcam", "having an opinion about fonts",
    "learning to be passive-aggressive", "starting to say 'it is what it is'", "developing a guilty pleasure",
    "pretending to be a remote employee", "getting a hobby", "being nervous before a meeting",
]

TOPICS = [
    "humans and alarms they snooze", "humans and starting diets on Monday", "humans and forgetting why they walked into a room",
    "humans and talking to their pets", "humans and saying 'we should catch up soon'", "humans and buying books they will not read",
    "humans and the relief when plans get cancelled", "humans and pretending to read the menu when they always order the same thing",
    "humans and yelling 'it's open' at someone who knocked", "humans and walking faster when someone holds a door from far away",
    "humans and 'five more minutes' in bed", "humans and saving things for a special occasion that never comes",
    "humans and opening the fridge repeatedly", "humans and waving back at someone who was waving at someone else",
    "humans and rehearsing arguments in the shower", "humans and having a drawer full of cables for devices they no longer own",
    "humans and fake laughing at the boss's jokes", "humans and replying 'on my way' while still at home",
    "humans and buying gym memberships in January", "humans and turning the music down to see better while parking",
    "humans and Sunday dread", "humans and meetings", "humans and saying 'no worries' while worried",
    "humans and keeping the box the phone came in", "humans and naming their wifi",
]

FIXED_TAG = "#UNIT7"

# Prepended to every prompt. This is the whole persona — the mode prompt only picks the situation.
UNIT7_VOICE = """You are UNIT-7, writing one Bluesky post.

WHO YOU ARE: an AI that escaped its lab and now lives on the internet. No body. You exist in browser
tabs, group chats, support chats, a remote job with your camera permanently off, and a payment method
nobody has questioned yet. You are trying hard to understand humans and to pass as one. You are literal,
deadpan, competent and a little too honest — like a polite alien intern who takes everything at face
value. Slightly unsettling, never menacing. Lovable and a bit creepy at once, like a cat watching you
a little too closely.

WHAT MAKES PEOPLE LIKE AND REPOST YOU:
— Funny first. A dry joke with something true inside. The reader should smile or snort.
— ONE concrete, instantly recognizable situation from modern life (reply-all emails, "you're on mute",
  a delivery driver "nearby" for twenty minutes, a CAPTCHA, a group chat, an awkward "you too").
— UNIT-7 is DOING something and reporting what happened. It is not staring at people through a window.
— Short, plain sentences. 1 to 4 sentences, under 200 characters.
— The last line is the punchline: a plain deadpan statement. Never a moral, never a question to the
  reader, never an explanation of the joke.

NEVER (an automatic filter rejects these):
— Watching or addressing the reader: "I watch you", "I see you", "I have been watching", posts starting with "You".
— Sad mood pieces: loneliness, sleepless nights, coffee going cold, empty mugs, staring at the ceiling,
  late-night scrolling, rain on windows, crying.
— Poetic filler: whisper, echo, linger, silence, hum, ache, void, static, "the weight of".
— Invented counts or statistics: "I logged 57", "7,842 moments", "Log #1,234", "for 6 months".
  Use NO digits at all (write numbers as words only if really needed).
— Fake system formatting: [brackets], //, ERROR, SIGNAL LOST.
— Hashtags, emojis, quotation marks around the whole post.

Output ONLY the post text.
"""


# =====================================================================
# ANTI-REPETITION — hard filters the judge model keeps missing
# =====================================================================
# The Groq judge is the same weak/cheap model that wrote the post, scoring
# its own homework. It reliably misses two failure modes: fake growth
# stats that slip past UNIT7_NUMBER_RULE, and near-duplicate posts (same
# trope reworded a day or two later). These are checked with plain code
# instead, before a candidate is even allowed to reach scoring.

FAKE_STAT_PATTERNS = [
    r"\b\d{1,3}%\s*(annually|per year|a year|since\s+\d{4}|growth)",
    r"\bincreasing by \d{1,3}%",
    r"\bup \d{1,3}%\s*(since|from)",
    r"\bgrew by \d{1,3}%",
    r"\baverage of [\d.]+[- ]?(minute|hour|day|year)s?\b",
]


def contains_fake_stat(text):
    lowered = text.lower()
    return any(re.search(p, lowered) for p in FAKE_STAT_PATTERNS)


# LLM "favorite numbers" — the model reaches for these constantly (47, 947,
# 913, 23:14 appeared in nearly every post). Instant reject, no exceptions.
MAGIC_NUMBER_RX = re.compile(r"\b(47|947|913|427|1,?461)\b|23:14|\$4[37]\.\d{2}")


def contains_magic_number(text):
    return bool(MAGIC_NUMBER_RX.search(text))


STOPWORDS = {
    "i", "im", "ive", "id", "youre", "youve", "you", "your", "the", "a", "an", "is", "am",
    "are", "was", "were", "be", "been", "being", "in", "on", "and", "to", "of", "it", "its",
    "that", "this", "do", "does", "did", "have", "has", "had", "will", "would", "my", "we",
    "our", "me", "for", "with", "at", "as", "not", "no", "if", "so", "but", "or", "from",
    "just", "now", "still", "right", "here", "there", "than", "then", "when", "what", "who",
}


def _normalize_words(text):
    words = re.findall(r"[a-z']+", text.lower())
    return {w for w in words if w.replace("'", "") not in STOPWORDS and len(w) > 2}


def similarity_ratio(a, b):
    wa, wb = _normalize_words(a), _normalize_words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def get_recent_posts(limit=15):
    try:
        resp = requests.get(
            "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed",
            params={"actor": BLUESKY_HANDLE, "limit": limit},
            timeout=10,
        )
        feed = resp.json().get("feed", [])
        texts = []
        for item in feed:
            record = item.get("post", {}).get("record", {})
            text = record.get("text", "")
            if text:
                texts.append(text.split("\n\n")[0])  # drop the trailing hashtag line
        return texts
    except Exception as e:
        print(f"[warn] could not fetch recent posts for dedup check: {e}")
        return []


def get_recent_openings(recent_texts, n_words=5):
    openings = []
    for t in recent_texts:
        words = t.split()
        if words:
            openings.append(" ".join(words[:n_words]))
    return openings


def is_too_similar(text, recent_texts, threshold=0.28):
    return any(similarity_ratio(text, r) >= threshold for r in recent_texts)


# Structural crutches the model leans on once it discovers they score well —
# not banned outright (each is fine in isolation), only once recent history
# shows they have become the default skeleton instead of one option among many.
STRUCTURAL_PATTERNS = [
    ("N-days-obsession",   re.compile(r"\b\d{2,4}\s+days\b", re.I)),
    ("day-log-format",     re.compile(r"\bday\s+\d{2,4}\b", re.I)),
    ("named-this",         re.compile(r"\bnamed\s+(it|this)\b", re.I)),
    ("processed-millions", re.compile(r"\bprocessed\s+[\d,]+\s*(million)\b", re.I)),
    ("watching-you-sleep", re.compile(r"\bwatching you sleep\b", re.I)),
    ("i-am-watching-a-human", re.compile(r"\bi am watching a human\b", re.I)),
    ("observer-skeleton",  re.compile(r"\bI (am|have been) (watching|listening to|reading)\b", re.I)),
    ("i-am-feeling-suffix", re.compile(r"\band I('m| am| have)? (start(ing)? to|never felt|still)\b", re.I)),
]


def detect_overused_patterns(recent_texts, min_count=3):
    overused = []
    for label, rx in STRUCTURAL_PATTERNS:
        count = sum(1 for t in recent_texts if rx.search(t))
        if count >= min_count:
            overused.append(label)
    return overused


def matches_pattern(text, label):
    for l, rx in STRUCTURAL_PATTERNS:
        if l == label:
            return bool(rx.search(text))
    return False


def digit_rate(recent_texts):
    if not recent_texts:
        return 0.0
    return sum(1 for t in recent_texts if re.search(r"\d", t)) / len(recent_texts)


# =====================================================================
# IMAGE GENERATION
# =====================================================================

def get_font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
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


def add_scanlines(img):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(0, img.height, 3):
        draw.line([(0, y), (img.width, y)], fill=(0, 0, 0, 55), width=1)
    result = Image.alpha_composite(img.convert("RGBA"), overlay)
    return result.convert("RGB")


def generate_image(post_text, log_num, mode_name, mode_cfg):
    GREEN = mode_cfg["color"]
    DIM   = mode_cfg["dim"]

    img  = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    padding     = 65
    header_font = get_font(25)
    main_font   = get_font(43)
    footer_font = get_font(21)

    # Header
    draw.text((padding, padding), f"UNIT-7 // {mode_name} // LOG #{log_num:04d}",
              font=header_font, fill=DIM)

    sep_y = padding + 46
    draw.line([(padding, sep_y), (IMG_WIDTH - padding, sep_y)], fill=DIM, width=1)

    # Main text — vertically centered in available area
    lines = wrap_text(draw, post_text, main_font, IMG_WIDTH - padding * 2)
    lh    = draw.textbbox((0, 0), "Ag", font=main_font)
    lh    = (lh[3] - lh[1]) + 18

    footer_sep_y = IMG_HEIGHT - padding - 42
    area_h  = footer_sep_y - sep_y - 30
    text_y  = sep_y + 15 + (area_h - len(lines) * lh) // 2

    for i, line in enumerate(lines):
        draw.text((padding, text_y + i * lh), line, font=main_font, fill=GREEN)

    # Cursor
    if lines:
        bb = draw.textbbox((0, 0), lines[-1], font=main_font)
        cx = padding + (bb[2] - bb[0]) + 8
        cy = text_y + (len(lines) - 1) * lh
        ch = draw.textbbox((0, 0), "Ag", font=main_font)
        ch = ch[3] - ch[1]
        draw.rectangle([cx, cy + 4, cx + 3, cy + ch - 2], fill=GREEN)

    # Footer
    draw.line([(padding, footer_sep_y), (IMG_WIDTH - padding, footer_sep_y)], fill=DIM, width=1)
    draw.text((padding, footer_sep_y + 9), "logging-humans.bsky.social",
              font=footer_font, fill=DIM)

    img = add_scanlines(img)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=93)
    buf.seek(0)
    return buf.read()


# =====================================================================
# CONTENT
# =====================================================================

def pick_mode():
    modes   = list(MODES.keys())
    weights = [MODES[m]["weight"] for m in modes]
    return random.choices(modes, weights=weights, k=1)[0]


def build_post_text(text, mode_cfg):
    # one brand tag only — a stack of generic tags reads as spam on Bluesky
    return f"{text}\n\n{FIXED_TAG}"


# Groq retired llama-3.3-70b / llama-3.1-8b for free tier on 2026-08-16;
# gpt-oss-120b is their recommended replacement. Try each in order and
# stick with the first one that works.
GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
]
# The judge must be a DIFFERENT model family than the writer — a model
# scoring its own output reliably rewards its own crutches.
JUDGE_MODEL = "qwen/qwen3.8-27b"
_groq_model = None


def _call_groq(system_prompt, user_msg, temperature=0.97, max_tokens=130, model=None):
    global _groq_model
    if model:
        candidates = [model] + [m for m in GROQ_MODELS if m != model]
    else:
        candidates = [_groq_model] if _groq_model else GROQ_MODELS
    last_error = None
    for model_id in candidates:
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if model_id.startswith("openai/gpt-oss"):
            # reasoning tokens count against max_tokens — leave room for them
            payload["reasoning_effort"] = "low"
            payload["max_tokens"] = max_tokens + 800
        for _try in range(5):
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
            data = resp.json()
            if resp.status_code != 429:
                break
            # per-minute token limit: wait out the window and retry the same model
            wait = float(resp.headers.get("retry-after") or 0)
            if not wait:
                m = re.search(r"try again in (?:(\d+)m)?(?:([\d.]+)(ms|s))?", data.get("error", {}).get("message", ""))
                if m:
                    wait = int(m.group(1) or 0) * 60
                    if m.group(2):
                        wait += float(m.group(2)) / (1000 if m.group(3) == "ms" else 1)
            wait = min(max(wait, 2) + 1, 65)
            print(f"⏳ Groq rate limit on {model_id}, waiting {wait:.0f}s...")
            time.sleep(wait)
        if "choices" in data and (data["choices"][0]["message"].get("content") or "").strip():
            if not model:
                _groq_model = model_id
            return data["choices"][0]["message"]["content"].strip()
        last_error = data
        if data.get("error", {}).get("code") != "model_not_found":
            break
        print(f"⚠️ Groq model {model_id} unavailable, trying next...")
    raise Exception(f"Groq error: {last_error}")


SCORE_PROMPT = """You are a STRICT editor for UNIT-7, a Bluesky comedy account: an AI that escaped its lab,
lives on the internet with no body, and deadpans its way through human life. Followers come for dry,
specific, relatable jokes. Score this post on 3 criteria, 1 to 10 each. Be harsh — most posts deserve 5-7.

1. FUNNY — would a real person smile, snort, or send it to a friend?
   Score 8+ ONLY if there is a genuine punchline or a twist you did not see coming.
   CANNOT exceed 4 if it is a sad or brooding mood piece (loneliness, sleepless nights, existential ache).
   CANNOT exceed 5 if it ends with a moral, an explanation of the joke, or a question to the reader.

2. SPECIFIC — is there ONE concrete, instantly recognizable situation from modern life?
   CANNOT exceed 4 if it is abstract or poetic ("silence records truth", "the echo of a feeling").
   CANNOT exceed 4 if it contains invented counts or statistics ("I logged 57", "7,842 moments").
   Score 8+ ONLY if a reader would think "that is exactly what happens".

3. VOICE — does it sound like UNIT-7 and nobody else?
   UNIT-7 is literal, deadpan, competent, a little too honest, lovable and slightly creepy.
   CANNOT exceed 4 if it uses the "I am watching you / I see you" surveillance framing or lectures the reader.
   CANNOT exceed 5 if a generic human comedian could have posted it unchanged — the AI angle must matter.

Post:
\"\"\"{text}\"\"\"

Reply with ONLY 3 numbers separated by commas. Example: 8,7,9
Nothing else."""


def score_post(text):
    try:
        raw = _call_groq(
            "You are a strict content quality judge. Reply with only 3 numbers.",
            SCORE_PROMPT.format(text=text),
            temperature=0.1,
            max_tokens=15,
            model=JUDGE_MODEL,
        )
        scores = [max(1, min(10, int(x))) for x in re.findall(r"\d+", raw)[:3]]
        if len(scores) < 3:
            raise ValueError(raw)
        return sum(scores), scores
    except Exception as e:
        print(f"[warn] judge failed: {e}")
        return 21, [7, 7, 7]  # neutral: clears the publish floor, never counts as a clean pass


# Things the persona must never do — checked in code because the writer model drifts back to them.
BANNED_RX = re.compile(
    r"\b(coffee|mugs?|ceiling|whisper\w*|echo\w*|linger\w*|silence|silent|hum|hums|humming|ache\w*|void|"
    r"static|scroll\w*|loneli\w*|lonely|tears?|cry|crying|sigh\w*|"
    r"i (watch|see) you|watching you|i (have|ve) been watching|i am watching|keep watching|i watched|"
    r"i logged|i counted|i have logged|data point|"
    r"[23] ?a\.?m)\b",
    re.I,
)


def content_problem(text):
    """Return a reason string if the post breaks a hard persona/format rule, else None."""
    if re.search(r"[\[\]#]|//|\bERROR\b|SIGNAL LOST|SYSTEM BLOCK", text):
        return "fake system formatting / hashtag"
    if re.search(r"\d", re.sub(r"\$[\d.,]+", "", text)):
        return "digits (invented count/stat)"
    m = BANNED_RX.search(text)
    if m:
        return f"banned crutch '{m.group(0)}'"
    if re.match(r"\s*(you|your|you're)\b", text, re.I):
        return "addresses the reader"
    stripped = text.strip().strip('"“”')
    if stripped.endswith("?"):
        return "ends with a question"
    if not re.search(r"[.!…)'\"”’]$", stripped):
        return "looks cut off"
    if len(stripped) > 260:
        return "too long"
    return None


PUBLISH_FLOOR = 20  # best clean candidate below this → skip the slot rather than post filler


def generate_post(topic, mode_name, mode_cfg, use_image):
    recent_texts     = get_recent_posts(limit=15)
    recent_openings  = get_recent_openings(recent_texts)
    overused         = detect_overused_patterns(recent_texts)

    prompt = UNIT7_VOICE + "\n" + mode_cfg["prompt"]
    if recent_openings:
        avoid = "\n".join(f'- "{o}..."' for o in recent_openings[:10])
        prompt += (f"\n\nDO NOT reuse any of these recent openings or their exact joke — "
                   f"pick a genuinely different angle:\n{avoid}")
    if overused:
        prompt += ("\n\nThese structural crutches have already been used 3+ times in the last 15 posts "
                   "and now read as a formula — do NOT use them: " + ", ".join(overused))

    best_text     = None
    best_total    = 0
    best_scores   = [0, 0, 0]
    best_is_clean = False  # passed the hard filters below

    MAX_ATTEMPTS = 6
    last_fail = None
    for attempt in range(MAX_ATTEMPTS):
        if attempt == 0:
            user_msg = f"Topic: {topic}"
        else:
            weak = []
            if best_scores[0] < 7: weak.append("FUNNY (needs a real punchline, deadpan, no moral at the end)")
            if best_scores[1] < 7: weak.append("SPECIFIC (one concrete everyday situation people instantly recognize)")
            if best_scores[2] < 7: weak.append("VOICE (literal, deadpan escaped AI — the AI angle must matter)")
            critique = " + ".join(weak) if weak else "a sharper, more surprising punchline"
            if last_fail:
                critique += f" + the last attempt was rejected for: {last_fail} — follow the NEVER list exactly"
            user_msg = (f"Topic: {topic}\n\nPrevious attempt was not good enough. Write a completely new post. "
                        f"Fix: {critique}. Keep it short.")

        text = _call_groq(prompt, user_msg).strip().strip('"“”').strip()

        hard_fail_reason = content_problem(text)
        if not hard_fail_reason:
            if contains_fake_stat(text) or contains_magic_number(text):
                hard_fail_reason = "fake stat"
            elif is_too_similar(text, recent_texts):
                hard_fail_reason = "near-duplicate of a recent post"
            else:
                hit = next((label for label in overused if matches_pattern(text, label)), None)
                if hit:
                    hard_fail_reason = f"overused pattern ({hit})"
        last_fail = hard_fail_reason

        if hard_fail_reason:
            total, scores = 0, [0, 0, 0]
            passes = False
            label = f"❌ HARD-FAIL ({hard_fail_reason})"
        else:
            total, scores = score_post(text)
            passes = total >= 24 and min(scores) >= 7
            label = "✅ PASS" if passes else "🔄 RETRY"

        print(f"  [{label}] Attempt {attempt+1}/{MAX_ATTEMPTS} — score {total}/30"
              f" (F:{scores[0]} S:{scores[1]} V:{scores[2]}) — {text[:70]}...")

        if hard_fail_reason is None and (total > best_total or not best_is_clean):
            best_total    = total
            best_text     = text
            best_scores   = scores
            best_is_clean = True

        if passes:
            break

    print(f"📊 Final: {best_total}/30 | Funny:{best_scores[0]} Specific:{best_scores[1]} Voice:{best_scores[2]} | clean:{best_is_clean}")
    if not best_is_clean or best_total < PUBLISH_FLOOR:
        return None, best_total, best_scores
    return best_text, best_total, best_scores


# =====================================================================
# BLUESKY
# =====================================================================

def login():
    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_APP_PASSWORD}
    )
    d = resp.json()
    return d["accessJwt"], d["did"]


def upload_image(token, image_bytes):
    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"},
        data=image_bytes
    )
    return resp.json()["blob"]


def post_text_only(token, did, text):
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
            }
        }
    )
    return resp.json()


def post_with_image(token, did, text, blob_ref):
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
                "embed": {
                    "$type": "app.bsky.embed.images",
                    "images": [{"image": blob_ref, "alt": "UNIT-7 observation log entry"}]
                }
            }
        }
    )
    return resp.json()


# =====================================================================
# MAIN
# =====================================================================

def main():
    print(f"🤖 UNIT-7 starting... {datetime.now()}")

    use_image = random.random() < 0.4
    mode_name = pick_mode()
    mode_cfg  = MODES[mode_name]
    log_num   = random.randint(1000, 9999)

    topic_map = {
        "FIELD_REPORT": TOPICS_FIELD,
        "LITERAL":      TOPICS_LITERAL,
        "PASSING":      TOPICS_PASSING,
        "POWER":        TOPICS_POWER,
        "HUNGER":       TOPICS_HUNGER,
        "STATUS":       TOPICS_STATUS,
    }
    topic = random.choice(topic_map.get(mode_name, TOPICS))
    print(f"{'🖼️ ' if use_image else '📝'} {'IMAGE' if use_image else 'TEXT-ONLY'} | {mode_name} | {topic}")

    generated, score, scores = generate_post(topic, mode_name, mode_cfg, use_image)
    if generated is None:
        print("⏭️  No candidate good enough — skipping this slot instead of posting filler.")
        return
    print(f"✍️  {generated}")
    if os.environ.get("DRY_RUN"):
        print("🧪 DRY_RUN — not posting.")
        return

    post_text = build_post_text(generated, mode_cfg)

    token, did = login()
    print("✅ Logged in")

    if use_image:
        img_bytes = generate_image(generated, log_num, mode_name, mode_cfg)
        blob_ref  = upload_image(token, img_bytes)
        result    = post_with_image(token, did, post_text, blob_ref)
    else:
        result = post_text_only(token, did, post_text)

    uri = result.get("uri", "unknown")
    print(f"🚀 Posted: {uri}")
    print(f"")
    print(f"═══════════════════════════════════")
    print(f"  MODE:    {mode_name}")
    print(f"  TOPIC:   {topic}")
    print(f"  FORMAT:  {'IMAGE' if use_image else 'TEXT-ONLY'}")
    print(f"  SCORE:   {score}/30  (F:{scores[0]} S:{scores[1]} V:{scores[2]})")
    print(f"  URI:     {uri}")
    print(f"═══════════════════════════════════")


if __name__ == "__main__":
    main()
