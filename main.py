import discord
import json
import os
import aiohttp
from discord.abc import GuildChannel

# Ensure data directory exists
os.makedirs("./data", exist_ok=True)

# Settings file path
SETTINGS_FILE = "./data/settings.json"


# Load or create settings
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"forwards": []}


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

client = discord.Client()

add_forward_waiting = {}
remove_forward_waiting = {}


@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")


@client.event
async def on_message(message):
    # Skip bot messages
    if message.author.id == client.user.id:
        # Check for +add command
        if message.content.startswith("+add "):
            await cmd_add_forward(message)
            return

        # Check for +remove command
        if message.content.startswith("+remove "):
            await cmd_remove_forward(message)
            return

        # Check for +list command
        if message.content.strip() == "+list":
            await cmd_list_forwards(message)
            return

    # Process message forwarding
    await process_forward(message)

async def cmd_add_forward(message):
    """Handle +add command with arguments"""
    try:
        parts = message.content.strip().split(' ')[1:]
        if len(parts) != 2:
            await message.reply("Usage: `+add source_channel_id webhook_url`")
            return

        print(parts)
        source_id = int(parts[0])
        webhook_url = parts[1].strip()

        source_channel = client.get_channel(source_id)

        if not source_channel:
            await message.reply(
                f"Source channel {source_id} not found or bot doesn't have access."
            )
            return

        settings = load_settings()

        for forward in settings["forwards"]:
            if forward["source"] == source_id and forward["webhook"] == webhook_url:
                await message.reply("This forward already exists!")
                return

        settings["forwards"].append({"source": source_id, "webhook": webhook_url})

        save_settings(settings)

        source_name = (
            source_channel.name
            if isinstance(source_channel, GuildChannel)
            else f"DM ({source_id})"
        )
        await message.reply(
            f"✅ Forward added successfully!\n"
            f"Source: {source_name} ({source_id})\n"
            f"Target: Webhook"
        )

    except ValueError:
        await message.reply(
            "Invalid channel ID. Please provide a valid numeric channel ID."
        )
    except Exception as e:
        await message.reply(f"Error adding forward: {str(e)}")


async def cmd_remove_forward(message):
    """Handle +remove command with arguments"""
    try:
        parts = message.content.strip().split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.reply(
                "Usage: `+remove <forward_number>`\nUse `+list` to see forward numbers."
            )
            return

        index = int(parts[1]) - 1

        settings = load_settings()

        if index < 0 or index >= len(settings["forwards"]):
            await message.reply(
                f"Invalid number. Please choose between 1 and {len(settings['forwards'])}."
            )
            return

        removed = settings["forwards"].pop(index)

        save_settings(settings)

        source = client.get_channel(removed["source"])
        source_name = (
            source.name
            if isinstance(source, GuildChannel)
            else f"DM ({removed['source']})"
            if source
            else "Unknown"
        )

        await message.reply(f"✅ Removed forward: {source_name} → Webhook")

    except Exception as e:
        await message.reply(f"Error removing forward: {str(e)}")


async def cmd_list_forwards(message):
    """Handle +list command"""
    settings = load_settings()

    if not settings["forwards"]:
        await message.reply("No active forwards.")
        return

    forward_list = "**Active Forwards:**\n\n"
    for i, forward in enumerate(settings["forwards"], 1):
        source = client.get_channel(forward["source"])
        source_name = (
            source.name
            if isinstance(source, GuildChannel)
            else f"DM ({forward['source']})"
            if source
            else f"Unknown ({forward['source']})"
        )
        forward_list += f"{i}. {source_name} → Webhook\n"

    await message.reply(forward_list)


async def process_forward(message):
    """Process message forwarding"""
    
    settings = load_settings()

    for forward in settings["forwards"]:
        if message.channel.id == forward["source"]:
            webhook_url = forward["webhook"]

            # Set webhook username to the original author's display name
            username = message.author.display_name

            content = message.content

            # Handle attachments
            if message.attachments:
                attachments_text = "\n".join([att.url for att in message.attachments])
                if content:
                    content += "\n" + attachments_text
                else:
                    content = attachments_text

            # Send via webhook with custom username
            payload = {"content": content, "username": username}

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(webhook_url, json=payload) as response:
                        if response.status not in [200, 204]:
                            print(f"Error forwarding message: HTTP {response.status}")
            except Exception as e:
                print(f"Error forwarding message: {e}")


# Run the bot using BOT_TOKEN environment variable
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("Error: BOT_TOKEN environment variable not set")
    exit(1)
client.run(BOT_TOKEN)
