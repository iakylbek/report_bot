import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_ID = [874928357]

BOT_TOKEN = os.getenv("BOT_TOKEN")

FILE_NAME = "data.xlsx"
FILE_PATH = os.path.abspath(FILE_NAME)
