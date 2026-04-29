from langdetect import detect, LangDetectException
from services.multilingual_detector import multilingual_detector

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
            'confidence': 0.5,
            'isCodeSwitching': False,
            'languageDistribution': {},
            'dominantIntentLanguage': 'en'
        }
    
    enhanced_result = multilingual_detector.detect_language_enhanced(text)
    
    if enhanced_result.get('isCodeSwitching'):
        return enhanced_result
    
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
            'detected': detected,
            'isCodeSwitching': False,
            'languageDistribution': {mapped_lang: 1.0},
            'dominantIntentLanguage': mapped_lang
        }
        
    except LangDetectException:
        return {
            'language': 'en',
            'confidence': 0.5,
            'isCodeSwitching': False,
            'languageDistribution': {'en': 1.0},
            'dominantIntentLanguage': 'en'
        }

def detect_language_enhanced(text):
    return multilingual_detector.detect_language_enhanced(text)

def analyze_code_switching(text):
    analysis = multilingual_detector.analyze_code_switching(text)
    return {
        'primary_language': analysis.primary_language,
        'is_code_switching': analysis.is_code_switching,
        'segments': [
            {
                'text': s.text,
                'language': s.language,
                'start_idx': s.start_idx,
                'end_idx': s.end_idx,
                'confidence': s.confidence
            }
            for s in analysis.segments
        ],
        'language_distribution': analysis.language_distribution,
        'switch_points': analysis.switch_points,
        'dominant_intent_language': analysis.dominant_intent_language
    }

def extract_bilingual_keywords(text):
    return multilingual_detector.extract_all_keywords(text)

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
