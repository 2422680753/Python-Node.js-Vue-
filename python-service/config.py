import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    REDIS_CACHE_TTL = int(os.getenv('REDIS_CACHE_TTL', 3600))
    
    INTENT_THRESHOLD = float(os.getenv('INTENT_THRESHOLD', 0.5))
    ESCALATION_THRESHOLD = float(os.getenv('ESCALATION_THRESHOLD', 0.4))
    
    LANGUAGES = ['zh', 'en', 'ja', 'ko', 'fr', 'de', 'es', 'pt', 'ar', 'ru']
    
    MODEL_PATH = os.getenv('MODEL_PATH', './models')
    KNOWLEDGE_BASE_PATH = os.getenv('KNOWLEDGE_BASE_PATH', './knowledge')

config = Config()
