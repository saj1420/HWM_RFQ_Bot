async def get_user_details(client, message):
    user = message.command[1] if len(message.command) == 2 else ""

    if user == "":
        await message.reply("Specify user id or username")
        return None
    try:
        user_object = await client.get_users(user)
    except IndexError:
        await message.reply("Specified id or username is not a user")
        return None
    except Exception as e:
        # If bot cant find user from the information provided <username or user ID>,
        # send a clear error message why bot cant find the user
        await message.reply(e)
        return None
    else:
        return user_object
