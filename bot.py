import os
import time
import random
import openai
import tweepy
from dotenv import load_dotenv

load_dotenv()

# New client (v1.0+)
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Twitter setup
twitter_client = tweepy.Client(
    consumer_key=os.getenv("TWITTER_API_KEY"),
    consumer_secret=os.getenv("TWITTER_API_SECRET"),
    access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
    access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
)


def generate_tweet(prompt):
    system_prompt = (
        "You're a witty and motivational indie hacker who tweets in a structured, concise format. "
        "Your tweets start with a one-line insight, then list 3–5 short steps or ideas (like a mini-guide), "
        "each on its own line with a dash. End with relevant hashtags like #buildinpublic and #indiehacker. "
        "No more than 280 characters total. Make it sharp and readable."
    )

    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Write a tweet: {prompt}"},
            ],
            max_tokens=120,
            temperature=0.9,
        )
        tweet = res.choices[0].message.content.strip()
        return tweet[:280]
    except Exception as e:
        print("⚠️ OpenAI error:", e)
        return prompt[:280]


def post_tweet(tweet):
    try:
        twitter_client.create_tweet(text=tweet)
        print("✅ Tweeted:", tweet)
    except Exception as e:
        print("Twitter error:", e)


def load_prompts():
    with open("prompts.txt") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    prompts = load_prompts()
    for _ in range(20):
        prompt = random.choice(prompts)
        tweet = generate_tweet(prompt)
        if tweet:
            post_tweet(tweet)
        time.sleep(60 * 72)  # ~72 mins between tweets


if __name__ == "__main__":
    main()
