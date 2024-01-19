from hydrogram import Client, filters
from shared_config import shared_object


@Client.on_message(
    filters.user(shared_object.clients["super_admin"]) & filters.command("logfile", prefixes="!"), group=-1
)
async def logfile(client, message):
    """
    Returns the logfile
    """

    try:
        await message.reply_document(document="logfile.log", quote=True)
    except ValueError as error:
        await message.reply(error, quote=True)

    message.stop_propagation()
