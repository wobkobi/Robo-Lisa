import re
import emoji
import csv
import os
import logging

logger = logging.getLogger("LisaBotLogger")


def is_emoji_name(text):
    # Check if the text is a valid standard emoji.
    return text in emoji.UNICODE_EMOJI_ENGLISH


def emoji_check(msg, guild_emojis):
    """Check if emoji exists in the message and if it belongs to the guild or is a standard emoji."""
    logger.debug(f"Checking emoji existence in message: {msg.content}")
    discord_emoji_pattern = re.compile(r":[a-zA-Z0-9_]+:")
    matches = discord_emoji_pattern.findall(msg.content)

    if matches:
        match = matches[0][1:-1]  # Remove the colons
        for guild_emoji in guild_emojis:
            if guild_emoji.name == match:
                logger.debug(f"Found matching guild emoji: {match}")
                return True

        if is_emoji_name(match):
            logger.debug(f"Found matching standard emoji: {match}")
            return True

    logger.debug("No matching emoji found.")
    return False


def filter_message(msg):
    # Filter the message to capture author, original message, and emoji reply.
    logger.debug("Filtering message for recording.")
    filtered_message = ""

    # Check if the message is a reply
    if msg.get_referenced_message:
        author = msg.get_referenced_message.author.display_name
        original_message = msg.get_referenced_message.content
    else:
        # Fallback for non-replied messages
        author = msg.author.display_name
        original_message = msg.content

    # Find emoji in the message content
    discord_emoji_pattern = re.compile(r":[a-zA-Z0-9_]+:")
    matches = discord_emoji_pattern.findall(msg.content)
    reply_emoji = matches[0] if matches else "None"

    filtered_message = ",".join([author, original_message, reply_emoji])
    logger.debug(f"Filtered message: {filtered_message}")
    return filtered_message


def record_msg(msg, guild_emojis):
    # Record the message if it contains valid emojis.
    logger.info("Recording a message.")
    if not emoji_check(msg, guild_emojis):
        logger.debug("No valid emoji in message. Skipping.")
        return

    filtered_message = filter_message(msg)
    file_exists = os.path.isfile("training.csv")
    with open("training.csv", "a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["author", "original_message", "reply_emoji"])
        writer.writerow(filtered_message.split(","))

    logger.info("Message recorded successfully.")
