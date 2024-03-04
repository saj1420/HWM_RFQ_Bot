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
question_text: Primary Email Address:
regex_pattern: ^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+$
error_response: Please use proper email format and try again.
is_private_question: True
-----
question_order:2
question_text: Desired ASIC Model:
-----
question_order: 3
question_text: Quantity of Machines Needed:
regex_pattern: ^.{0,15}$
error_response: COMEON !!!!!
-----
question_order: 4
question_text: Target Price per TH:
-----
question_order: 5
question_text: Destination Country:
-----
question_order: 6 
question_text: Purchase Timeline:
-----
question_order: 7 
question_text: Any Additional Information:
"""

load_question(NQ_DATA, 'NQ')

RQ_DATA = """
question_order: 1
question_text: Model available:
-----
question_order: 2
question_text: Quantity available:
-----
question_order: 3
question_text: Offered price per TH:
-----
question_order: 4
question_text: Shipping cost per unit:
-----
question_order: 5
question_text: Shipping terms:
-----
question_order: 6
question_text: Specify batch:
-----
question_order: 7
question_text: Quote expiration date & time:
-----
question_order: 8
question_text: Additional information:
"""

load_question(RQ_DATA, 'RQ')
