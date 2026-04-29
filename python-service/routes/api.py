from flask import Blueprint, request, jsonify
from services.language_detector import detect_language
from services.intent_classifier import intent_classifier
from services.response_generator import translate_text, generate_response
from services.knowledge_base import get_knowledge_base, should_escalate_intent
from config import config

api_bp = Blueprint('api', __name__)

@api_bp.route('/detect-language', methods=['POST'])
def api_detect_language():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    result = detect_language(text)
    
    return jsonify({
        'success': True,
        'data': result
    })

@api_bp.route('/translate', methods=['POST'])
def api_translate():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    target_lang = data.get('targetLang', 'en')
    source_lang = data.get('sourceLang', None)
    
    if target_lang not in config.LANGUAGES:
        return jsonify({
            'success': False,
            'error': f'Invalid target language. Supported: {config.LANGUAGES}'
        }), 400
    
    result = translate_text(text, target_lang, source_lang)
    
    return jsonify({
        'success': True,
        'data': result
    })

@api_bp.route('/intent', methods=['POST'])
def api_intent():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    language = data.get('language', 'en')
    
    result = intent_classifier.classify(text, language)
    
    should_escalate = should_escalate_intent(result.get('intent', 'unknown')) or \
                       result.get('confidence', 0) < config.ESCALATION_THRESHOLD
    
    return jsonify({
        'success': True,
        'data': {
            **result,
            'shouldEscalate': should_escalate,
            'escalationThreshold': config.ESCALATION_THRESHOLD
        }
    })

@api_bp.route('/entities', methods=['POST'])
def api_entities():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    language = data.get('language', 'en')
    
    result = intent_classifier.classify(text, language)
    
    return jsonify({
        'success': True,
        'data': {
            'entities': result.get('entities', []),
            'text': text,
            'language': language
        }
    })

@api_bp.route('/generate-response', methods=['POST'])
def api_generate_response():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    context = data.get('context', {})
    language = data.get('language', 'en')
    
    result = generate_response(text, context, language)
    
    return jsonify({
        'success': True,
        'data': result
    })

@api_bp.route('/intents', methods=['GET'])
def api_list_intents():
    intents = intent_classifier.get_all_intents()
    
    return jsonify({
        'success': True,
        'data': {
            'intents': intents,
            'total': len(intents),
            'languages': config.LANGUAGES
        }
    })

@api_bp.route('/languages', methods=['GET'])
def api_list_languages():
    languages_info = [
        {'code': 'zh', 'name': '中文', 'englishName': 'Chinese'},
        {'code': 'en', 'name': 'English', 'englishName': 'English'},
        {'code': 'ja', 'name': '日本語', 'englishName': 'Japanese'},
        {'code': 'ko', 'name': '한국어', 'englishName': 'Korean'},
        {'code': 'fr', 'name': 'Français', 'englishName': 'French'},
        {'code': 'de', 'name': 'Deutsch', 'englishName': 'German'},
        {'code': 'es', 'name': 'Español', 'englishName': 'Spanish'},
        {'code': 'pt', 'name': 'Português', 'englishName': 'Portuguese'},
        {'code': 'ar', 'name': 'العربية', 'englishName': 'Arabic'},
        {'code': 'ru', 'name': 'Русский', 'englishName': 'Russian'}
    ]
    
    return jsonify({
        'success': True,
        'data': {
            'languages': languages_info,
            'total': len(languages_info)
        }
    })

@api_bp.route('/analyze', methods=['POST'])
def api_full_analyze():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    target_lang = data.get('targetLang', 'en')
    context = data.get('context', {})
    
    language_result = detect_language(text)
    source_lang = language_result.get('language', 'en')
    
    intent_result = intent_classifier.classify(text, source_lang)
    
    translation_result = translate_text(text, target_lang, source_lang)
    
    response_result = generate_response(text, context, source_lang)
    
    return jsonify({
        'success': True,
        'data': {
            'language': language_result,
            'intent': intent_result,
            'translation': translation_result,
            'response': response_result
        }
    })

@api_bp.route('/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'healthy',
        'service': 'nlp-translation-service',
        'languages': config.LANGUAGES,
        'intentThreshold': config.INTENT_THRESHOLD,
        'escalationThreshold': config.ESCALATION_THRESHOLD
    })
