from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def add_keyboad_button_and_send_text_message(client, chat_id, text, keyboard_dict):
    """
    Create InlineKeyboardButton based on keyboard_dict and send with text to chat_id
    keyboard_dict => {"keyboard label": "call back data"}
    """

    keyboard_list = []
    for key, value in keyboard_dict.items():
        keyboard_list.append(
            [  # row
                InlineKeyboardButton(key, callback_data=value),
            ]
        )

    await client.send_message(
        chat_id,
        text,
        reply_markup=InlineKeyboardMarkup(keyboard_list),
    )
