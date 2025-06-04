import os
from dotenv import load_dotenv
load_dotenv()
API_TOKEN=os.getenv("API_TOKEN")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
AUTHORIZED_USER_IDS=[int(x) for x in os.getenv("AUTHORIZED_USER_IDS","").split(',') if x.strip()]
