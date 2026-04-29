from typing import Dict, Any
from services.language_detector import detect_language
from services.intent_classifier import intent_classifier
from services.knowledge_base import get_intent_response, should_escalate_intent

TRANSLATION_TEMPLATES = {
    'zh_to_en': {
        '你好': 'Hello',
        '您好': 'Hello',
        '订单': 'Order',
        '退款': 'Refund',
        '退货': 'Return',
        '物流': 'Logistics/Shipping',
        '支付': 'Payment',
        '信用卡': 'Credit card',
        '投诉': 'Complaint',
        '问题': 'Problem/Question',
        '价格': 'Price',
        '产品': 'Product',
        '商品': 'Product/Item',
        '发货': 'Ship/Delivery',
        '客服': 'Customer service',
        '人工': 'Human agent',
        '谢谢': 'Thank you',
        '再见': 'Goodbye',
        '请问': 'May I ask',
        '能否': 'Could you',
        '可以': 'Can/Could',
        '需要': 'Need',
        '想要': 'Want',
        '查询': 'Query/Check',
        '查看': 'View/Check',
        '取消': 'Cancel',
        '修改': 'Modify/Change',
        '更换': 'Exchange',
        '申请': 'Apply/Request'
    },
    'en_to_zh': {
        'hello': '你好',
        'hi': '你好',
        'order': '订单',
        'refund': '退款',
        'return': '退货',
        'shipping': '物流/发货',
        'delivery': '配送',
        'payment': '支付',
        'credit card': '信用卡',
        'complaint': '投诉',
        'problem': '问题',
        'issue': '问题',
        'price': '价格',
        'product': '产品',
        'item': '商品',
        'customer service': '客服',
        'agent': '客服/代理人',
        'human': '人工',
        'thank you': '谢谢',
        'thanks': '谢谢',
        'goodbye': '再见',
        'bye': '再见',
        'cancel': '取消',
        'change': '修改',
        'modify': '修改',
        'exchange': '更换',
        'apply': '申请',
        'request': '请求',
        'track': '追踪',
        'status': '状态',
        'help': '帮助',
        'assist': '协助'
    }
}

LANGUAGE_NAMES = {
    'zh': '中文',
    'en': 'English',
    'ja': '日本語',
    'ko': '한국어',
    'fr': 'Français',
    'de': 'Deutsch',
    'es': 'Español',
    'pt': 'Português',
    'ar': 'العربية',
    'ru': 'Русский'
}

def translate_text(text: str, target_lang: str, source_lang: str = None) -> Dict[str, Any]:
    if not text or not text.strip():
        return {
            'translatedText': text,
            'sourceLang': source_lang or 'en',
            'targetLang': target_lang,
            'method': 'original'
        }
    
    if source_lang is None:
        lang_detection = detect_language(text)
        source_lang = lang_detection.get('language', 'en')
    
    if source_lang == target_lang:
        return {
            'translatedText': text,
            'sourceLang': source_lang,
            'targetLang': target_lang,
            'method': 'same_language'
        }
    
    translated = _simple_translate(text, source_lang, target_lang)
    
    return {
        'translatedText': translated,
        'sourceLang': source_lang,
        'targetLang': target_lang,
        'method': 'template_based'
    }

def _simple_translate(text: str, source_lang: str, target_lang: str) -> str:
    if source_lang == 'zh' and target_lang == 'en':
        return _zh_to_en_translate(text)
    elif source_lang == 'en' and target_lang == 'zh':
        return _en_to_zh_translate(text)
    else:
        return _generic_translate(text, source_lang, target_lang)

def _zh_to_en_translate(text: str) -> str:
    result = text
    
    for zh_term, en_term in TRANSLATION_TEMPLATES['zh_to_en'].items():
        if zh_term in result:
            result = result.replace(zh_term, en_term)
    
    if result == text:
        result = f"[Translation needed: {text}]"
    
    return result

def _en_to_zh_translate(text: str) -> str:
    result = text.lower()
    
    for en_term, zh_term in TRANSLATION_TEMPLATES['en_to_zh'].items():
        if en_term in result:
            result = result.replace(en_term, zh_term)
    
    if result == text.lower():
        result = f"[需要翻译: {text}]"
    
    return result

def _generic_translate(text: str, source_lang: str, target_lang: str) -> str:
    source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    
    return f"[需要从 {source_name} 翻译到 {target_name}: {text}]"

def generate_response(text: str, context: Dict = None, language: str = 'en') -> Dict[str, Any]:
    context = context or {}
    
    intent_result = intent_classifier.classify(text, language)
    intent = intent_result.get('intent', 'unknown')
    confidence = intent_result.get('confidence', 0.3)
    entities = intent_result.get('entities', [])
    suggested_responses = intent_result.get('suggested_responses', [])
    
    should_escalate = should_escalate_intent(intent) or confidence < 0.4
    
    response = ''
    if suggested_responses:
        response = suggested_responses[0]
    else:
        response = _get_default_response(language, should_escalate)
    
    if should_escalate:
        response = _get_escalation_message(language, intent)
    
    return {
        'response': response,
        'intent': intent,
        'confidence': confidence,
        'entities': entities,
        'shouldEscalate': should_escalate,
        'reason': _get_escalation_reason(intent, confidence) if should_escalate else None,
        'alternatives': intent_result.get('alternatives', [])
    }

def _get_default_response(language: str, should_escalate: bool) -> str:
    default_responses = {
        'zh': '我理解您的问题，正在为您查询相关信息。',
        'en': 'I understand your question, let me check the relevant information for you.',
        'ja': 'ご質問を理解しました。関連情報を確認しております。',
        'ko': '질문을 이해했습니다. 관련 정보를 확인하고 있습니다.',
        'fr': 'Je comprends votre question, je vérifie les informations pertinentes pour vous.',
        'de': 'Ich verstehe Ihre Frage, ich überprüfe die relevanten Informationen für Sie.',
        'es': 'Entiendo su pregunta, estoy verificando la información relevante para usted.',
        'pt': 'Entendo sua pergunta, estou verificando as informações relevantes para você.',
        'ar': 'أفهم سؤالك، وأنا أقوم بالتحقق من المعلومات ذات الصلة لك.',
        'ru': 'Я понимаю ваш вопрос, я проверяю соответствующую информацию для вас.'
    }
    return default_responses.get(language, default_responses['en'])

def _get_escalation_message(language: str, intent: str) -> str:
    escalation_messages = {
        'zh': '您的问题需要我们专业客服人员协助。正在为您转接人工客服，请稍候...',
        'en': 'Your question requires assistance from our professional customer service team. Transferring you to a human agent, please wait...',
        'ja': 'ご質問について専門のカスタマーサービス担当者が対応いたします。人間のオペレーターにお繋ぎしております。',
        'ko': '문의하신 내용에 대해 전문 상담원이 도와드려야 합니다. 인간 상담원으로 연결해 드리고 있으니 잠시만 기다려 주세요.',
        'fr': 'Votre question nécessite l\'assistance de notre service clientèle professionnel. Nous vous transférons à un agent humain, veuillez patienter...',
        'de': 'Ihre Frage erfordert die Unterstützung unseres professionellen Kundendienstes. Wir verbinden Sie mit einem menschlichen Agenten, bitte warten Sie...',
        'es': 'Su pregunta requiere la asistencia de nuestro servicio al cliente profesional. Lo estamos transfiriendo a un agente humano, por favor espere...',
        'pt': 'Sua pergunta requer a assistência do nosso serviço de atendimento ao cliente profissional. Estamos transferindo você para um agente humano, por favor aguarde...',
        'ar': 'سؤالك يتطلب مساعدة من فريق خدمة العملاء المحترف لدينا. نقوم بتحويلك إلى وكيل بشري، يرجى الانتظار...',
        'ru': 'Ваш вопрос требует помощи нашей профессиональной службы поддержки. Переключаем вас на человеческого агента, пожалуйста, подождите...'
    }
    return escalation_messages.get(language, escalation_messages['en'])

def _get_escalation_reason(intent: str, confidence: float) -> str:
    if confidence < 0.4:
        return f"Low intent confidence ({confidence})"
    
    escalation_reasons = {
        'refund': 'Refund request requires agent review',
        'complaint': 'Customer complaint requires human attention',
        'technical_support': 'Technical issue needs specialized support'
    }
    
    return escalation_reasons.get(intent, f"Intent '{intent}' requires escalation")
