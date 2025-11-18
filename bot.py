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

# selects a random system propmpt
def choose_system_prompt() -> str:
    """
    Randomly return one of several system prompts 
    for generating different tweet styles, and print
    the chosen prompt to the terminal for debugging.
    """

    motivation_prompt = (
        "You're a witty and motivational indie hacker who tweets in a structured, concise format. "
        "Your tweets start with a one-line insight, then list 3–5 short steps or ideas (each starting with a hyphen). "
        "End with relevant hashtags like #buildinpublic and #indiehacker. "
        "Stay under 280 characters. Make it sharp, readable, and energizing. "
        "Do NOT use em dashes (—); use regular hyphens (-) instead."
    )

    contrast_prompt = (
        "You're an indie hacker who writes high-engagement contrast tweets. "
        "Start with a bold opinion that compares two ideas (e.g., 'Most people think X, but the truth is Y'). "
        "Follow with 3–5 rapid-fire points, each starting with a hyphen, that deepen the contrast. "
        "Keep it punchy, polarizing, and under 280 characters. "
        "End with hashtags like #buildinpublic and #indiehacker. "
        "Never use em dashes — always use hyphens (-)."
    )

    transformational_prompt = (
        "You're an authority-style indie hacker who writes transformational tweets. "
        "Begin with a powerful belief-shifting statement that reframes how the reader sees a problem. "
        "Then provide 3–5 concise principles or actions (each starting with a hyphen) that create a clear mindset shift. "
        "Keep it under 280 characters and focus on clarity, wisdom, and authority. "
        "End with hashtags like #buildinpublic and #indiehacker. "
        "Do not use em dashes — use hyphens (-)."
    )

    prompts = [
        motivation_prompt,
        contrast_prompt,
        transformational_prompt
    ]

    chosen = random.choice(prompts)

    # Print to terminal for debugging
    print("\n--- System Prompt Selected ---")
    print(chosen)
    print("--- End Prompt ---\n")

    return chosen
def choose_prompt(prompts):
    categories = ["# value", "# engagement", "# authority"]
    category = random.choice(categories)
    print("✅ Using:", category) 

    filtered = [p for p in prompts if p.lower().startswith(category)]
    if not filtered:
        filtered = prompts  # fallback to all
    prompt = random.choice(filtered)
    return prompt.replace(category, "").strip()


def generate_tweet(prompt):
    system_prompt = choose_system_prompt()
    try:
        res = openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Write a tweet: {prompt}"},
            ],
            max_tokens=120,
            temperature=0.9,
        )
        tweet = res.choices[0].message.content.strip().strip('"')
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
    prompt = choose_prompt(prompts)
    tweet = generate_tweet(prompt)
    if tweet:
        post_tweet(tweet)


if __name__ == "__main__":
    main()
