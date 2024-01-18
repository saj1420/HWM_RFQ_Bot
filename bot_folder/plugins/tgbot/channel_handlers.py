from django.db import IntegrityError
from hydrogram import Client, filters

from db.models import Ads, AdminChannels, BrokerChannels, Config, CurrentConifgKeys

from shared_config import shared_object

from bot_folder.helpers import get_chat_details

from hydrogram import enums


async def is_admin(message):
    if message.from_user:
        user_id = message.from_user.id
        return user_id in shared_object.clients["bot_admins"]

    if message.sender_chat:
        return message.sender_chat.id == message.chat.id

    return None


# @Client.on_message(shared_object.clients["discussion_group"])
@Client.on_message(~filters.reply)
async def message_in_discussion_group(client, message, group=-1):
    # print(shared_object.clients["discussion_group"])
    # print()
    # print(message)
    if message.chat.id in shared_object.clients["discussion_group"]:
        print(message)

    group_id = message.chat.id

    if not message.forward_from_chat:
        return None

    channel_id = message.forward_from_chat.id
    channel_message_id = message.forward_from_message_id

    if channel_id:
        await Ads.objects.filter(channel_id=channel_id, channel_message_id=channel_message_id).aupdate(
            group_id=group_id, group_message_id=message.id
        )
    message.stop_propagation()


@Client.on_message(filters.command("setprivatedatachannel", prefixes="!"), group=-1)
async def setprivatechannel(client, message):
    if await is_admin(message) is False:
        return None

    chat_object = await get_chat_details(client, message)

    if chat_object and chat_object.type == enums.ChatType.CHANNEL:
        linked_chat = chat_object.linked_chat

        if linked_chat:
            if not await client.get_chat_member(linked_chat.id, "me"):
                await message.reply("You should add bot to the discussion group")
                return None
        else:
            await message.reply("You should create a discussion group and add bot to the discussion group")
            return None

        await Config.objects.aupdate_or_create(
            key=CurrentConifgKeys.PRIVATE_CHANNEL, defaults={'value': chat_object.id}
        )
        await message.reply(f"{chat_object.title} is now the private data channel")
        # shared_object.clients["discussion_group"] = filters.chat(linked_chat.id)
        shared_object.clients["discussion_group"].clear()
        shared_object.clients["discussion_group"].add(linked_chat.id)

    else:
        await message.reply("You can only channel as private data channel")

    message.stop_propagation()


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("addadminchannel", prefixes="!"))
async def add_admin_handler(client, message):
    chat_object = await get_chat_details(client, message)

    if chat_object:
        try:
            await AdminChannels.objects.acreate(group_id=chat_object.id, title=chat_object.title)
            await message.reply(f"Added {chat_object.title} to admin channels")
        except IntegrityError:
            await message.reply(f"{chat_object.title} already in admin channels")

    message.stop_propagation()


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("removeadminchannel", prefixes="!"))
async def remove_admin_handler(client, message):
    chat_object = await get_chat_details(client, message)

    if chat_object:
        await AdminChannels.objects.filter(group_id=chat_object.id).adelete()
        await message.reply(f"Removed {message.chat.title} from admin channels if they were in admin channels")

    message.stop_propagation()


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("listadminchannel", prefixes="!"))
async def list_admin_handler(client, message):
    output = "List of admin channels\n"

    async for channel in AdminChannels.objects.all():
        output += f"{channel.title} `{channel.group_id}`\n"

    output = output if output != "List of admin channels\n" else "No admin channels present in the db"
    await message.reply(output, quote=False)

    message.stop_propagation()


"""
BROKER CHANNEL
"""


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("addbrokerchannel", prefixes="!"), group=-1)
async def add_broker_handler(client, message):
    chat_object = await get_chat_details(client, message)

    if chat_object:
        try:
            await BrokerChannels.objects.acreate(group_id=chat_object.id, title=chat_object.title)
            await message.reply(f"Added {chat_object.title} to broker channels")
        except IntegrityError:
            await message.reply(f"{chat_object.title} already in broker channels")

    message.stop_propagation()


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("removebrokerchannel", prefixes="!"))
async def remove_broker_handler(client, message):
    chat_object = await get_chat_details(client, message)

    if chat_object:
        await BrokerChannels.objects.filter(group_id=chat_object.id).adelete()
        await message.reply(f"Removed {message.chat.title} from broker channels if they were in broker channels")

    message.stop_propagation()


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("listbrokerchannels", prefixes="!"))
async def list_broker_handler(client, message):
    output = "List of broker channels\n"

    async for channel in BrokerChannels.objects.all():
        output += f"{channel.title} `{channel.group_id}`\n"

    output = output if output != "List of broker channels\n" else "No broker channels present in the db"
    await message.reply(output, quote=False)

    message.stop_propagation()
