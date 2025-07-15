import os
import time
import random
import openai
import tweepy
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# OpenAI setup
openai.api_key = os.getenv("OPENAI_API_KEY")

# Twitter setup
client = tweepy.Client(
    consumer_key=os.getenv("TWITTER_API_KEY"),
    consumer_secret=os.getenv("TWITTER_API_SECRET"),
    access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
    access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
)


def generate_tweet(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Write a tweet: {prompt}"}],
            max_tokens=100,
            temperature=0.9,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("OpenAI error:", e)
        return None


def post_tweet(tweet):
    try:
        client.create_tweet(text=tweet)
        print("✅ Tweeted:", tweet)
    except Exception as e:
        print("Twitter error:", e)


def load_prompts():
    with open("prompts.txt") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    prompts = load_prompts()
    for i in range(20):
        prompt = random.choice(prompts)
        tweet = generate_tweet(prompt)
        if tweet:
            post_tweet(tweet)
        time.sleep(60 * 72)  # tweet every ~72 minutes (20 per day)


if __name__ == "__main__":
    main()
