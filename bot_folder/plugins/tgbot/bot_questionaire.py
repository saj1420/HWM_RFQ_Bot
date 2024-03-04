from hydrogram import Client, filters


from db.models import Questions, ConversationType, QnA

from bot_folder.helpers import add_keyboad_button_and_send_text_message
from bot_folder.helpers import does_input_string_match_pattern

from .enable_forward import has_private_forwards_handler_for_message_handlers


@Client.on_message(filters.group & filters.command("id", prefixes="/"), group=-1)
async def chat_id(client, message):
    await message.reply(message.chat.id)


@Client.on_message(filters.private & filters.command("continue_rfq", prefixes="/"), group=-1)
async def continue_questions(client, message):

    next_question_object = (
        await QnA.objects.filter(from_user_id=message.from_user.id).order_by("question_order").afirst()
    )

    next_question_object = (
        await QnA.objects.filter(from_user_id=message.from_user.id, response_text="")
        .order_by("question_order")
        .afirst()
    )

    if next_question_object:
        await message.reply(next_question_object.question_text)
    message.stop_propagation()


@Client.on_message(filters.private & filters.command("start", prefixes="/"), group=-1)
async def start(client, message):
    name = f"{message.from_user.first_name} {(message.from_user.last_name or '')}"
    user_id = message.from_user.id
    mention = f"[{name}](tg://user?id={user_id})"

    await has_private_forwards_handler_for_message_handlers(client, message)

    greetings = (
        f"Hey {mention}, thank you for reaching out for a quote request, "
        "please click /newquote below and fill out all the information, "
        "the quote request will propagate to our network of trusted brokers with solid reputations, "
        "and we will get back to you wit the best options as soon as possible."
    )

    await message.reply(greetings)
    message.stop_propagation()


async def initiate_questions(client, from_user_id, conversation_type, linked_ad=None):
    await QnA.objects.filter(from_user_id=from_user_id).adelete()

    QUERY = []
    async for question_data in Questions.objects.filter(conversation_type=conversation_type).order_by(
        "question_order",
    ):
        QUERY.append(
            QnA(
                from_user_id=from_user_id,
                question_order=question_data.question_order,
                question_text=question_data.question_text,
                regex_pattern=question_data.regex_pattern,
                error_response=question_data.error_response,
                is_private_question=question_data.is_private_question,
                conversation_type=question_data.conversation_type,
                linked_ad=linked_ad,
            )
        )

    await QnA.objects.abulk_create(QUERY)
    await first_question(client, from_user_id)


@Client.on_message(filters.private & filters.command("newquote", prefixes="/"), group=-1)
async def newquote(client, message):
    await has_private_forwards_handler_for_message_handlers(client, message)

    question_object = (
        await QnA.objects.filter(from_user_id=message.from_user.id, response_text="")
        .order_by("question_order")
        .afirst()
    )

    if not question_object:

        await message.reply('To submit RFQ, please provide the following information')
        await initiate_questions(
            client, from_user_id=message.from_user.id, conversation_type=ConversationType.NEW_QUOTE
        )
    else:

        await message.reply(
            "Complete answering pending questions, you cant have two conversation with bot\n/continue_rfq to repeat the question"
        )
    message.stop_propagation()


async def first_question(client, from_user_id):
    question_object = (
        await QnA.objects.filter(from_user_id=from_user_id, response_text="").order_by("question_order").afirst()
    )

    if question_object:
        await client.send_message(from_user_id, question_object.question_text)


@Client.on_message(filters.private, group=1)
async def questionaire(client, message):
    from_user_id = message.from_user.id

    if not message.text:
        return None

    response_text = message.text.strip()

    question_object = (
        await QnA.objects.filter(from_user_id=from_user_id, response_text="").order_by("question_order").afirst()
    )

    if not question_object:
        message.continue_propagation()

    if question_object.regex_pattern:
        if not await does_input_string_match_pattern(response_text, question_object.regex_pattern):
            await message.reply(question_object.error_response)
            return None

    await QnA.objects.filter(id=question_object.id).aupdate(response_text=response_text)

    next_question_object = (
        await QnA.objects.filter(from_user_id=from_user_id, response_text="").order_by("question_order").afirst()
    )

    if next_question_object:
        await message.reply(next_question_object.question_text)
    else:
        # added_time = timezone.now()
        question_answer = []

        first_uuid = None

        async for conversation_data in QnA.objects.filter(
            from_user_id=from_user_id,
        ).order_by("question_order"):
            if first_uuid is None:
                first_uuid = conversation_data.unique_id
            question_answer.append(f"**{conversation_data.question_text}**\n{conversation_data.response_text}\n")

        # final_data = (
        #     f"**Date:** {added_time.strftime('%d %b %Y at %H:%M:%S %Z')}\n"
        #     f"**UserID:** `{from_user_id}`\n"
        #     f"**Name:** [{message.from_user.first_name} {(message.from_user.last_name or '')}](tg://user?id={from_user_id})\n"
        #     f"**Username:** {'@' + message.from_user.username if message.from_user.username else None}\n\n"
        # )

        final_data = "\n".join(question_answer)
        final_data = final_data.strip()

        # quote_id = xxhash.xxh32(final_data.encode("utf-8"), seed=12718745).hexdigest()

        await add_keyboad_button_and_send_text_message(
            client, from_user_id, final_data, {"SUBMIT": f"SUBMIT {first_uuid}", "CANCEL": f"CANCEL {first_uuid}"}
        )
