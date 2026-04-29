import re
import jieba
from typing import List, Dict, Any, Tuple
from services.knowledge_base import get_knowledge_base
from services.bilingual_intent_classifier import BilingualIntentClassifier
from services.language_detector import detect_language_enhanced

class IntentClassifier:
    def __init__(self):
        self.knowledge_base = get_knowledge_base()
        self.intents = self.knowledge_base.get('intents', {})
        self._build_keyword_index()
        self.bilingual_classifier = BilingualIntentClassifier(self)
    
    def _build_keyword_index(self):
        self.keyword_map = {}
        for intent_name, intent_data in self.intents.items():
            keywords = intent_data.get('keywords', [])
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower not in self.keyword_map:
                    self.keyword_map[keyword_lower] = []
                self.keyword_map[keyword_lower].append(intent_name)
    
    def tokenize(self, text: str, language: str = 'en') -> List[str]:
        if language == 'zh' or self._contains_chinese(text):
            return list(jieba.cut(text.lower()))
        else:
            return re.findall(r'\w+', text.lower())
    
    def _contains_chinese(self, text: str) -> bool:
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def classify(self, text: str, language: str = 'en') -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                'intent': 'unknown',
                'confidence': 0.0,
                'entities': [],
                'suggested_responses': []
            }
        
        language_analysis = detect_language_enhanced(text)
        
        if language_analysis.get('isCodeSwitching'):
            return self.bilingual_classifier.classify_bilingual(text, language_analysis)
        
        dominant_lang = language_analysis.get('dominantIntentLanguage', language)
        
        tokens = self.tokenize(text, dominant_lang)
        text_lower = text.lower()
        
        intent_scores = {}
        
        for token in tokens:
            if token in self.keyword_map:
                for intent in self.keyword_map[token]:
                    if intent not in intent_scores:
                        intent_scores[intent] = 0
                    intent_scores[intent] += 1
        
        for intent_name, intent_data in self.intents.items():
            keywords = intent_data.get('keywords', [])
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in text_lower and len(keyword_lower) > 2:
                    if intent_name not in intent_scores:
                        intent_scores[intent_name] = 0
                    score_boost = len(keyword_lower) / 10.0
                    intent_scores[intent_name] += score_boost
        
        if not intent_scores:
            return {
                'intent': 'unknown',
                'confidence': 0.3,
                'entities': self._extract_entities(text, dominant_lang),
                'suggested_responses': ['我理解您的问题，但需要更多信息才能准确回答。请您详细描述一下您的需求。'],
                'isCodeSwitching': False,
                'languageDistribution': language_analysis.get('languageDistribution', {})
            }
        
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        best_intent = sorted_intents[0][0]
        best_score = sorted_intents[0][1]
        
        confidence = self._calculate_confidence(best_score, len(tokens))
        
        entities = self._extract_entities(text, dominant_lang)
        
        suggested_responses = []
        if best_intent in self.intents:
            responses = self.intents[best_intent].get('responses', {})
            if dominant_lang in responses:
                suggested_responses.append(responses[dominant_lang])
            elif 'en' in responses:
                suggested_responses.append(responses['en'])
        
        return {
            'intent': best_intent,
            'confidence': confidence,
            'entities': entities,
            'suggested_responses': suggested_responses,
            'isCodeSwitching': False,
            'languageDistribution': language_analysis.get('languageDistribution', {}),
            'dominantLanguage': dominant_lang,
            'alternatives': [
                {'intent': intent, 'score': score}
                for intent, score in sorted_intents[1:3]
            ] if len(sorted_intents) > 1 else []
        }
    
    def _calculate_confidence(self, score: float, token_count: int) -> float:
        if token_count == 0:
            return 0.0
        
        base_confidence = min(score / max(token_count, 1), 1.0)
        
        if score >= 3:
            base_confidence = min(base_confidence + 0.2, 1.0)
        elif score >= 2:
            base_confidence = min(base_confidence + 0.1, 1.0)
        
        return round(base_confidence, 3)
    
    def _extract_entities(self, text: str, language: str) -> List[Dict[str, Any]]:
        entities = []
        
        order_pattern = re.compile(r'(?:order|订单|单号)[\s#:]*([A-Za-z0-9_-]{6,})', re.IGNORECASE)
        for match in order_pattern.finditer(text):
            entities.append({
                'type': 'order_id',
                'value': match.group(1),
                'start': match.start(),
                'end': match.end()
            })
        
        amount_pattern = re.compile(r'[\$¥€£]\s*(\d+(?:\.\d{2})?)|(\d+(?:\.\d{2})?)\s*(?:USD|CNY|EUR|GBP|usd|cny|eur|gbp|美元|人民币|欧元|英镑)', re.IGNORECASE)
        for match in amount_pattern.finditer(text):
            value = match.group(1) or match.group(2)
            if value:
                entities.append({
                    'type': 'amount',
                    'value': value,
                    'start': match.start(),
                    'end': match.end()
                })
        
        date_pattern = re.compile(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日号]?|(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})', re.IGNORECASE)
        for match in date_pattern.finditer(text):
            entities.append({
                'type': 'date',
                'value': match.group(),
                'start': match.start(),
                'end': match.end()
            })
        
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        for match in email_pattern.finditer(text):
            entities.append({
                'type': 'email',
                'value': match.group(),
                'start': match.start(),
                'end': match.end()
            })
        
        phone_pattern = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}')
        for match in phone_pattern.finditer(text):
            value = match.group()
            if len(re.sub(r'\D', '', value)) >= 7:
                entities.append({
                    'type': 'phone',
                    'value': value,
                    'start': match.start(),
                    'end': match.end()
                })
        
        product_pattern = re.compile(r'(?:产品|商品|product|item)[\s:]*([^，。！？,\.\!\?]+)', re.IGNORECASE)
        for match in product_pattern.finditer(text):
            product_name = match.group(1).strip()
            if product_name and len(product_name) > 0:
                entities.append({
                    'type': 'product_name',
                    'value': product_name,
                    'start': match.start(),
                    'end': match.end()
                })
        
        return entities
    
    def get_all_intents(self) -> Dict[str, Any]:
        return {
            intent_name: {
                'keywords': data.get('keywords', []),
                'supports_languages': list(data.get('responses', {}).keys()),
                'should_escalate': data.get('should_escalate', False)
            }
            for intent_name, data in self.intents.items()
        }

intent_classifier = IntentClassifier()
