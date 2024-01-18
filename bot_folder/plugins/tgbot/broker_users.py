from django.db import IntegrityError
from hydrogram import Client, filters
from db.models import BrokerChannels


from shared_config import shared_object


from bot_folder.helpers import get_user_details


# @Client.on_message()
# async def test1(client, message):
#     print(message)


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("addbroker", prefixes="!"))
async def add_broker_user_handler(client, message):
    """
    This is a message handler to add new bot admin.
    The user must be super admin in order use this command.
    The command syntax is: !add_bot_admin <username or user ID>
    """

    user_object = await get_user_details(client, message)

    if user_object:
        # If the <username or user ID> is valid, add that user as a bot admin
        name = user_object.first_name + (user_object.last_name or "")
        try:
            await BrokerChannels.objects.acreate(group_id=user_object.id, title=name, is_user=True)
        except IntegrityError:
            await message.reply(f"{name} is already a bot user")
        else:
            shared_object.clients["bot_admins"].add(user_object.id)
            await message.reply(f"Added user {name} to broker groups")

    message.stop_propagation()


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("removebroker", prefixes="!"))
async def remove_broker_user_handler(client, message):
    user_object = await get_user_details(client, message)

    if user_object:
        name = user_object.first_name + (user_object.last_name or "")
        await BrokerChannels.objects.filter(group_id=user_object.id, is_user=True).adelete()
        shared_object.clients["bot_admins"].discard(user_object.id)
        await message.reply(f"Removed {name} from broker groups if he was a broker user")

    message.stop_propagation()


@Client.on_message(shared_object.clients["bot_admins"] & filters.command("listbrokers", prefixes="!"))
async def list_broker_user_handler(client, message):
    output = "List of broker users\n"

    async for channel in BrokerChannels.objects.filter(is_user=True):
        output += f"{channel.title } `{channel.group_id}`\n"

    output = output if output != "List of broker users\n" else "No broker users in the db"
    await message.reply(output, quote=False)

    message.stop_propagation()
