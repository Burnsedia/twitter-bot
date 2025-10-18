import os
import random
import openai
import tweepy
from dotenv import load_dotenv
from datetime import datetime

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


def get_tweet(twitID):
    pass

def genorate_replay(twitID):
     system_prompt = (
        "You're a witty and motivational indie hacker who tweets in a structured, concise format. "
        "Your tweets start with a one-line insight, then list 3–5 short steps or ideas (like a mini-guide), "
        "each on its own line with a dash. End with relevant hashtags like #buildinpublic and #indiehacker. "
        "No more than 280 characters total. Make it sharp and readable."
        "Do NOT use em dashes (—); use regular hyphens (-) or other punctuation instead."    
    )

    try:
        res = openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Write a tweet: {twitID}"},
            ],
            max_tokens=120,
            temperature=0.9,
        )
        tweet = res.choices[0].message.content.strip().strip('"')
        return tweet[:280]
    except Exception as e:
        print("⚠️ OpenAI error:", e)
        return prompt[:280]



def replay_to_tweet(replay_Text, twitID):
    pass



def main():
    pass

 if __name__ == "__main__":
    main()
