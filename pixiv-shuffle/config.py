import os
from dotenv import load_dotenv

load_dotenv()

PIXIV_REFRESH_TOKEN: str = os.environ.get("PIXIV_REFRESH_TOKEN", "")
BATCH_HOUR: int = int(os.environ.get("BATCH_HOUR", "3"))   # 3 AM by default
BATCH_MINUTE: int = int(os.environ.get("BATCH_MINUTE", "0"))
