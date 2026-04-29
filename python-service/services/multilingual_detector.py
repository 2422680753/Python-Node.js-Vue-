import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class LanguageCode(str, Enum):
    ZH = 'zh'
    EN = 'en'
    JA = 'ja'
    KO = 'ko'
    FR = 'fr'
    DE = 'de'
    ES = 'es'
    PT = 'pt'
    AR = 'ar'
    RU = 'ru'
    MIXED = 'mixed'

@dataclass
class LanguageSegment:
    text: str
    language: str
    start_idx: int
    end_idx: int
    confidence: float

@dataclass
class CodeSwitchAnalysis:
    primary_language: str
    is_code_switching: bool
    segments: List[LanguageSegment]
    language_distribution: Dict[str, float]
    switch_points: List[int]
    dominant_intent_language: str

class MultilingualDetector:
    CHINESE_RANGE = ('\u4e00', '\u9fff')
    JAPANESE_HIRAGANA_RANGE = ('\u3040', '\u309f')
    JAPANESE_KATAKANA_RANGE = ('\u30a0', '\u30ff')
    KOREAN_RANGE = ('\uac00', '\ud7af')
    ARABIC_RANGE = ('\u0600', '\u06ff')
    CYRILLIC_RANGE = ('\u0400', '\u04ff')
    
    LATIN_EXTENDED = set('àâäéèêëîïôöùûüÿçñœæ'
                          'ÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÇÑŒÆ'
                          'áéíóúüñ¿¡ÁÉÍÓÚÜÑ'
                          'àéèçùÀÉÈÇÙ'
                          'äöüßÄÖÜ')
    
    COMMON_CODE_SWITCH_PATTERNS = [
        (r'(我的|我想|请|帮我|查询|查看|取消|申请)(\s*)([a-zA-Z_]+)', 'zh_en'),
        (r'([a-zA-Z_]+)(\s*)(状态|订单|物流|退款|支付|信息|问题)', 'en_zh'),
        (r'(order|Order|ORDER)(\s*)([0-9#]+)', 'en_zh'),
        (r'(订单|单号)(\s*)([a-zA-Z0-9_-]+)', 'zh_en'),
        (r'(refund|Refund|REFUND)(\s*)(请求|申请|需要)', 'en_zh'),
        (r'(payment|Payment|PAYMENT)(\s*)(失败|问题|异常)', 'en_zh'),
        (r'(shipping|Shipping|SHIPPING)(\s*)(信息|地址|时间)', 'en_zh'),
    ]

    def __init__(self):
        self._init_language_keywords()
    
    def _init_language_keywords(self):
        self.language_keywords = {
            'zh': set(['订单', '退款', '物流', '支付', '客服', '用户', '您好', '谢谢',
                      '查询', '取消', '申请', '问题', '状态', '信息', '产品', '商品',
                      '价格', '发货', '收货', '退换', '投诉', '反馈', '帮助', '需要',
                      '我的', '我要', '请帮', '请问', '能否', '可以', '如何', '怎么']),
            'en': set(['order', 'refund', 'payment', 'shipping', 'customer', 'service',
                      'help', 'need', 'want', 'please', 'cancel', 'apply', 'status',
                      'information', 'product', 'item', 'price', 'delivery', 'return',
                      'exchange', 'complaint', 'feedback', 'my', 'how', 'what', 'where',
                      'when', 'why', 'hello', 'hi', 'thanks', 'thank you', 'hello']),
        }
        
        self.bilingual_keyword_pairs = {
            'order_status': {
                'zh': ['订单状态', '订单情况', '物流状态'],
                'en': ['order status', 'order information', 'tracking']
            },
            'refund_request': {
                'zh': ['退款', '退货', '退换', '申请退款'],
                'en': ['refund', 'return', 'exchange', 'refund request']
            },
            'payment_issue': {
                'zh': ['支付问题', '付款失败', '支付异常'],
                'en': ['payment issue', 'payment failed', 'payment error']
            },
            'shipping_info': {
                'zh': ['物流信息', '发货', '配送', '快递'],
                'en': ['shipping', 'delivery', 'tracking', 'dispatch']
            },
            'product_info': {
                'zh': ['产品信息', '商品详情', '价格'],
                'en': ['product info', 'item details', 'price']
            },
            'complaint': {
                'zh': ['投诉', '反馈', '不满意'],
                'en': ['complaint', 'feedback', 'unsatisfied']
            },
            'technical_support': {
                'zh': ['技术支持', '网站问题', 'APP问题'],
                'en': ['technical support', 'website issue', 'app problem']
            },
        }

    def detect_script_type(self, char: str) -> str:
        if self.CHINESE_RANGE[0] <= char <= self.CHINESE_RANGE[1]:
            return 'chinese'
        
        if self.JAPANESE_HIRAGANA_RANGE[0] <= char <= self.JAPANESE_HIRAGANA_RANGE[1]:
            return 'japanese'
        if self.JAPANESE_KATAKANA_RANGE[0] <= char <= self.JAPANESE_KATAKANA_RANGE[1]:
            return 'japanese'
        
        if self.KOREAN_RANGE[0] <= char <= self.KOREAN_RANGE[1]:
            return 'korean'
        
        if self.ARABIC_RANGE[0] <= char <= self.ARABIC_RANGE[1]:
            return 'arabic'
        
        if self.CYRILLIC_RANGE[0] <= char <= self.CYRILLIC_RANGE[1]:
            return 'cyrillic'
        
        if char.isalpha() and char.isascii():
            return 'latin'
        
        if char.lower() in self.LATIN_EXTENDED:
            return 'latin_extended'
        
        if char.isdigit() or char in '.,?!;:()[]{}"\'':
            return 'punctuation'
        
        if char.isspace():
            return 'whitespace'
        
        return 'other'

    def classify_script_language(self, script_type: str) -> Optional[str]:
        script_to_lang = {
            'chinese': 'zh',
            'japanese': 'ja',
            'korean': 'ko',
            'arabic': 'ar',
            'cyrillic': 'ru',
        }
        return script_to_lang.get(script_type)

    def segment_by_language(self, text: str) -> List[LanguageSegment]:
        if not text:
            return []
        
        segments = []
        current_segment = None
        
        for idx, char in enumerate(text):
            script_type = self.detect_script_type(char)
            
            if script_type in ['punctuation', 'whitespace', 'other']:
                if current_segment:
                    current_segment.text += char
                    current_segment.end_idx = idx
                continue
            
            lang = self.classify_script_language(script_type)
            
            if script_type == 'latin':
                lang = 'en'
            elif script_type == 'latin_extended':
                lang = self._detect_latin_language(char, text, idx)
            
            if not current_segment:
                current_segment = LanguageSegment(
                    text=char,
                    language=lang or 'unknown',
                    start_idx=idx,
                    end_idx=idx,
                    confidence=0.8
                )
            elif current_segment.language == lang:
                current_segment.text += char
                current_segment.end_idx = idx
            else:
                if current_segment.text.strip():
                    segments.append(current_segment)
                
                current_segment = LanguageSegment(
                    text=char,
                    language=lang or 'unknown',
                    start_idx=idx,
                    end_idx=idx,
                    confidence=0.8
                )
        
        if current_segment and current_segment.text.strip():
            segments.append(current_segment)
        
        segments = self._merge_adjacent_segments(segments)
        segments = self._refine_segment_confidence(text, segments)
        
        return segments

    def _detect_latin_language(self, char: str, text: str, idx: int) -> str:
        latin_language_indicators = {
            'fr': ['é', 'è', 'ê', 'à', 'ç', 'ù', 'ô', 'œ', 'æ'],
            'de': ['ä', 'ö', 'ü', 'ß'],
            'es': ['á', 'é', 'í', 'ó', 'ú', 'ñ', '¿', '¡'],
            'pt': ['á', 'â', 'ã', 'é', 'ê', 'í', 'ó', 'ô', 'õ', 'ú', 'ç'],
        }
        
        for lang, chars in latin_language_indicators.items():
            if char.lower() in chars:
                return lang
        
        return 'en'

    def _merge_adjacent_segments(self, segments: List[LanguageSegment]) -> List[LanguageSegment]:
        if not segments:
            return []
        
        merged = [segments[0]]
        
        for seg in segments[1:]:
            last = merged[-1]
            
            if last.language == seg.language:
                last.text += seg.text
                last.end_idx = seg.end_idx
                continue
            
            if seg.text.strip() == '':
                last.text += seg.text
                last.end_idx = seg.end_idx
                continue
            
            merged.append(seg)
        
        return merged

    def _refine_segment_confidence(self, text: str, segments: List[LanguageSegment]) -> List[LanguageSegment]:
        for seg in segments:
            if seg.language == 'zh':
                chinese_chars = sum(1 for c in seg.text if self.CHINESE_RANGE[0] <= c <= self.CHINESE_RANGE[1])
                total_chars = sum(1 for c in seg.text if c.strip())
                if total_chars > 0:
                    seg.confidence = chinese_chars / total_chars
            
            elif seg.language == 'en':
                latin_chars = sum(1 for c in seg.text if c.isalpha())
                total_chars = sum(1 for c in seg.text if c.strip())
                if total_chars > 0:
                    seg.confidence = latin_chars / total_chars
            
            else:
                seg.confidence = 0.7
        
        return segments

    def analyze_code_switching(self, text: str) -> CodeSwitchAnalysis:
        segments = self.segment_by_language(text)
        
        if not segments:
            return CodeSwitchAnalysis(
                primary_language='en',
                is_code_switching=False,
                segments=[],
                language_distribution={},
                switch_points=[],
                dominant_intent_language='en'
            )
        
        total_length = sum(len(s.text.strip()) for s in segments if s.text.strip())
        
        language_distribution = {}
        for seg in segments:
            lang = seg.language
            if lang not in language_distribution:
                language_distribution[lang] = 0
            language_distribution[lang] += len(seg.text.strip())
        
        if total_length > 0:
            for lang in language_distribution:
                language_distribution[lang] /= total_length
        
        switch_points = []
        prev_lang = None
        for idx, seg in enumerate(segments):
            if prev_lang and prev_lang != seg.language:
                switch_points.append(seg.start_idx)
            prev_lang = seg.language
        
        is_code_switching = len(switch_points) > 0 or len(language_distribution) > 1
        
        if language_distribution:
            primary_language = max(language_distribution.items(), key=lambda x: x[1])[0]
        else:
            primary_language = 'en'
        
        dominant_intent_language = self._determine_intent_language(text, segments, language_distribution)
        
        return CodeSwitchAnalysis(
            primary_language=primary_language,
            is_code_switching=is_code_switching,
            segments=segments,
            language_distribution=language_distribution,
            switch_points=switch_points,
            dominant_intent_language=dominant_intent_language
        )

    def _determine_intent_language(self, text: str, segments: List[LanguageSegment], 
                                    distribution: Dict[str, float]) -> str:
        text_lower = text.lower()
        
        for intent_name, lang_keywords in self.bilingual_keyword_pairs.items():
            for lang, keywords in lang_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        return lang
        
        if 'zh' in distribution and distribution['zh'] >= 0.3:
            return 'zh'
        
        if distribution:
            return max(distribution.items(), key=lambda x: x[1])[0]
        
        return 'en'

    def detect_language_enhanced(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                'language': 'en',
                'confidence': 0.5,
                'isCodeSwitching': False,
                'segments': [],
                'languageDistribution': {},
                'dominantIntentLanguage': 'en'
            }
        
        analysis = self.analyze_code_switching(text)
        
        if analysis.is_code_switching:
            primary_confidence = analysis.language_distribution.get(analysis.primary_language, 0.5)
            
            return {
                'language': analysis.dominant_intent_language,
                'confidence': primary_confidence,
                'isCodeSwitching': True,
                'primaryLanguage': analysis.primary_language,
                'segments': [
                    {
                        'text': s.text,
                        'language': s.language,
                        'startIdx': s.start_idx,
                        'endIdx': s.end_idx,
                        'confidence': s.confidence
                    }
                    for s in analysis.segments
                ],
                'languageDistribution': analysis.language_distribution,
                'dominantIntentLanguage': analysis.dominant_intent_language,
                'switchPoints': analysis.switch_points
            }
        else:
            return {
                'language': analysis.primary_language,
                'confidence': analysis.language_distribution.get(analysis.primary_language, 0.7),
                'isCodeSwitching': False,
                'segments': [],
                'languageDistribution': analysis.language_distribution,
                'dominantIntentLanguage': analysis.primary_language
            }

    def extract_all_keywords(self, text: str) -> Dict[str, List[str]]:
        result = {'zh': [], 'en': [], 'mixed': []}
        
        text_lower = text.lower()
        
        for lang, keywords in self.language_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    result[lang].append(keyword)
        
        for pattern, switch_type in self.COMMON_CODE_SWITCH_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                result['mixed'].extend([''.join(m) for m in matches])
        
        return result

multilingual_detector = MultilingualDetector()
