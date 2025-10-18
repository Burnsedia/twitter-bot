import os
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta

import tweepy
from dotenv import load_dotenv
import openai

# =========================
# Config
# =========================
STATE_PATH = Path("./reply_state.json")
MAX_FOLLOWING_SAMPLE = 200            # cap how many followings to scan each run
MAX_TWEETS_PER_USER = 3               # pull a few per user
MAX_SEARCH_RESULTS = 50
MIN_LIKES = 5                          # basic popularity filter
MIN_RTS = 1
LANG = "en"
REPLY_LIMIT_PER_RUN = 5               # how many replies per execution
COOLDOWN_SECONDS = 3                  # small pause between posts

# Your niche knobs
NICHE_TERMS = [
    "indie hacker", "build in public", "bootstrap", "solopreneur",
    "devops", "neovim", "linux", "python", "django", "godot"
]
# Optional curated list of popular accounts in your niche (usernames, no @)
NICHE_ACCOUNTS_ALLOWLIST = [
    # "levelsio", "swyx", "naval", ...
]

# =========================
# Setup
# =========================
load_dotenv()

openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

twitter = tweepy.Client(
    bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
    consumer_key=os.getenv("TWITTER_API_KEY"),
    consumer_secret=os.getenv("TWITTER_API_SECRET"),
    access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
    access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    wait_on_rate_limit=True,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# =========================
# State
# =========================
def load_state() -> Dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"since_id_following": None, "since_id_search": None, "replied_ids": []}

def save_state(state: Dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))

# =========================
# Helpers
# =========================
def safe_280(text: str) -> str:
    text = (text or "").strip().replace("\n\n", "\n").strip('"')
    return text[:280]

def my_user_id() -> Optional[str]:
    try:
        me = twitter.get_me()
        return me.data.id if me and me.data else None
    except tweepy.TweepyException as e:
        logging.error(f"get_me error: {e}")
        return None

def fetch_following_ids(user_id: str, limit: int = MAX_FOLLOWING_SAMPLE) -> List[str]:
    ids = []
    try:
        paginator = tweepy.Paginator(
            twitter.get_users_following,
            id=user_id,
            max_results=100,
            user_fields=["username"]
        )
        for page in paginator:
            if page.data:
                ids.extend([u.id for u in page.data])
            if len(ids) >= limit:
                break
    except tweepy.TweepyException as e:
        logging.error(f"get_users_following error: {e}")
    return ids[:limit]

def fetch_recent_from_users(user_ids: List[str], since_id: Optional[str]) -> List[Dict]:
    """Collect recent original tweets (no RT/reply) from given users."""
    items = []
    for uid in user_ids:
        try:
            resp = twitter.get_users_tweets(
                id=uid,
                since_id=since_id,
                exclude=["retweets","replies"],
                max_results=min(100, MAX_TWEETS_PER_USER * 5),
                tweet_fields=["created_at","lang","public_metrics","referenced_tweets","author_id"]
            )
            if not resp.data:
                continue
            # Keep only a few per user to be polite
            for t in resp.data[:MAX_TWEETS_PER_USER]:
                if t.lang and t.lang != LANG:
                    continue
                pm = t.public_metrics or {}
                items.append({
                    "id": t.id,
                    "text": t.text or "",
                    "author_id": t.author_id,
                    "likes": pm.get("like_count", 0),
                    "rts": pm.get("retweet_count", 0),
                    "created_at": t.created_at or datetime.now(timezone.utc),
                    "source": "following"
                })
        except tweepy.TweepyException as e:
            logging.warning(f"get_users_tweets error for {uid}: {e}")
            continue
    # sort newest first
    items.sort(key=lambda x: x["id"], reverse=True)
    return items

def build_search_query(terms: List[str]) -> str:
    # (term1 OR term2 ...) -is:retweet -is:reply lang:en
    or_block = " OR ".join([f'"{t}"' if " " in t else t for t in terms])
    base = f"({or_block}) -is:retweet -is:reply lang:{LANG}"
    return base

def fetch_niche_search(since_id: Optional[str]) -> List[Dict]:
    items = []
    query = build_search_query(NICHE_TERMS)
    try:
        resp = twitter.search_recent_tweets(
            query=query,
            since_id=since_id,
            max_results=min(100, MAX_SEARCH_RESULTS),
            tweet_fields=["created_at","lang","public_metrics","author_id"],
        )
        if resp.data:
            for t in resp.data:
                pm = t.public_metrics or {}
                items.append({
                    "id": t.id,
                    "text": t.text or "",
                    "author_id": t.author_id,
                    "likes": pm.get("like_count", 0),
                    "rts": pm.get("retweet_count", 0),
                    "created_at": t.created_at or datetime.now(timezone.utc),
                    "source": "search"
                })
    except tweepy.TweepyException as e:
        logging.error(f"search_recent_tweets error: {e}")
    return items

def fetch_from_allowlist(usernames: List[str], since_id: Optional[str]) -> List[Dict]:
    """Optional: pull from curated popular accounts."""
    items = []
    if not usernames:
        return items
    # Resolve usernames -> ids (batch)
    try:
        resp = twitter.get_users(usernames=usernames, user_fields=["username"])
        ids = [u.id for u in (resp.data or [])]
    except tweepy.TweepyException as e:
        logging.error(f"get_users (allowlist) error: {e}")
        ids = []
    if not ids:
        return items
    return fetch_recent_from_users(ids, since_id)

def filter_and_rank(candidates: List[Dict], replied_ids: List[str], self_id: str) -> List[Dict]:
    fresh_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    out = []
    seen = set()
    for c in candidates:
        if str(c["id"]) in replied_ids:
            continue
        if c["author_id"] == self_id:
            continue
        if c["likes"] < MIN_LIKES and c["rts"] < MIN_RTS:
            continue
        if isinstance(c["created_at"], datetime) and c["created_at"] < fresh_cutoff:
            continue
        key = str(c["id"])
        if key in seen:
            continue
        seen.add(key)
        score = c["likes"] * 2 + c["rts"]
        c["score"] = score
        out.append(c)
    # highest score first
    out.sort(key=lambda x: (x["score"], x["id"]), reverse=True)
    return out

def gen_reply(orig_text: str, author_handle: Optional[str]) -> Optional[str]:
    system_prompt = (
        "You're a witty, motivational indie hacker who replies in a concise, structured format. "
        "Start with a one-line insight, then 3–5 actionable bullets (each line begins with a hyphen). "
        "End with 1–2 relevant hashtags like #buildinpublic or #indiehacker. "
        "Max 280 characters. No em dashes (—); use hyphens (-). Avoid generic praise. Add value."
    )
    user_prompt = (
        f"Original tweet by @{author_handle or 'user'}:\n"
        f"\"{orig_text.strip()}\"\n\n"
        f"Write a concise value-add reply."
    )
    try:
        res = openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=140,
            temperature=0.9,
        )
        return safe_280(res.choices[0].message.content)
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return None

def get_author_handle(user_id: str) -> Optional[str]:
    try:
        resp = twitter.get_user(id=user_id, user_fields=["username"])
        return resp.data.username if resp and resp.data else None
    except tweepy.TweepyException:
        return None

def post_reply(text: str, in_reply_to_id: str) -> Optional[Tuple[str, str]]:
    if not text:
        return None
    try:
        resp = twitter.create_tweet(text=safe_280(text), in_reply_to_tweet_id=in_reply_to_id)
        if resp and resp.data and "id" in resp.data:
            rid = resp.data["id"]
            url = f"https://x.com/i/web/status/{rid}"
            logging.info(f"Replied: {url}")
            return rid, url
    except tweepy.TweepyException as e:
        logging.error(f"create_tweet error: {e}")
    return None

# =========================
# Main flow
# =========================
def collect_candidates(state: Dict, uid: str) -> Tuple[List[Dict], Dict]:
    # 1) from following
    following = fetch_following_ids(uid)
    from_following = fetch_recent_from_users(following, state.get("since_id_following"))
    if from_following:
        # update since_id to the highest id we saw
        state["since_id_following"] = max(str(t["id"]) for t in from_following)

    # 2) niche search
    from_search = fetch_niche_search(state.get("since_id_search"))
    if from_search:
        state["since_id_search"] = max(str(t["id"]) for t in from_search)

    # 3) curated allowlist (optional)
    from_allow = fetch_from_allowlist(NICHE_ACCOUNTS_ALLOWLIST, state.get("since_id_search"))

    all_items = from_following + from_search + from_allow
    logging.info(f"Collected: following={len(from_following)}, search={len(from_search)}, allowlist={len(from_allow)}")
    return all_items, state

def run(dry_run: bool = True):
    state = load_state()
    uid = my_user_id()
    if not uid:
        logging.error("Could not resolve authenticated user ID.")
        return

    candidates, state = collect_candidates(state, uid)
    ranked = filter_and_rank(candidates, state.get("replied_ids", []), uid)

    if not ranked:
        logging.info("No suitable tweets found.")
        save_state(state)
        return

    posted = 0
    for c in ranked:
        if posted >= REPLY_LIMIT_PER_RUN:
            break
        author = get_author_handle(c["author_id"])
        draft = gen_reply(c["text"], author)
        if not draft:
            continue

        logging.info(f"Draft ({len(draft)}):\n{draft}\n---\nSource: {c['source']} | Likes={c['likes']} RTs={c['rts']} | TweetID={c['id']}")

        if dry_run:
            logging.info("Dry-run: not posting.")
            # Mark as replied in dry-run? Usually no. Keep it discoverable next real run.
        else:
            res = post_reply(draft, str(c["id"]))
            if res:
                state.setdefault("replied_ids", []).append(str(c["id"]))
                posted += 1
                time.sleep(COOLDOWN_SECONDS)

    save_state(state)
    logging.info(f"Done. Posted={posted}, Remaining candidates={max(0, len(ranked)-posted)}")

if __name__ == "__main__":
    import sys
    dry = True
    if "--post" in sys.argv:
        dry = False
    run(dry_run=dry)

