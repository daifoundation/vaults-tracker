import sys
import os
from dotenv import load_dotenv

PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))

# load secrets from the local .env file
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

sys.path.insert(0, PROJECT_ROOT)
from app import app as application