from django.db import models
import uuid
from django.utils import timezone


# def generate_unique_uuid(model=None, field='code'):
#     unique_id = uuid.uuid4()  # or some hex represenation

#     filter = {field: unique_id}
#     exists = model.objects.filter(**filter).exists()
#     while exists:
#         unique_id = uuid.uuid4()  # or some hex represenation
#         filter = {field: unique_id}
#         exists = model.objects.filter(**filter).exists()

#     return unique_id


class CurrentConifgKeys(models.TextChoices):
    PRIVATE_CHANNEL = "PC", "Private Channel"
    LOG_CHANNEL = "LC", "Log Channel"
    TIMEOUT = "T", "Timeout"


class Config(models.Model):
    key = models.TextField(unique=True, choices=CurrentConifgKeys)
    value = models.TextField()


#     # https://www.cloudtruth.com/blog/self-validating-django-models#:~:text=You%20see%2C%20Django%20models%20allow,run%20the%20full_clean()%20method.
#     def save(self, *args, **kwargs):
#         self.full_clean()
#         return super().save(*args, **kwargs)


class ConversationType(models.TextChoices):
    NEW_QUOTE = "NQ", "New Quote"
    RESPONSE_TO_QUOTE = "RQ", "Response To Quote"
    NEW_SALE = "NS", "New Sale"
    RESPONSE_TO_SALE = "RS", "Response To Sale"


class Questions(models.Model):
    question_order = models.IntegerField()
    question_text = models.TextField()

    regex_pattern = models.TextField(blank=True, null=True)
    error_response = models.TextField(blank=True, null=True)

    is_private_question = models.BooleanField(default=False)

    conversation_type = models.TextField(choices=ConversationType)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class QnA(models.Model):
    from_user_id = models.BigIntegerField()
    response_text = models.TextField(default="")
    unique_id = models.TextField(unique=True, default=uuid.uuid4)
    question_order = models.IntegerField()
    question_text = models.TextField()

    regex_pattern = models.TextField(blank=True, null=True)
    error_response = models.TextField(blank=True, null=True)

    is_private_question = models.BooleanField()

    conversation_type = models.TextField(choices=ConversationType)
    linked_ad = models.ForeignKey("Ads", on_delete=models.CASCADE, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


# Questions(question_order=1, question_text="public", is_private_question=False, conversation_type=ConversationType.NEW_QUOTE).save()
# Questions(question_order=2, question_text="private", is_private_question=True, conversation_type=ConversationType.NEW_QUOTE).save()
# Questions(question_order=1, question_text="public", is_private_question=False, conversation_type=ConversationType.RESPONSE_TO_QUOTE).save()
# Questions(question_order=2, question_text="private", is_private_question=True, conversation_type=ConversationType.RESPONSE_TO_QUOTE).save()
class Ads(models.Model):
    from_user_id = models.BigIntegerField()
    unique_id = models.TextField(unique=True, default=uuid.uuid4)
    added_time = models.DateTimeField(default=timezone.now)
    channel_id = models.BigIntegerField()
    channel_message_id = models.BigIntegerField()
    group_id = models.BigIntegerField(blank=True, null=True)
    group_message_id = models.BigIntegerField(blank=True, null=True)

    conversation_type = models.TextField(choices=ConversationType)

    direct_forward = models.BooleanField(default=False)

    accepted_offer = models.ForeignKey("Replies", blank=True, null=True, on_delete=models.CASCADE)

    is_accepted = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)


class QnAForAds(models.Model):
    from_user_id = models.BigIntegerField()
    response_text = models.TextField()
    unique_id = models.TextField(unique=True, default=uuid.uuid4)
    ad = models.ForeignKey(Ads, on_delete=models.CASCADE)

    question_order = models.IntegerField()
    question_text = models.TextField()

    regex_pattern = models.TextField(blank=True, null=True)
    error_response = models.TextField(blank=True, null=True)

    is_private_question = models.BooleanField()

    conversation_type = models.TextField(choices=ConversationType)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Replies(models.Model):
    from_user_id = models.BigIntegerField()
    unique_id = models.TextField(unique=True, default=uuid.uuid4)
    added_time = models.DateTimeField(default=timezone.now)
    linked_ad = models.ForeignKey(Ads, on_delete=models.CASCADE)

    conversation_type = models.TextField(choices=ConversationType)
    is_shared_with_author = models.BooleanField(default=False)


class QnAForReplies(models.Model):
    from_user_id = models.BigIntegerField()
    response_text = models.TextField()
    unique_id = models.TextField(unique=True, default=uuid.uuid4)
    replies = models.ForeignKey(Replies, on_delete=models.CASCADE)

    question_order = models.IntegerField()
    question_text = models.TextField()

    regex_pattern = models.TextField(blank=True, null=True)
    error_response = models.TextField(blank=True, null=True)

    is_private_question = models.BooleanField()

    conversation_type = models.TextField(choices=ConversationType)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class BotAdmins(models.Model):
    user_id = models.BigIntegerField(unique=True)
    name = models.TextField()


class BrokerChannels(models.Model):
    group_id = models.BigIntegerField(unique=True)
    title = models.TextField()


class AdminChannels(models.Model):
    group_id = models.BigIntegerField(unique=True)
    title = models.TextField()
