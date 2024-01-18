import os
import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

django.setup()

from db.models import Questions
import ast


def load_question(data, conversation_type):
    Questions.objects.filter(conversation_type=conversation_type).delete()

    data = data.split("-----")

    for question_set in data:
        question_set = question_set.strip()
        fields = question_set.lstrip().split('\n')
        print(fields)

        # fields = [ast.literal_eval(i.strip()) if i.strip() else None for i in fields]

        new_fields = {'conversation_type': conversation_type}
        for i in fields:
            field_name, field_data = i.split(":", maxsplit=1)
            try:
                field_data = ast.literal_eval(field_data.strip())

            except Exception:
                field_data = field_data.strip()

            if field_data == "":
                field_data = None

            new_fields[field_name] = field_data

        Questions.objects.create(**new_fields)


NQ_DATA = """
question_order: 1 
question_text: Please provide your best contact Email.
regex_pattern: ^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+$
error_response: Please use proper email format and try again.
is_private_question: True
-----
question_order:2
question_text: ASIC model you are looking for?
-----
question_order: 3
question_text: Quantity of machines?
regex_pattern: ^.{0,15}$
error_response: COMEON !!!!!
-----
question_order: 4
question_text: What’s your target price per TH?
-----
question_order: 5
question_text: What is your timeline to make the purchase?
-----
question_order: 6 
question_text: Any notes you would like to share?
"""

load_question(NQ_DATA, 'NQ')

RQ_DATA = """
question_order: 1
question_text: Model
-----
question_order: 2
question_text: Quantity
-----
question_order: 3
question_text: Price per TH
-----
question_order: 4
question_text: Shipping Cost
-----
question_order: 5
question_text: Shipping Terms
-----
question_order: 6
question_text: Stock or futures, if futures, which batch?
-----
question_order: 7
question_text: Quote expiration date & time
-----
question_order: 8
question_text: notes
"""

load_question(RQ_DATA, 'RQ')
