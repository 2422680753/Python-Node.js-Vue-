from flask import Blueprint, request, jsonify
from services.language_detector import detect_language
from services.multilingual_detector import multilingual_detector, CodeSwitchAnalysis
from services.intent_classifier import intent_classifier
from services.bilingual_intent_classifier import bilingual_intent_classifier
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

@api_bp.route('/detect-multilingual', methods=['POST'])
def api_detect_multilingual():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    check_code_switching = data.get('checkCodeSwitching', True)
    
    analysis = multilingual_detector.analyze_multilingual(text, check_code_switching)
    
    convert_analysis = {
        'hasCodeSwitching': analysis.has_code_switching,
        'detectedLanguages': analysis.detected_languages,
        'languageDistribution': analysis.language_distribution,
        'segments': [
            {
                'language': seg.language,
                'text': seg.text,
                'startIndex': seg.start_index,
                'endIndex': seg.end_index,
                'confidence': seg.confidence
            }
            for seg in analysis.segments
        ],
        'dominantLanguage': analysis.dominant_language,
        'dominantIntentLanguage': analysis.dominant_intent_language,
        'isBilingual': analysis.is_bilingual,
        'switchPoints': analysis.switch_points,
        'languageSequence': analysis.language_sequence
    }
    
    return jsonify({
        'success': True,
        'data': convert_analysis
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
    use_bilingual = data.get('useBilingual', True)
    context_intents = data.get('contextIntents', None)
    
    if use_bilingual:
        result = bilingual_intent_classifier.classify_bilingual_intent(
            text, language, context_intents
        )
    else:
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
    use_bilingual = data.get('useBilingual', True)
    context_intents = data.get('contextIntents', None)
    
    multilingual_analysis = multilingual_detector.analyze_multilingual(text, True)
    
    language_result = detect_language(text)
    source_lang = language_result.get('language', 'en')
    
    if use_bilingual:
        intent_result = bilingual_intent_classifier.classify_bilingual_intent(
            text, source_lang, context_intents
        )
    else:
        intent_result = intent_classifier.classify(text, source_lang)
    
    translation_result = translate_text(text, target_lang, source_lang)
    
    response_result = generate_response(text, context, source_lang)
    
    return jsonify({
        'success': True,
        'data': {
            'language': language_result,
            'multilingualAnalysis': {
                'hasCodeSwitching': multilingual_analysis.has_code_switching,
                'detectedLanguages': multilingual_analysis.detected_languages,
                'languageDistribution': multilingual_analysis.language_distribution,
                'dominantLanguage': multilingual_analysis.dominant_language,
                'dominantIntentLanguage': multilingual_analysis.dominant_intent_language,
                'isBilingual': multilingual_analysis.is_bilingual,
                'segments': [
                    {
                        'language': seg.language,
                        'text': seg.text,
                        'confidence': seg.confidence
                    }
                    for seg in multilingual_analysis.segments
                ]
            },
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
        'escalationThreshold': config.ESCALATION_THRESHOLD,
        'features': {
            'codeSwitchingDetection': True,
            'bilingualIntentClassification': True,
            'multilingualAnalysis': True
        }
    })
