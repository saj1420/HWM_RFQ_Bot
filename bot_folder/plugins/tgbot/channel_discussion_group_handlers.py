import asyncio

from hydrogram import Client, filters
from db.models import BrokerChannels

from shared_config import shared_object


async def get_top_message_object(client, message):
    if message.reply_to_top_message_id:
        top_message = await client.get_messages(message.chat.id, message.reply_to_top_message_id)
    elif message.reply_to_message:
        top_message = message.reply_to_message
    else:
        top_message = None

    return top_message


async def is_admin(message):
    if message.from_user:
        user_id = message.from_user.id
        return user_id in shared_object.clients["bot_admins"]

    if message.sender_chat:
        return message.sender_chat.id == message.chat.id

    return None


@Client.on_message(filters.group & filters.reply & filters.command("close", prefixes="!"))
async def close_discussion_by_announcement_message(client, message):
    top_message = await get_top_message_object(client, message)

    if top_message.forward_from_chat is None:
        return None

    is_forwarded_from_broker_channel = await BrokerChannel.objects.filter(
        group_id=top_message.forward_from_chat.id
    ).aexists()

    if is_forwarded_from_broker_channel is False:
        return None

    if await is_admin(message) is False:
        return None

    message_text = message.text.replace("!close", "", 1).strip()
    await message.delete()

    if message_text == "":
        temp_message = await top_message.reply("You need to specify final price per TH")
        await asyncio.sleep(2)
        await temp_message.delete()

    else:
        await top_message.reply(f"This deal has closed for a final price of {message_text} per TH")
