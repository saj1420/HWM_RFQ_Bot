from hydrogram.raw.functions.users import GetFullUser


async def has_private_forwards(client, user_id):
    user = await client.invoke(GetFullUser(id=await client.resolve_peer(user_id)))
    private_forward_name = user.full_user.private_forward_name

    # print(user)
    # print(private_forward_name)

    has_private_forward = not private_forward_name

    return has_private_forward


async def has_private_forwards_handler_for_message_handlers(client, message):
    if not await has_private_forwards(client, message.from_user.id):
        await message.reply("You should first enable forward message privacy settings to use this bot")
        message.stop_propagation()


async def has_private_forwards_handler_for_callbacks(client, callback_query):
    user_id = callback_query.from_user.id

    can_mention_in_other_chats = await has_private_forwards(client, user_id)

    return can_mention_in_other_chats


# from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# @Client.on_message(filters.private & filters.command("test1", prefixes="/"), group=-1)
# async def test1(client, message):
#     reply_keyboard = InlineKeyboardMarkup(
#         [
#             [
#                 InlineKeyboardButton("TEST1", callback_data=f"TEST1"),
#                 InlineKeyboardButton("TEST2", callback_data=f"TEST2"),
#             ],
#         ]
#     )

#     await client.send_message(message.from_user.id, "test1", reply_markup=reply_keyboard)


# @Client.on_callback_query(filters.regex("TEST1"))
# async def response_1(client, callback_query):
#     await callback_query.answer("test1", show_alert=True)


# @Client.on_callback_query(filters.regex("TEST2"))
# async def response_2(client, callback_query):
#     await callback_query.answer("test2", show_alert=False)


# @Client.on_message(filters.private & filters.command("test1", prefixes="/"), group=-1)
# async def test1(client, message):
#     reply_keyboard = InlineKeyboardMarkup(
#         [
#             [
#                 InlineKeyboardButton("Accept bid", callback_data=f"ACCEPT_BID"),
#                 InlineKeyboardButton("Cancel bid", callback_data=f"CANCEL_BID"),
#                 InlineKeyboardButton("Ask a question to admins", callback_data=f"ASK_QUESTION"),
#             ],
#         ]
#     )
#     await client.send_message(message.from_user.id, "test1", reply_markup=reply_keyboard)

# from pyrogram.types import ReplyKeyboardRemove


# @Client.on_message(filters.private & filters.command("test1", prefixes="/"), group=-1)
# async def test1(client, message):
#     await client.send_message(
#         message.from_user.id,
#         "This is a ReplyKeyboardMarkup example",
#         reply_markup=ReplyKeyboardRemove(),
#     )
