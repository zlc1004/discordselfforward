import discord
import json
import os

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


# # Bot setup
# intents = discord.Intents.default()
# intents.message_content = True
# intents.messages = True

# client = discord.Client(intents=intents)

client = discord.Client()

# Store active menus and waiting states
active_menus = {}
add_forward_waiting = {}
remove_forward_waiting = {}


@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")


@client.event
async def on_message(message):
    # Skip bot's own messages
    if message.author == client.user:
        return

    # Check for +menu command
    if message.content.strip() == "+menu":
        await handle_menu_command(message)
        return

    # Check if this is a menu response
    if message.author.id in active_menus and not message.content.startswith("+"):
        await handle_menu_response(message)
        return

    # Check if this is an add forward response
    if message.author.id in add_forward_waiting and not message.content.startswith("+"):
        await process_add_forward(message)
        return

    # Check if this is a remove forward response
    if message.author.id in remove_forward_waiting and not message.content.startswith(
        "+"
    ):
        await process_remove_forward(message)
        return

    # Process message forwarding
    await process_forward(message)


async def handle_menu_command(message):
    """Handle +menu command"""
    if message.author.id in active_menus:
        await message.reply(
            "You already have an active menu. Please complete or cancel it first."
        )
        return

    menu_msg = await message.reply(
        "**Message Forwarding Menu**\n\n"
        "1. Add forward - Add a new channel forward\n"
        "2. Remove forward - Remove an existing forward\n"
        "3. List forwards - Show all active forwards\n\n"
        "Reply with the number (1-3) to select an option."
    )

    active_menus[message.author.id] = {"message": menu_msg, "channel": message.channel}


async def handle_menu_response(message):
    """Handle menu option selection"""
    menu_data = active_menus[message.author.id]

    if message.content.strip() == "1":
        await handle_add_forward(message)
    elif message.content.strip() == "2":
        await handle_remove_forward(message)
    elif message.content.strip() == "3":
        await handle_list_forwards(message)
    else:
        await message.reply("Invalid option. Please reply with 1, 2, or 3.")
        return

    del active_menus[message.author.id]


async def handle_add_forward(message):
    """Handle add forward option"""
    msg = await message.reply(
        "**Add Forward**\n\n"
        "Please provide two channel IDs separated by a space.\n"
        "Format: `source_channel_id target_channel_id`\n\n"
        "Messages from the source channel will be forwarded to the target channel."
    )
    add_forward_waiting[message.author.id] = {
        "channel": message.channel,
        "message": msg,
    }


async def process_add_forward(message):
    """Process the add forward input"""
    data = add_forward_waiting.pop(message.author.id)

    try:
        parts = message.content.strip().split()
        if len(parts) != 2:
            await message.reply(
                "Invalid format. Please provide exactly two channel IDs separated by a space."
            )
            return

        source_id = int(parts[0])
        target_id = int(parts[1])

        # Verify channels exist
        source_channel = client.get_channel(source_id)
        target_channel = client.get_channel(target_id)

        if not source_channel:
            await message.reply(
                f"Source channel {source_id} not found or bot doesn't have access."
            )
            return

        if not target_channel:
            await message.reply(
                f"Target channel {target_id} not found or bot doesn't have access."
            )
            return

        # Load settings and add forward
        settings = load_settings()

        # Check if forward already exists
        for forward in settings["forwards"]:
            if forward["source"] == source_id and forward["target"] == target_id:
                await message.reply("This forward already exists!")
                return

        settings["forwards"].append({"source": source_id, "target": target_id})

        save_settings(settings)

        await message.reply(
            f"✅ Forward added successfully!\n"
            f"Source: {source_channel.name} ({source_id})\n"
            f"Target: {target_channel.name} ({target_id})"
        )

    except ValueError:
        await message.reply(
            "Invalid channel IDs. Please provide valid numeric channel IDs."
        )
    except Exception as e:
        await message.reply(f"Error adding forward: {str(e)}")


async def handle_remove_forward(message):
    """Handle remove forward option"""
    settings = load_settings()

    if not settings["forwards"]:
        await message.reply("No forwards to remove.")
        return

    forward_list = "**Active Forwards:**\n\n"
    for i, forward in enumerate(settings["forwards"], 1):
        source = client.get_channel(forward["source"])
        target = client.get_channel(forward["target"])
        source_name = source.name if source else "Unknown"
        target_name = target.name if target else "Unknown"
        forward_list += f"{i}. {source_name} → {target_name}\n"

    forward_list += "\nReply with the number of the forward to remove."

    msg = await message.reply(forward_list)
    remove_forward_waiting[message.author.id] = {
        "channel": message.channel,
        "message": msg,
        "forwards": settings["forwards"],
    }


async def process_remove_forward(message):
    """Process the remove forward input"""
    data = remove_forward_waiting.pop(message.author.id)
    forwards = data["forwards"]

    try:
        index = int(message.content.strip()) - 1
        if index < 0 or index >= len(forwards):
            await message.reply(
                f"Invalid number. Please choose between 1 and {len(forwards)}."
            )
            return

        removed = forwards.pop(index)

        settings = load_settings()
        settings["forwards"] = forwards
        save_settings(settings)

        source = client.get_channel(removed["source"])
        target = client.get_channel(removed["target"])
        source_name = source.name if source else "Unknown"
        target_name = target.name if target else "Unknown"

        await message.reply(f"✅ Removed forward: {source_name} → {target_name}")

    except ValueError:
        await message.reply("Please provide a valid number.")
    except Exception as e:
        await message.reply(f"Error removing forward: {str(e)}")


async def handle_list_forwards(message):
    """Handle list forwards option"""
    settings = load_settings()

    if not settings["forwards"]:
        await message.reply("No active forwards.")
        return

    forward_list = "**Active Forwards:**\n\n"
    for i, forward in enumerate(settings["forwards"], 1):
        source = client.get_channel(forward["source"])
        target = client.get_channel(forward["target"])
        source_name = source.name if source else f"Unknown ({forward['source']})"
        target_name = target.name if target else f"Unknown ({forward['target']})"
        forward_list += f"{i}. {source_name} → {target_name}\n"

    await message.reply(forward_list)


async def process_forward(message):
    """Process message forwarding"""
    if message.author == client.user:
        return

    settings = load_settings()

    for forward in settings["forwards"]:
        if message.channel.id == forward["source"]:
            target_channel = client.get_channel(forward["target"])
            if target_channel:
                # Format: displayname(@username): message
                author_name = message.author.display_name
                author_username = message.author.name
                content = message.content

                # Handle attachments
                attachments = ""
                if message.attachments:
                    attachments = "\n" + "\n".join(
                        [att.url for att in message.attachments]
                    )

                forwarded_message = (
                    f"**{author_name}** (@{author_username}): {content}{attachments}"
                )

                try:
                    await target_channel.send(forwarded_message)
                except Exception as e:
                    print(f"Error forwarding message: {e}")


# Run the bot using BOT_TOKEN environment variable
client.run(os.environ.get("BOT_TOKEN"))
