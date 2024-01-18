from hydrogram import enums


async def get_chat_details(client, message):
    # if there is username specified take it as chat id else take current chat id from message
    chat = message.command[1] if len(message.command) == 2 else message.chat.id

    try:
        chat_object = await client.get_chat(chat)
    except Exception as e:
        await message.reply(e)
        return None
    else:
        if chat_object.type == enums.ChatType.PRIVATE:
            await message.reply("Specified id or username is not a group or channel")
            return None
        else:
            return chat_object
