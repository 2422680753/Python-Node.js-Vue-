from langdetect import detect, LangDetectException

SUPPORTED_LANGUAGES = {
    'zh-cn': 'zh',
    'zh-tw': 'zh',
    'en': 'en',
    'ja': 'ja',
    'ko': 'ko',
    'fr': 'fr',
    'de': 'de',
    'es': 'es',
    'pt': 'pt',
    'ar': 'ar',
    'ru': 'ru'
}

def detect_language(text):
    if not text or not text.strip():
        return {
            'language': 'en',
            'confidence': 0.5
        }
    
    try:
        detected = detect(text)
        mapped_lang = SUPPORTED_LANGUAGES.get(detected, 'en')
        
        confidence = 0.9 if mapped_lang != 'en' else 0.7
        
        if _contains_chinese(text):
            mapped_lang = 'zh'
            confidence = 0.95
        elif _contains_japanese(text):
            mapped_lang = 'ja'
            confidence = 0.95
        elif _contains_korean(text):
            mapped_lang = 'ko'
            confidence = 0.95
        elif _contains_arabic(text):
            mapped_lang = 'ar'
            confidence = 0.95
        elif _contains_cyrillic(text):
            mapped_lang = 'ru'
            confidence = 0.95
        
        return {
            'language': mapped_lang,
            'confidence': confidence,
            'detected': detected
        }
        
    except LangDetectException:
        return {
            'language': 'en',
            'confidence': 0.5
        }

def _contains_chinese(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False

def _contains_japanese(text):
    for char in text:
        if '\u3040' <= char <= '\u30ff' or '\u31f0' <= char <= '\u31ff':
            return True
    return False

def _contains_korean(text):
    for char in text:
        if '\uac00' <= char <= '\ud7af' or '\u1100' <= char <= '\u11ff':
            return True
    return False

def _contains_arabic(text):
    for char in text:
        if '\u0600' <= char <= '\u06ff' or '\u0750' <= char <= '\u077f':
            return True
    return False

def _contains_cyrillic(text):
    for char in text:
        if '\u0400' <= char <= '\u04ff':
            return True
    return False
