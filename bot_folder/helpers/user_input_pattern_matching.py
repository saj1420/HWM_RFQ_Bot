import re


async def does_input_string_match_pattern(input_string, regex_pattern):
    return re.search(regex_pattern, input_string) is not None
