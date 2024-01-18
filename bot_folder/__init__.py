# Django specific settings
import os
import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

django.setup()

# from apscheduler.schedulers.asyncio import AsyncIOScheduler

# scheduler = AsyncIOScheduler()
# scheduler.start()
