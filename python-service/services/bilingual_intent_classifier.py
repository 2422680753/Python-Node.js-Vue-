import re
import jieba
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from services.knowledge_base import get_knowledge_base
from services.multilingual_detector import multilingual_detector, LanguageSegment

@dataclass
class BilingualMatch:
    intent: str
    chinese_keyword: Optional[str]
    english_keyword: Optional[str]
    score: float
    match_type: str

class BilingualIntentClassifier:
    BILINGUAL_INTENT_KEYWORDS = {
        'order_status': {
            'zh': ['订单', '订单状态', '物流', '配送', '发货', '收货', '快递', '单号', '查询订单'],
            'en': ['order', 'order status', 'delivery', 'shipping', 'track', 'tracking', 'shipment', 'order number'],
            'zh_en_hybrid': [
                r'(我的|查询|查看)(\s*)(order|Order|ORDER)',
                r'(order|Order|ORDER)(\s*)(状态|情况|信息)',
                r'(track|Track|TRACK)(\s*)(我的|订单)',
            ]
        },
        'refund': {
            'zh': ['退款', '退货', '退换', '申请退款', '退款申请', '退货退款', '退款退货'],
            'en': ['refund', 'return', 'exchange', 'refund request', 'return request', 'get money back'],
            'zh_en_hybrid': [
                r'(申请|需要|想要)(\s*)(refund|Refund|REFUND|return|Return)',
                r'(refund|Refund|REFUND)(\s*)(申请|请求)',
            ]
        },
        'complaint': {
            'zh': ['投诉', '反馈', '不满意', '问题', '糟糕', '差', '劣质', '质量问题'],
            'en': ['complaint', 'feedback', 'unsatisfied', 'not happy', 'problem', 'issue', 'bad', 'terrible'],
            'zh_en_hybrid': [
                r'(有|存在)(\s*)(problem|Problem|PROBLEM|issue|Issue)',
                r'(very|Very|too)(\s*)(bad|Bad|BAD)',
            ]
        },
        'payment': {
            'zh': ['支付', '付款', '交钱', '支付方式', '付款方式', '信用卡', '支付宝', '微信支付'],
            'en': ['payment', 'pay', 'credit card', 'alipay', 'wechat pay', 'paypal', 'payment method'],
            'zh_en_hybrid': [
                r'(使用|用)(\s*)(credit|Credit|CREDIT|paypal|PayPal|PAYPAL)',
                r'(payment|Payment|PAYMENT)(\s*)(失败|问题|异常)',
            ]
        },
        'technical_support': {
            'zh': ['技术支持', '网站', 'APP', '页面', '打不开', '无法', 'bug', '错误', '故障'],
            'en': ['technical support', 'website', 'app', 'page', 'cannot open', 'bug', 'error', 'issue', 'technical'],
            'zh_en_hybrid': [
                r'(网站|APP|页面)(\s*)(bug|Bug|BUG|error|Error)',
                r'(cannot|can\'t|Can\'t|CAN\'T)(\s*)(打开|访问|登录)',
            ]
        },
        'product_info': {
            'zh': ['产品', '商品', '价格', '多少钱', '尺寸', '大小', '颜色', '库存', '有没有'],
            'en': ['product', 'item', 'price', 'how much', 'size', 'color', 'stock', 'available', 'in stock'],
            'zh_en_hybrid': [
                r'(这个|这个商品)(\s*)(price|Price|PRICE|size|Size)',
                r'(product|Product|PRODUCT|item|Item)(\s*)(价格|尺寸|颜色)',
            ]
        },
        'shipping_info': {
            'zh': ['运费', '包邮', '关税', '海外', '国际', '快递费', '配送费'],
            'en': ['shipping', 'shipping fee', 'free shipping', 'customs', 'duty', 'international', 'overseas'],
            'zh_en_hybrid': [
                r'(是否)(\s*)(free|Free|FREE)(\s*)(shipping|Shipping)',
                r'(customs|Customs|CUSTOMS)(\s*)(关税|费用)',
            ]
        },
        'greeting': {
            'zh': ['你好', '您好', '嗨', 'hi', 'hello', '您好吗'],
            'en': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
            'zh_en_hybrid': []
        }
    }

    def __init__(self, base_intent_classifier):
        self.base_classifier = base_intent_classifier
        self.knowledge_base = get_knowledge_base()
        self.intents = self.knowledge_base.get('intents', {})
        self._build_bilingual_index()
    
    def _build_bilingual_index(self):
        self.bilingual_keyword_map = {}
        
        for intent_name, lang_keywords in self.BILINGUAL_INTENT_KEYWORDS.items():
            for lang, keywords in lang_keywords.items():
                if lang == 'zh_en_hybrid':
                    continue
                
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower not in self.bilingual_keyword_map:
                        self.bilingual_keyword_map[keyword_lower] = []
                    self.bilingual_keyword_map[keyword_lower].append({
                        'intent': intent_name,
                        'language': lang,
                        'keyword': keyword
                    })
        
        self.hybrid_patterns = []
        for intent_name, lang_keywords in self.BILINGUAL_INTENT_KEYWORDS.items():
            for pattern in lang_keywords.get('zh_en_hybrid', []):
                self.hybrid_patterns.append({
                    'intent': intent_name,
                    'pattern': re.compile(pattern, re.IGNORECASE)
                })

    def classify_bilingual(self, text: str, language_analysis: Dict[str, Any]) -> Dict[str, Any]:
        text_lower = text.lower()
        
        intent_scores = {}
        matched_keywords = []
        hybrid_matches = []
        
        for hybrid_pattern in self.hybrid_patterns:
            matches = list(hybrid_pattern['pattern'].finditer(text))
            if matches:
                intent = hybrid_pattern['intent']
                if intent not in intent_scores:
                    intent_scores[intent] = 0
                
                for match in matches:
                    intent_scores[intent] += 1.5
                    hybrid_matches.append({
                        'intent': intent,
                        'matched_text': match.group(),
                        'start': match.start(),
                        'end': match.end()
                    })
        
        is_code_switching = language_analysis.get('isCodeSwitching', False)
        segments = language_analysis.get('segments', [])
        language_distribution = language_analysis.get('languageDistribution', {})
        
        if is_code_switching and segments:
            for segment in segments:
                seg_text = segment.get('text', '').lower()
                seg_lang = segment.get('language', 'en')
                
                tokens = self._tokenize_segment(seg_text, seg_lang)
                
                for token in tokens:
                    if token in self.bilingual_keyword_map:
                        for match_info in self.bilingual_keyword_map[token]:
                            intent = match_info['intent']
                            if intent not in intent_scores:
                                intent_scores[intent] = 0
                            intent_scores[intent] += 1.0
                            matched_keywords.append({
                                'intent': intent,
                                'keyword': token,
                                'language': seg_lang,
                                'segment': seg_text
                            })
        
        for intent_name, lang_keywords in self.BILINGUAL_INTENT_KEYWORDS.items():
            for lang in ['zh', 'en']:
                keywords = lang_keywords.get(lang, [])
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if len(keyword_lower) > 2 and keyword_lower in text_lower:
                        if intent_name not in intent_scores:
                            intent_scores[intent_name] = 0
                        
                        boost_factor = 1.0
                        if is_code_switching:
                            boost_factor = 1.2
                        
                        if ' ' in keyword:
                            boost_factor *= 1.3
                        
                        intent_scores[intent_name] += (len(keyword_lower) / 10.0) * boost_factor
                        matched_keywords.append({
                            'intent': intent_name,
                            'keyword': keyword,
                            'language': lang,
                            'is_phrase': ' ' in keyword
                        })
        
        base_result = self.base_classifier.classify(text, language_analysis.get('dominantIntentLanguage', 'en'))
        
        if base_result.get('intent') != 'unknown':
            base_intent = base_result['intent']
            base_confidence = base_result['confidence']
            if base_intent not in intent_scores:
                intent_scores[base_intent] = 0
            intent_scores[base_intent] += base_confidence * 0.5
        
        if not intent_scores:
            return {
                'intent': 'unknown',
                'confidence': 0.3,
                'entities': self._extract_entities_bilingual(text),
                'suggested_responses': ['我理解您的问题，但需要更多信息才能准确回答。请您详细描述一下您的需求。'],
                'isBilingual': is_code_switching,
                'languageDistribution': language_distribution,
                'matchedKeywords': [],
                'hybridMatches': []
            }
        
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        best_intent = sorted_intents[0][0]
        best_score = sorted_intents[0][1]
        
        confidence = self._calculate_bilingual_confidence(
            best_score, 
            len(matched_keywords) + len(hybrid_matches),
            is_code_switching
        )
        
        entities = self._extract_entities_bilingual(text)
        
        suggested_responses = []
        if best_intent in self.intents:
            responses = self.intents[best_intent].get('responses', {})
            response_lang = language_analysis.get('dominantIntentLanguage', 'en')
            if response_lang in responses:
                suggested_responses.append(responses[response_lang])
            elif 'en' in responses:
                suggested_responses.append(responses['en'])
        
        return {
            'intent': best_intent,
            'confidence': confidence,
            'entities': entities,
            'suggested_responses': suggested_responses,
            'isBilingual': is_code_switching,
            'languageDistribution': language_distribution,
            'matchedKeywords': matched_keywords[:10],
            'hybridMatches': hybrid_matches,
            'alternatives': [
                {'intent': intent, 'score': round(score, 3)}
                for intent, score in sorted_intents[1:3]
            ] if len(sorted_intents) > 1 else []
        }

    def _tokenize_segment(self, text: str, language: str) -> List[str]:
        if language == 'zh':
            return list(jieba.cut(text.lower()))
        else:
            return re.findall(r'\w+', text.lower())

    def _calculate_bilingual_confidence(self, score: float, match_count: int, is_code_switching: bool) -> float:
        base_confidence = min(score / max(1, 3), 1.0)
        
        if is_code_switching:
            base_confidence = min(base_confidence * 0.9, 1.0)
        
        if score >= 3:
            base_confidence = min(base_confidence + 0.2, 1.0)
        elif score >= 2:
            base_confidence = min(base_confidence + 0.1, 1.0)
        
        if match_count >= 3:
            base_confidence = min(base_confidence + 0.1, 1.0)
        
        return round(base_confidence, 3)

    def _extract_entities_bilingual(self, text: str) -> List[Dict[str, Any]]:
        entities = []
        
        order_patterns = [
            r'(?:order|订单|单号|Order|ORDER)[\s#:]*([A-Za-z0-9_-]{6,})',
            r'([A-Za-z]{2,4}\d{6,})',
        ]
        for pattern in order_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    'type': 'order_id',
                    'value': match.group(1) if len(match.groups()) > 0 else match.group(),
                    'start': match.start(),
                    'end': match.end()
                })
        
        amount_patterns = [
            r'[\$¥€£]\s*(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*(?:USD|CNY|EUR|GBP|usd|cny|eur|gbp|美元|人民币|欧元|英镑)',
        ]
        for pattern in amount_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1)
                if value:
                    entities.append({
                        'type': 'amount',
                        'value': value,
                        'start': match.start(),
                        'end': match.end()
                    })
        
        date_patterns = [
            r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日号]?',
            r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})',
        ]
        for pattern in date_patterns:
            for match in re.finditer(pattern, text):
                entities.append({
                    'type': 'date',
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append({
                'type': 'email',
                'value': match.group(),
                'start': match.start(),
                'end': match.end()
            })
        
        phone_patterns = [
            r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}',
            r'1[3-9]\d{9}',
        ]
        for pattern in phone_patterns:
            for match in re.finditer(pattern, text):
                value = match.group()
                digits = re.sub(r'\D', '', value)
                if len(digits) >= 7:
                    entities.append({
                        'type': 'phone',
                        'value': value,
                        'start': match.start(),
                        'end': match.end()
                    })
        
        product_patterns = [
            r'(?:产品|商品|product|item|Product|Item)[\s:]*([^，。！？,\.\!\?]+)',
            r'(?:SKU|sku|id|ID)[\s#:]*([A-Za-z0-9_-]+)',
        ]
        for pattern in product_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                product_name = match.group(1).strip()
                if product_name and len(product_name) > 0:
                    entities.append({
                        'type': 'product_name',
                        'value': product_name,
                        'start': match.start(),
                        'end': match.end()
                    })
        
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity['type'], entity['value'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return unique_entities

    def get_intent_keywords(self, intent: str = None) -> Dict[str, Any]:
        if intent:
            return self.BILINGUAL_INTENT_KEYWORDS.get(intent, {})
        return self.BILINGUAL_INTENT_KEYWORDS
