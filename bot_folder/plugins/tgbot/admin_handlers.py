from django.db import IntegrityError
from hydrogram import Client, filters
from db.models import BotAdmins, Config, CurrentConifgKeys

from shared_config import shared_object

from bot_folder.helpers import get_user_details


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("settimeout", prefixes="!"))
async def set_timeout(client, message):
    timeout = message.replace("!settimeout", "")

    if not timeout.isdigit():
        message.reply("timeout number should be a digit")
        return None

    await Config.objects.acreate(key=CurrentConifgKeys.TIMEOUT, value=timeout)

    await message.reply(f"Timeout -- {timeout}")

    message.stop_propagation()


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("addadmin", prefixes="!"))
async def add_bot_admin(client, message):
    """
    This is a message handler to add new bot admin.
    The user must be super admin in order use this command.
    The command syntax is: !add_bot_admin <username or user ID>
    """

    user_object = await get_user_details(client, message)

    if user_object:
        if user_object.id == shared_object.clients["super_admin"]:
            pass

    if user_object:
        # If the <username or user ID> is valid, add that user as a bot admin
        name = user_object.first_name + (user_object.last_name or "")
        try:
            await BotAdmins.objects.acreate(user_id=user_object.id, name=name)
        except IntegrityError:
            await message.reply(f"{name} is already a bot admin")
        else:
            shared_object.clients["bot_admins"].add(user_object.id)
            await message.reply(f"Added {name} as bot admin")

    message.stop_propagation()


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("removeadmin", prefixes="!"))
async def remove_bot_admin(client, message):
    """
    This is a message handler to remove a user from bot admin list.
    The user must be super admin in order use this command.
    The command syntax is: !remove_bot_admin <username or user ID>
    """

    user_object = await get_user_details(client, message)

    if user_object:
        if user_object.id == shared_object.clients["super_admin"]:
            # dont remove super admin from bot admin
            pass

        else:
            name = user_object.first_name + (user_object.last_name or "")
            await BotAdmins.objects.filter(user_id=user_object.id).adelete()
            shared_object.clients["bot_admins"].discard(user_object.id)
            await message.reply(f"Removed {name} from bot admin if they were bot admin")

    message.stop_propagation()


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("listadmin", prefixes="!"))
async def list_bot_admin(client, message):
    """
    This is a message handler to list all bot admins.
    The user must be super admin in order use this command.
    The command syntax is: !list_bot_admin
    """

    output = "List of bot admins\n"

    # Refreshes bot admin set in memory aswell
    shared_object.clients["bot_admins"].clear()
    shared_object.clients["bot_admins"].add(shared_object.clients["super_admin"])

    async for admin in BotAdmins.objects.all():
        shared_object.clients["bot_admins"].add(admin.user_id)
        output += f"{admin.name } `{admin.user_id}`\n"

    output = output if output != "List of admins\n" else "No bot admins in the db"
    await message.reply(output, quote=False)

    message.stop_propagation()
