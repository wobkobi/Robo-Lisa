import logging
from logging.handlers import RotatingFileHandler
from interactions import (
    Client,
    Intents,
    listen,
)
from interactions.api.events import MessageCreate
from dotenv import load_dotenv
import os
import pickle
import random
import asyncio
import bot_retrainer
import bot_recorder
from pathlib import Path
from datetime import datetime


def load_pickle(file_name):
    with open(file_name, "rb") as file:
        return pickle.load(file)


# Setup for logging
log_folder = Path("logs")
log_folder.mkdir(exist_ok=True)

# Get today's date for the log file
current_date = datetime.now().strftime("%Y-%m-%d")
log_file = log_folder / "latest.log"  # Current log file as 'latest.log'
log_file_template = (
    log_folder / f"{current_date}-%d.log"
)  # Rotated log files with date-based naming

log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Rotating File Handler: Max 5MB per file, keeps the last 5 rotated files per date
log_handler = RotatingFileHandler(
    log_file,
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=5,  # Keep last 5 rotated files for each day
)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.DEBUG)

# Console Handler for printing logs to the console
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# Logger setup
logger = logging.getLogger("LisaBotLogger")
logger.setLevel(logging.DEBUG)
logger.addHandler(log_handler)
logger.addHandler(console_handler)

logger.info("Centralized logging initialized with date-based filenames.")

# Loading the serialized components
vectorizer = load_pickle("vectorizer.pkl")
classifier = load_pickle("classifier.pkl")
encoded_to_string = load_pickle("encoded_to_string.pkl")
tfidf_transformer = ""


def get_emoji_back(encoded_number):
    return encoded_to_string.get(encoded_number, "Unknown")


def predict_emoji(text, classifier, vectorizer, tfidf_transformer, threshold=0.1):
    logger.debug(f"Predicting emojis for text: {text}")
    # Preprocess and vectorize the input text
    text_vectorized = vectorizer.transform([text])

    # TFIDF Convert
    text_tfidf = tfidf_transformer.transform(text_vectorized)

    # Get probabilities for each emoji
    probabilities = classifier.predict_proba(text_tfidf)[0]

    # Filter out predictions with probabilities above the threshold
    high_prob_indices = [i for i, prob in enumerate(probabilities) if prob > threshold]

    # Decode the emojis
    emojis = [get_emoji_back(index) for index in high_prob_indices]

    logger.debug(f"Predicted emojis: {emojis}")
    return emojis


def answer_question(message):
    # first check if message is a question directed at lisabot
    if message.strip().endswith("?"):
        if len(message) > 1:
            likert_scale = {
                "strong_agree": ["YES", "YESSSS", "Absolutely!"],
                "agree": [
                    "yes",
                    "yessir",
                    "ya",
                    "shut up yes",
                    "https://tenor.com/view/kkekekekekkeke-kk-gif-27232250",
                ],
                "neutral": [
                    "I actually dont know",
                    "um duh",
                    "period",
                    "not rn",
                    "lol",
                    "I wish I could tell you but I don't want to",
                    "AYO????",
                    "https://cdn.discordapp.com/attachments/1113266262345273428/1213985020901851146/IMG_7578.png?ex=65f776a7&is=65e501a7&hm=20b5210081b1362c97ca5a5fd5dd02dd33f15b2da783cc44aab2fa1a670d6878&",
                ],
                "disagree": ["nope", "ewww no", "naurrr", "joever"],
                "strong_disagree": ["WHAT NO", "NO", "Absolutely not!!!"],
            }

            random_opinion = random.choice(list(likert_scale.keys()))
            likert_answer = random.choice(likert_scale[random_opinion])

            return likert_answer
        else:
            return "?"


# put canned responses
def response_to(message):
    reply = ""

    keywords = {
        "erm actually": lambda: "https://tenor.com/view/nerd-dog-nerd-dog-gif-nerd-dog-alen-orbanic-gif-15562966513664309472",
        "lisa burger": lambda: "https://media.discordapp.net/attachments/1113266262345273428/1187365137598922802/imageedit_9_9053779888.png?ex=65969ef4&is=658429f4&hm=8ea4ed39282ce942d2556cced752afcc23353607d02a60e7b5119a4ac9c8e43f&=&format=webp&quality=lossless&width=462&height=462",
        "in my opinion": lambda: "https://cdn.discordapp.com/attachments/1168400523104358442/1193073645715734578/y147cc9pwqac1.png?ex=65ab636b&is=6598ee6b&hm=c081a2716fbb8415c6a8be0d8ad8fa24fbfa639a5d97d0d673b15c65e2b984ca&",
        "are you the real lisa?": lambda: "I am the real Lisa",
        "fortnite blake": lambda: "https://tenor.com/view/fortnite-fish-guy-fortnite-wow-gif-27449064",
        "ramesh": lambda: "https://tenor.com/view/sleeping-sleep-dog-dawg-eeper-gif-5083970977419902566",
        "too powerful": lambda: "https://cdn.discordapp.com/emojis/853892024879808513.gif?size=128&quality=lossless",
    }

    for keyword, action in keywords.items():
        if keyword in message:
            reply = action()

    return reply


load_dotenv()
TOKEN = os.getenv("TOKEN")

bot = Client(intents=Intents.ALL)

# used for determining if everyone is posting the same thing.
previous_msg = ""

# count of how many replies the bot has before it stops.
count = 10


async def run_every_2_hours():
    global count, vectorizer, tfidf_transformer, classifier, encoded_to_string
    while True:
        count += 3
        logger.info("Retraining bot...")
        vectorizer, tfidf_transformer, classifier, encoded_to_string = (
            bot_retrainer.retrain_bot()
        )
        logger.info("Bot retrained successfully.")
        await asyncio.sleep(3 * 60 * 60)


@listen()
async def on_ready():
    logger.info("Bot is ready and connected.")
    asyncio.create_task(run_every_2_hours())


@listen()
async def on_message_create(event: MessageCreate):
    global count
    msg = event.message
    guild_emojis = await msg.guild.fetch_all_custom_emojis()
    logger.debug(f"Message received: {msg.content} by {msg.author}")

    if msg.author.bot:  # Check if the message is from a bot
        logger.debug("Message is from a bot. Ignoring.")
        return

    # lisa38
    if msg.author == "lisa38":
        # print("lisa spoke")
        bot_recorder.record_msg(msg, guild_emojis)

    # follow along if everyone is posting the same thing.
    global previous_msg
    # checks if first time booting up
    if isinstance(previous_msg, str):
        previous_msg = msg
    if msg.content == previous_msg.content and msg.author != previous_msg.author:
        logger.info(f"Echoing message: {msg.content}")
        await msg.channel.send(msg.content)
        previous_msg.content = "lisabot"
        return
    previous_msg = msg

    likert_answer = ""

    # checks for trigger word and sends hardcoded reply
    trigger = response_to(msg.content)
    if trigger != "":
        logger.info(f"Triggered response for keyword. Replying with: {trigger}")
        await msg.reply(trigger)
        return
    # checks if the bot is mentioned
    bot_mentioned = (
        f"@{bot.user.id}" in msg.content or f"<@{bot.user.id}>" in msg.content
    )
    if bot_mentioned:
        # gets rid of bot's name before running through the classifier
        text = msg.content.replace(f"<@{bot.user.id}>", "").strip()
        # wakes the bot for a bit
        count += 3
        likert_answer = answer_question(text)
    else:
        text = msg.content

    text = str(msg.author)[1:] + " " + text

    # Determine whether to skip the count and random chance check
    skip_check = bot_mentioned or (count > 0 and random.randint(1, 15) == 1)
    if not skip_check:
        logger.debug("Check not passed. Exiting function.")
        return  # print(f"Check not passed. Exiting function. {bot_mentioned}, {count}")

    emoji_list = predict_emoji(
        text, classifier, vectorizer, tfidf_transformer, threshold=0.1
    )
    if emoji_list:
        emojis_to_send = ""
        for emoji_name in emoji_list:
            for guild_emoji in await msg.guild.fetch_all_custom_emojis():
                if guild_emoji.name == emoji_name.replace(":", ""):
                    emojis_to_send += str(guild_emoji)

        if emojis_to_send or likert_answer:
            response = likert_answer + " " + emojis_to_send
            if random.randint(1, 2) == 1:
                logger.info(f"Replying to message: {response}")
                await msg.reply(response)
            else:
                logger.info(f"Sending message: {response}")
                await msg.channel.send(response)
        else:
            fallback_response = random.choice(["HUH", "??"])
            logger.info(f"Fallback response: {fallback_response}")
            await msg.channel.send(fallback_response)

        count -= 1


bot.start(TOKEN)
