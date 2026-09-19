from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env.local', override=False)
VAR = Path(os.getenv('ANALYST_DATA_DIR', str(ROOT / 'var')))
MODEL = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
VERSION = '0.2.1'

def model_status():
    return {'configured': bool(os.getenv('OPENAI_API_KEY')), 'mode': 'live' if os.getenv('OPENAI_API_KEY') else 'demo', 'model': MODEL, 'provider': 'OpenAI Responses API'}
