import logging
import uuid
import asyncio
from bot_folder.helpers import add_keyboad_button_and_send_text_message
from db.models import (
    Ads,
    BrokerChannels,
    Config,
    CurrentConifgKeys,
    QnA,
    QnAForAds,
    ConversationType,
    Replies,
    QnAForReplies,
)
from django.forms.models import model_to_dict
from django.utils import timezone
from hydrogram import Client, filters
from hydrogram.errors import BadRequest, Forbidden
from .enable_forward import has_private_forwards_handler_for_callbacks
from shared_config import shared_object
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .bot_questionaire import initiate_questions


# from ... import scheduler

mapping = {
    ConversationType.NEW_QUOTE: ConversationType.RESPONSE_TO_QUOTE,
    ConversationType.NEW_SALE: ConversationType.RESPONSE_TO_SALE,
}


async def public_ad_question(linked_ad):
    public_channel_data = []
    async for conversation_data in linked_ad.qnaforads_set.filter():
        if not conversation_data.is_private_question:
            public_channel_data.append(f"**{conversation_data.question_text}**\n{conversation_data.response_text}\n")

    public_channel_data_string = "\n".join(public_channel_data)

    return public_channel_data_string


async def send_pending_qna(client, from_user_id):
    if shared_object.clients["qna_queue_dict"].get(from_user_id):
        pending_qna = shared_object.clients["qna_queue_dict"][from_user_id].pop(0)
        conversation_type, linked_ad = pending_qna
        public_channel_data_string = await public_ad_question(linked_ad)

        if conversation_type == ConversationType.RESPONSE_TO_QUOTE:
            response_to = f"RFQ ID: `{linked_ad.unique_id}`"
        else:
            response_to = f"RFS ID: `{linked_ad.unique_id}`"

        public_channel_data_string = (
            f"Thank you for responding to {response_to}\nHere are the RFQ details:\n" + public_channel_data_string
        )
        public_channel_data_string += "\nPlease respond to the messages below and after you have answered all questions, you will be prompted to Submit your offer."

        await client.send_message(from_user_id, public_channel_data_string)
        await initiate_questions(
            client,
            from_user_id=from_user_id,
            conversation_type=conversation_type,
            linked_ad=linked_ad,
        )


async def forward_job(client, to_user_id, ad_id):
    ad_object = await Ads.objects.aget(id=ad_id)
    async for responses in Replies.objects.filter(linked_ad_id=ad_id, is_shared_with_author=False):
        message_text = []
        unique_id = responses.unique_id

        reply_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Accept bid", callback_data=f"ACCEPT_BID {unique_id}"),
                    InlineKeyboardButton("Cancel bid", callback_data=f"CANCEL_BID {ad_object.unique_id}"),
                ],
                [
                    InlineKeyboardButton("Ask a question to admins", callback_data=f"ASK_QUESTION {unique_id}"),
                ],
            ]
        )

        prefix_template_string = (
            f"**Unique ID:** {responses.unique_id}\n"
            f"**Date:** {responses.added_time.strftime('%d %b %Y at %H:%M:%S %Z')}\n"
        )

        async for conversation_data in responses.qnaforreplies_set.filter(is_private_question=False):
            message_text.append(f"**{conversation_data.question_text}**\n{conversation_data.response_text}\n")

        message_text_str = prefix_template_string + "\n".join(message_text)

        await client.send_message(ad_object.from_user_id, message_text_str, reply_markup=reply_keyboard)

    print(ad_id)
    print(ad_object.group_id)
    print(print(ad_object.group_message_id))


@Client.on_callback_query(filters.regex("^ACCEPT_BID\s\S+"))
async def accept_bid(client, callback_query):
    can_mention_in_other_chats = await has_private_forwards_handler_for_callbacks(client, callback_query)
    if not can_mention_in_other_chats:
        await callback_query.answer(
            "You should first enable forward message privacy settings to use this bot",
            show_alert=True,
        )

        return None

    unique_id = callback_query.data.replace("ACCEPT_BID", "").strip()
    print(unique_id)
    replies_object = await Replies.objects.select_related("linked_ad").aget(unique_id=unique_id)

    linked_ad = replies_object.linked_ad

    if linked_ad.is_accepted or linked_ad.is_cancelled:
        await client.edit_message_reply_markup(
            callback_query.message.chat.id,
            callback_query.message.id,
            reply_markup=None,
        )
        return None

    linked_ad.accepted_offer = replies_object
    linked_ad.is_accepted = True

    await linked_ad.asave()

    private_channel_data = []
    public_channel_data = []

    prefix_template_string = (
        f"**Unique ID:** {replies_object.unique_id}\n"
        f"**Date:** {replies_object.added_time.strftime('%d %b %Y at %H:%M:%S %Z')}\n"
    )

    async for conversation_data in replies_object.qnaforreplies_set.filter():
        private_channel_data.append(f"**{conversation_data.question_text}**\n{conversation_data.response_text}\n")

        if not conversation_data.is_private_question:
            public_channel_data.append(f"**{conversation_data.question_text}**\n{conversation_data.response_text}\n")

    private_channel_data_string = (
        "This quote has won the bid" + " " + prefix_template_string + "\n".join(private_channel_data)
    )
    public_channel_data_string = (
        "This quote has won the bid" + " " + prefix_template_string + "\n".join(public_channel_data)
    )

    group_id = linked_ad.group_id
    message_id = linked_ad.group_message_id

    await client.send_message(chat_id=group_id, text=private_channel_data_string, reply_to_message_id=message_id)

    async for broker_channel in BrokerChannels.objects.all():
        group_id = broker_channel.group_id
        await client.send_message(group_id, public_channel_data_string)

    await client.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.id,
        reply_markup=None,
    )


@Client.on_callback_query(filters.regex("^ASK_QUESTION\s\S+"))
async def ask_question(client, callback_query):
    can_mention_in_other_chats = await has_private_forwards_handler_for_callbacks(client, callback_query)
    if not can_mention_in_other_chats:
        await callback_query.answer(
            "You should first enable forward message privacy settings to use this bot",
            show_alert=True,
        )

        return None
    unique_id = callback_query.data.replace("ASK_QUESTION", "").strip()

    replies_object = await Replies.objects.select_related("linked_ad").aget(unique_id=unique_id)

    linked_ad = replies_object.linked_ad

    if linked_ad.is_accepted or linked_ad.is_cancelled:
        await client.edit_message_reply_markup(
            callback_query.message.chat.id,
            callback_query.message.id,
            reply_markup=None,
        )
        return None

    private_channel_data = []
    public_channel_data = []

    prefix_template_string = (
        f"**Unique ID:** {replies_object.unique_id}\n"
        f"**Date:** {replies_object.added_time.strftime('%d %b %Y at %H:%M:%S %Z')}\n"
    )

    async for conversation_data in replies_object.qnaforreplies_set.filter():
        private_channel_data.append(f"**{conversation_data.question_text}**\n{conversation_data.response_text}\n")

        if not conversation_data.is_private_question:
            public_channel_data.append(f"**{conversation_data.question_text}**\n{conversation_data.response_text}\n")

    private_channel_data_string = prefix_template_string + "\n".join(private_channel_data)

    group_id = linked_ad.group_id
    message_id = linked_ad.group_message_id

    from_user = callback_query.from_user
    private_channel_data_string = (
        f"[{from_user.first_name} {(from_user.last_name or '')}](tg://user?id={from_user.id}) like to ask questions about the offer below\n"
        + private_channel_data_string
    )
    await client.send_message(chat_id=group_id, text=private_channel_data_string, reply_to_message_id=message_id)
    await client.send_message(chat_id=group_id, text=private_channel_data_string)

    await client.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.id,
        reply_markup=None,
    )


@Client.on_callback_query(filters.regex("^CANCEL_BID\s\S+"))
async def cancel_bid(client, callback_query):
    unique_id = callback_query.data.replace("CANCEL_BID", "").strip()

    print(unique_id)
    ad_object = await Ads.objects.aget(unique_id=unique_id)

    if ad_object.is_accepted or ad_object.is_cancelled:
        await client.edit_message_reply_markup(
            callback_query.message.chat.id,
            callback_query.message.id,
            reply_markup=None,
        )
        return None

    ad_object.is_cancelled = True

    await ad_object.asave()

    await client.send_message(
        callback_query.from_user.id, "We have cancelled that bid IF it wasnt accepted or cancelled"
    )

    await client.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.id,
        reply_markup=None,
    )


@Client.on_callback_query(filters.regex("^SEND_OFFER\s\S+"))
async def send_offer(client, callback_query):
    can_mention_in_other_chats = await has_private_forwards_handler_for_callbacks(client, callback_query)
    if not can_mention_in_other_chats:
        await callback_query.answer(
            "You should first enable forward message privacy settings to use this bot",
            show_alert=True,
        )

        return None

    # await callback_query.answer(cache_time=100)

    unique_id = callback_query.data.replace("SEND_OFFER", "").strip()

    linked_ad = await Ads.objects.aget(unique_id=unique_id)

    if linked_ad.is_accepted or linked_ad.is_cancelled:
        new_message = "This bid isnt looking for new offers" + "\n\n" + callback_query.message.text

        await client.edit_message_text(
            callback_query.message.chat.id,
            callback_query.message.id,
            text=new_message,
            reply_markup=None,
        )
        return None

    conversation_type = mapping[linked_ad.conversation_type]

    question_object = (
        await QnA.objects.filter(from_user_id=callback_query.from_user.id, response_text="")
        .order_by("question_order")
        .afirst()
    )

    if not question_object:
        public_channel_data_string = await public_ad_question(linked_ad)
        if conversation_type == ConversationType.RESPONSE_TO_QUOTE:
            response_to = f"RFQ ID: `{linked_ad.unique_id}`"
        else:
            response_to = f"RFS ID: `{linked_ad.unique_id}`"

        public_channel_data_string = (
            f"Thank you for responding to {response_to}\nHere are the RFQ details:\n" + public_channel_data_string
        )
        public_channel_data_string += "\nPlease respond to the messages below and after you have answered all questions, you will be prompted to Submit your offer."
        await client.send_message(callback_query.from_user.id, public_channel_data_string)

        await initiate_questions(
            client,
            from_user_id=callback_query.from_user.id,
            conversation_type=conversation_type,
            linked_ad=linked_ad,
        )

    else:
        current_qna_from_user = shared_object.clients["qna_queue_dict"].get(callback_query.from_user.id, [])
        current_qna_from_user.append((conversation_type, linked_ad))
        shared_object.clients["qna_queue_dict"][callback_query.from_user.id] = current_qna_from_user

        await callback_query.answer(
            "We will send questions about this ad after you have answered pending questions about previous ones",
            show_alert=True,
        )


@Client.on_callback_query(filters.regex("^SUBMIT\s\S+"))
async def user_submit_callback_handler(client, callback_query):
    can_mention_in_other_chats = await has_private_forwards_handler_for_callbacks(client, callback_query)
    if not can_mention_in_other_chats:
        await callback_query.answer(
            "You should first enable forward message privacy settings to use this bot",
            show_alert=True,
        )

        return None

    await callback_query.answer(cache_time=100)
    from_user_id = callback_query.from_user.id
    user_object = await client.get_users(from_user_id)

    unique_id = callback_query.data.replace("SUBMIT", "").strip()

    await client.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.id,
        reply_markup=None,
    )

    if not await QnA.objects.filter(unique_id=unique_id, from_user_id=from_user_id).aexists():
        await client.send_message('Something went wrong, try entire steps again')
        return None

    new_unique_id = uuid.uuid4()
    added_time = timezone.now()

    private_channel_data = [
        f"**UserID:** `{from_user_id}`\n",
        f"**Name:** [{user_object.first_name} {(user_object.last_name or '')}](tg://user?id={from_user_id})\n",
        f"**Username:** {'@' + user_object.username if user_object.username else None}\n\n",
    ]

    public_channel_data = []

    prefix_template_string = (
        f"**Unique ID:** {new_unique_id}\n" f"**Date:** {added_time.strftime('%d %b %Y at %H:%M:%S %Z')}\n"
    )

    conversation_data_list = []

    async for conversation_data in (
        QnA.objects.filter(from_user_id=from_user_id).select_related('linked_ad').order_by("question_order")
    ):
        data = model_to_dict(conversation_data)
        data.pop('unique_id')
        conversation_data_list.append(data)

        private_channel_data.append(f"**{conversation_data.question_text}**\n{conversation_data.response_text}\n")
        if not conversation_data.is_private_question:
            public_channel_data.append(f"**{conversation_data.question_text}**\n{conversation_data.response_text}\n")

    linked_ad = conversation_data.linked_ad

    conversation_type = conversation_data.conversation_type
    private_channel_data_string = prefix_template_string + "\n".join(private_channel_data)
    public_channel_data_string = prefix_template_string + "\n".join(public_channel_data)

    if conversation_type in {ConversationType.NEW_QUOTE, ConversationType.NEW_SALE}:
        private_data_channel = await Config.objects.aget(key=CurrentConifgKeys.PRIVATE_CHANNEL)
        private_data_channel_id = private_data_channel.value
        channel_message = await client.send_message(private_data_channel_id, private_channel_data_string)
        channel_message_id = channel_message.id

        ad_object = await Ads.objects.acreate(
            from_user_id=from_user_id,
            unique_id=new_unique_id,
            added_time=added_time,
            channel_id=private_data_channel_id,
            channel_message_id=channel_message_id,
            conversation_type=conversation_type,
        )

        QUERY = []
        for conversation_data in conversation_data_list:
            conversation_data["ad"] = ad_object
            del conversation_data['linked_ad']
            QUERY.append(QnAForAds(**conversation_data))

        await QnAForAds.objects.abulk_create(QUERY)
        await QnA.objects.filter(from_user_id=from_user_id).adelete()

        response_to_user = f"Thank you for submitting your request! Your unique ID is: `{new_unique_id}`. Our team is actively sourcing the best offers through our verified brokers network and will provide you with an update at the earliest opportunity."

        await client.send_message(callback_query.message.chat.id, response_to_user)

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Send an offer", callback_data=f"SEND_OFFER {new_unique_id}"),
                ],
            ]
        )
        async for broker_channel in BrokerChannels.objects.all():
            group_id = broker_channel.group_id
            await client.send_message(group_id, public_channel_data_string, reply_markup=keyboard)

        timeout = await Config.objects.filter(key=CurrentConifgKeys.TIMEOUT).afirst()

        if timeout is None:
            timeout_in_seconds = 0
        else:
            timeout_in_seconds = int(timeout) * 60

        print("no forward")
        await asyncio.sleep(timeout_in_seconds)

        await ad_object.arefresh_from_db()

        ad_object.direct_forward = True
        print("yes forward")
        await ad_object.asave()
        await forward_job(client, from_user_id, ad_object.id)

    else:
        print(linked_ad.id)
        print(linked_ad.group_id)
        print(linked_ad.group_id)
        group_id = linked_ad.group_id

        message_id = linked_ad.group_message_id

        direct_forward = linked_ad.direct_forward

        await client.send_message(chat_id=group_id, text=private_channel_data_string, reply_to_message_id=message_id)

        replies_object = await Replies.objects.acreate(
            from_user_id=from_user_id,
            unique_id=new_unique_id,
            added_time=added_time,
            conversation_type=conversation_type,
            linked_ad=linked_ad,
        )

        QUERY = []
        for conversation_data in conversation_data_list:
            conversation_data["replies"] = replies_object
            del conversation_data['linked_ad']
            QUERY.append(QnAForReplies(**conversation_data))

        await QnAForReplies.objects.abulk_create(QUERY)
        await QnA.objects.filter(from_user_id=from_user_id).adelete()

        response_to_user = f"Thank you for submitting your offer. We'll notify you if your offer has been selected"
        await client.send_message(callback_query.message.chat.id, response_to_user)

        print(new_unique_id)
        print(replies_object)
        print(replies_object.unique_id)

        print(linked_ad.unique_id)
        print(linked_ad)
        print(linked_ad.unique_id)
        # reply_keyboard = InlineKeyboardMarkup(
        #     [
        #         [
        #             InlineKeyboardButton("Accept bid", callback_data=f"ACCEPT_BID {new_unique_id}"),
        #             InlineKeyboardButton("Cancel bid", callback_data=f"CANCEL_BID {linked_ad.unique_id}"),
        #         ],
        #     ]
        # )

        if direct_forward:
            # await client.send_message(linked_ad.from_user_id, public_channel_data_string, reply_markup=reply_keyboard)
            await forward_job(client, from_user_id, linked_ad.id)
            replies_object.is_shared_with_author = True

    await send_pending_qna(client, callback_query.from_user.id)


@Client.on_callback_query(filters.regex("^CANCEL\s\S+"))
async def user_cancel_callback_handler(client, callback_query):
    """
    This message handler handles the callback query when a user press CANCEL button
    after answering all the questions
    """
    await callback_query.answer(cache_time=100)

    await client.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.id,
        reply_markup=None,
    )

    await QnA.objects.filter(from_user_id=callback_query.from_user.id).adelete()

    response_to_user = "Your request has been cancelled\n"
    await client.send_message(callback_query.message.chat.id, response_to_user)

    await send_pending_qna(client, callback_query.from_user.id)


# @Client.on_callback_query(filters.regex(r"SEND"))
# async def admin_choice_callback_handler(client, callback_query):
#     await callback_query.answer(cache_time=100)

#     await client.edit_message_reply_markup(
#         callback_query.message.chat.id,
#         callback_query.message.id,
#         reply_markup=None,
#     )

#     final_message = callback_query.message.text
#     quote_id = final_message.split("\n")[0].strip()
#     quote_id = quote_id.replace("Quote ID:", "").strip()

#     question_answer = []
#     conversation_identifier_object = await ConversationIdentifier.objects.filter(quote_id=quote_id).afirst()

#     async for conversation_backup in ConversationBackups.objects.filter(
#         conversation_identifier=conversation_identifier_object.id
#     ).exclude(private_question=True):
#         question_answer.append(f"**{conversation_backup.question}**\n{conversation_backup.response}\n")

#     final_data = "\n".join(question_answer)
#     final_data = f"**Quote ID:** {quote_id}\n\n" + final_data

#     admin_broker_channel = await BrokerChannel.objects.filter(is_user=False).afirst()

#     try:
#         temp_message = await client.send_message(admin_broker_channel.group_id, final_data)
#         response = f"Quote sent to broker channel ([link of message in broker channel]({temp_message.link}))"
#         await client.send_message(callback_query.message.chat.id, response)

#     except BadRequest as e:
#         logging.exception(e)

#     async for broker_user in BrokerChannel.objects.filter(is_user=True):
#         try:
#             question = quote_id

#             await client.send_message(broker_user.group_id, final_data)

#             await Conversations.objects.aget_or_create(
#                 user_id=broker_user.group_id,
#                 question=question,
#                 conversation_type="bot message",
#             )

#             await Conversations.objects.filter(user_id=broker_user.group_id, conversation_type="bot message").exclude(
#                 question=question
#             ).adelete()

#         except Exception as e:
#             continue


# @Client.on_message(filters.private, group=1)
# async def response_from_brokers_test(client, message):
#     if not message.text:
#         message.continue_propagation()

#     user_id = message.from_user.id
#     name = message.from_user.first_name + (message.from_user.last_name or "")

#     try:
#         question_answered_to_object = await Conversations.objects.filter(
#             user_id=user_id, response="", conversation_type="bot message"
#         ).alatest("id")
#     except Conversations.DoesNotExist:
#         await message.reply("Send /newquote for new quote request")
#         message.continue_propagation()
#         return None

#     if not question_answered_to_object:
#         await message.reply("Send /newquote for new quote request")
#         message.continue_propagation()
#         return None

#     question = quote_id = question_answered_to_object.question.strip()
#     response = message.text.strip()

#     await Conversations.objects.filter(id=question_answered_to_object.id).adelete()

#     quote_conversation = await ConversationIdentifier.objects.filter(quote_id=quote_id).afirst()
#     discussion_group_id = quote_conversation.discussion_group_id
#     message_id = quote_conversation.message_id

#     response = f"{name} replied\n{response}"
#     try:
#         await client.send_message(chat_id=discussion_group_id, reply_to_message_id=message_id, text=response)
#     except Exception as e:
#         pass

#     await message.reply("Thank you for your response")

#     message.continue_propagation()


# @Client.on_message(filters.group)
# async def discussion_group(client, message):
#     if message.sender_chat:
#         first_broker_channel_object = await BrokerChannel.objects.filter(
#             group_id=message.sender_chat.id, is_user=False
#         ).afirst()

#         if first_broker_channel_object:
#             if first_broker_channel_object.group_id == message.sender_chat.id:
#                 discussion_group_id = message.chat.id
#                 message_id = message.id
#                 final_message = message.text.strip()
#                 quote_id = final_message.split("\n")[0].strip()
#                 quote_id = quote_id.replace("Quote ID:", "").strip()
#                 await ConversationIdentifier.objects.filter(quote_id=quote_id).aupdate(
#                     discussion_group_id=discussion_group_id, message_id=message_id
#                 )

#     message.continue_propagation()


# {
#     "_": "Message",
#     "id": 8,
#     "sender_chat": {
#         "_": "Chat",
#         "id": -1002125484620,
#         "type": "ChatType.CHANNEL",
#         "is_verified": false,
#         "is_restricted": false,
#         "is_creator": false,
#         "is_scam": false,
#         "is_fake": false,
#         "is_forum": false,
#         "title": "channel",
#         "username": "hjsksllslslskksks",
#         "has_protected_content": false
#     },
#     "date": "2023-12-19 21:34:20",
#     "chat": {
#         "_": "Chat",
#         "id": -1002125484620,
#         "type": "ChatType.CHANNEL",
#         "is_verified": false,
#         "is_restricted": false,
#         "is_creator": false,
#         "is_scam": false,
#         "is_fake": false,
#         "is_forum": false,
#         "title": "channel",
#         "username": "hjsksllslslskksks",
#         "has_protected_content": false
#     },
#     "mentioned": false,
#     "scheduled": false,
#     "from_scheduled": false,
#     "has_protected_content": false,
#     "text": "a",
#     "views": 1,
#     "forwards": 0,
#     "outgoing": false
# }

# {
#     "_": "Message",
#     "id": 26,
#     "sender_chat": {
#         "_": "Chat",
#         "id": -1002125484620,
#         "type": "ChatType.CHANNEL",
#         "is_verified": false,
#         "is_restricted": false,
#         "is_creator": false,
#         "is_scam": false,
#         "is_fake": false,
#         "is_forum": false,
#         "title": "channel",
#         "username": "hjsksllslslskksks",
#         "has_protected_content": false
#     },
#     "date": "2023-12-19 21:34:24",
#     "chat": {
#         "_": "Chat",
#         "id": -1002023778333,
#         "type": "ChatType.SUPERGROUP",
#         "is_verified": false,
#         "is_restricted": false,
#         "is_creator": false,
#         "is_scam": false,
#         "is_fake": false,
#         "is_forum": false,
#         "title": "channel chat",
#         "has_protected_content": false,
#         "permissions": {
#             "_": "ChatPermissions",
#             "can_send_messages": true,
#             "can_send_media_messages": true,
#             "can_send_other_messages": true,
#             "can_send_polls": true,
#             "can_add_web_page_previews": true,
#             "can_change_info": false,
#             "can_invite_users": false,
#             "can_pin_messages": false,
#             "can_manage_topics": true
#         }
#     },
#     "forward_from_chat": {
#         "_": "Chat",
#         "id": -1002125484620,
#         "type": "ChatType.CHANNEL",
#         "is_verified": false,
#         "is_restricted": false,
#         "is_creator": false,
#         "is_scam": false,
#         "is_fake": false,
#         "is_forum": false,
#         "title": "channel",
#         "username": "hjsksllslslskksks",
#         "has_protected_content": false
#     },
#     "forward_from_message_id": 8,
#     "forward_date": "2023-12-19 21:34:20",
#     "mentioned": false,
#     "scheduled": false,
#     "from_scheduled": false,
#     "has_protected_content": false,
#     "text": "a",
#     "views": 1,
#     "forwards": 0,
#     "outgoing": false
# }
