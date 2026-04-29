from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
import re
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import OrderedDict
from datetime import datetime
from services.data_processing_pipeline import DataFormat

class ParseError(Exception):
    pass

class FormatDetector:
    JSON_INDICATORS = [
        (r'^\s*\{', 0.8),
        (r'\}\s*$', 0.8),
        (r'"[^"]+"\s*:', 0.9),
        (r':\s*(true|false|null|\d+\.?\d*)\s*', 0.7),
    ]
    
    XML_INDICATORS = [
        (r'^\s*<\?xml', 1.0),
        (r'^\s*<[a-zA-Z_][a-zA-Z0-9_\-]*>', 0.8),
        (r'</[a-zA-Z_][a-zA-Z0-9_\-]*>\s*$', 0.8),
        (r'/>', 0.6),
    ]
    
    CSV_INDICATORS = [
        (r'^[a-zA-Z_\s,]+$', 0.5),
        (r',[a-zA-Z_\s]+,[a-zA-Z_\s]+', 0.6),
        (r'\n[^,\n]+,[^,\n]+,[^,\n]+', 0.7),
    ]
    
    YAML_INDICATORS = [
        (r'^\s*---', 0.9),
        (r'^[a-zA-Z_][a-zA-Z0-9_\-]*:\s*', 0.7),
        (r'^(\s+)-\s+\S', 0.8),
    ]
    
    @classmethod
    def detect(cls, text: str) -> Dict[str, float]:
        text = text.strip() if text else ''
        if not text:
            return {DataFormat.UNKNOWN.value: 1.0}
        
        scores = {}
        
        json_score = cls._calculate_score(text, cls.JSON_INDICATORS)
        if json_score > 0:
            scores[DataFormat.JSON.value] = json_score
        
        xml_score = cls._calculate_score(text, cls.XML_INDICATORS)
        if xml_score > 0:
            scores[DataFormat.XML.value] = xml_score
        
        csv_score = cls._calculate_score(text, cls.CSV_INDICATORS)
        if csv_score > 0:
            scores[DataFormat.CSV.value] = csv_score
        
        yaml_score = cls._calculate_score(text, cls.YAML_INDICATORS)
        if yaml_score > 0:
            scores[DataFormat.YAML.value] = yaml_score
        
        if not scores:
            return {DataFormat.TEXT.value: 1.0}
        
        total = sum(scores.values())
        normalized = {k: v / total for k, v in scores.items()}
        
        return normalized
    
    @classmethod
    def _calculate_score(cls, text: str, patterns: List[tuple]) -> float:
        score = 0.0
        for pattern, weight in patterns:
            if re.search(pattern, text, re.MULTILINE):
                score += weight
        return min(score, 1.0)
    
    @classmethod
    def detect_with_confidence(cls, text: str) -> tuple:
        scores = cls.detect(text)
        if not scores:
            return DataFormat.UNKNOWN, 0.0
        
        best_format = max(scores.items(), key=lambda x: x[1])
        return DataFormat(best_format[0]), best_format[1]

@dataclass
class ParseResult:
    format: DataFormat
    data: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    raw_length: int = 0
    parse_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseParser:
    FORMAT: DataFormat = DataFormat.UNKNOWN
    
    @classmethod
    def can_parse(cls, text: str) -> bool:
        raise NotImplementedError
    
    @classmethod
    def parse(cls, text: str) -> ParseResult:
        raise NotImplementedError

class JSONParser(BaseParser):
    FORMAT = DataFormat.JSON
    
    @classmethod
    def can_parse(cls, text: str) -> bool:
        text = text.strip()
        return (text.startswith('{') and text.endswith('}')) or \
               (text.startswith('[') and text.endswith(']'))
    
    @classmethod
    def parse(cls, text: str) -> ParseResult:
        start_time = datetime.now()
        warnings = []
        
        try:
            data = json.loads(text, object_pairs_hook=OrderedDict)
            
            end_time = datetime.now()
            
            return ParseResult(
                format=cls.FORMAT,
                data=data if isinstance(data, dict) else {'items': data},
                success=True,
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000,
                metadata={
                    'is_array': isinstance(data, list),
                    'key_count': len(data) if isinstance(data, dict) else len(data),
                }
            )
        except json.JSONDecodeError as e:
            end_time = datetime.now()
            return ParseResult(
                format=cls.FORMAT,
                data={},
                success=False,
                error_message=f'JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}',
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000
            )
        except Exception as e:
            end_time = datetime.now()
            return ParseResult(
                format=cls.FORMAT,
                data={},
                success=False,
                error_message=str(e),
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000
            )

class XMLParser(BaseParser):
    FORMAT = DataFormat.XML
    
    @classmethod
    def can_parse(cls, text: str) -> bool:
        text = text.strip()
        return text.startswith('<') and (
            text.endswith('>')
        )
    
    @classmethod
    def parse(cls, text: str) -> ParseResult:
        start_time = datetime.now()
        warnings = []
        
        try:
            root = ET.fromstring(text)
            data = cls._element_to_dict(root)
            
            end_time = datetime.now()
            
            return ParseResult(
                format=cls.FORMAT,
                data=data,
                success=True,
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000,
                metadata={
                    'root_tag': root.tag,
                    'child_count': len(list(root)),
                }
            )
        except ET.ParseError as e:
            end_time = datetime.now()
            return ParseResult(
                format=cls.FORMAT,
                data={},
                success=False,
                error_message=f'XML parse error: {str(e)}',
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000
            )
        except Exception as e:
            end_time = datetime.now()
            return ParseResult(
                format=cls.FORMAT,
                data={},
                success=False,
                error_message=str(e),
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000
            )
    
    @classmethod
    def _element_to_dict(cls, element) -> Dict[str, Any]:
        result = {}
        
        if element.attrib:
            result['@attributes'] = dict(element.attrib)
        
        text = (element.text or '').strip()
        children = list(element)
        
        if text and not children:
            if element.attrib:
                result['#text'] = text
            else:
                result = text
        elif children:
            child_dict = {}
            for child in children:
                child_data = cls._element_to_dict(child)
                if child.tag in child_dict:
                    if not isinstance(child_dict[child.tag], list):
                        child_dict[child.tag] = [child_dict[child.tag]]
                    child_dict[child.tag].append(child_data)
                else:
                    child_dict[child.tag] = child_data
            if text:
                child_dict['#text'] = text
            result.update(child_dict)
        
        return {element.tag: result}

class CSVParser(BaseParser):
    FORMAT = DataFormat.CSV
    
    DELIMITERS = [',', ';', '\t', '|']
    
    @classmethod
    def can_parse(cls, text: str) -> bool:
        text = text.strip()
        if not text:
            return False
        
        lines = text.split('\n')
        if len(lines) < 1:
            return False
        
        first_line = lines[0]
        for delim in cls.DELIMITERS:
            delim_count = first_line.count(delim)
            if delim_count >= 1:
                return True
        return False
    
    @classmethod
    def parse(cls, text: str) -> ParseResult:
        start_time = datetime.now()
        warnings = []
        
        try:
            lines = text.strip().split('\n')
            if not lines:
                return ParseResult(
                    format=cls.FORMAT,
                    data={'headers': [], 'rows': []},
                    success=False,
                    error_message='Empty CSV content',
                    warnings=warnings,
                    raw_length=len(text),
                    parse_time_ms=0.0
                )
            
            delimiter = cls._detect_delimiter(lines[0])
            
            has_header = cls._detect_header(lines[0], delimiter)
            
            if has_header:
                headers = cls._parse_line(lines[0], delimiter)
                data_lines = lines[1:]
            else:
                headers = [f'column_{i}' for i in range(len(cls._parse_line(lines[0], delimiter)))]
                data_lines = lines
            
            rows = []
            for line in data_lines:
                if not line.strip():
                    continue
                values = cls._parse_line(line, delimiter)
                if len(values) == len(headers):
                    row = dict(zip(headers, values))
                    rows.append(row)
                elif len(values) > 0:
                    warnings.append(f'Row has {len(values)} columns but expected {len(headers)}')
                    row = dict(zip(headers, values + [None] * (len(headers) - len(values))))
                    rows.append(row)
            
            end_time = datetime.now()
            
            return ParseResult(
                format=cls.FORMAT,
                data={
                    'headers': headers,
                    'rows': rows,
                    'row_count': len(rows),
                    'delimiter': delimiter,
                    'has_header': has_header
                },
                success=True,
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000,
                metadata={
                    'delimiter_detected': delimiter,
                    'header_detected': has_header,
                    'columns': len(headers),
                }
            )
        except Exception as e:
            end_time = datetime.now()
            return ParseResult(
                format=cls.FORMAT,
                data={'headers': [], 'rows': []},
                success=False,
                error_message=str(e),
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000
            )
    
    @classmethod
    def _detect_delimiter(cls, line: str) -> str:
        best_delim = ','
        max_count = 0
        
        for delim in cls.DELIMITERS:
            count = line.count(delim)
            if count > max_count:
                max_count = count
                best_delim = delim
        
        return best_delim
    
    @classmethod
    def _detect_header(cls, first_line: str, delimiter: str) -> bool:
        values = cls._parse_line(first_line, delimiter)
        
        all_text = all(re.match(r'^[a-zA-Z_\s]+$', v.strip()) for v in values if v.strip())
        
        has_numbers = any(re.match(r'^\d+\.?\d*$', v.strip()) for v in values if v.strip())
        
        return all_text and not has_numbers and len(values) > 1
    
    @classmethod
    def _parse_line(cls, line: str, delimiter: str) -> List[str]:
        values = []
        current = ''
        in_quotes = False
        quote_char = None
        
        for char in line:
            if char in '"\'' and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char == delimiter and not in_quotes:
                values.append(current.strip())
                current = ''
            else:
                current += char
        
        values.append(current.strip())
        return values

class YAMLParser(BaseParser):
    FORMAT = DataFormat.YAML
    
    @classmethod
    def can_parse(cls, text: str) -> bool:
        text = text.strip()
        if text.startswith('---'):
            return True
        
        lines = text.split('\n')
        for line in lines[:5]:
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_\-]*:\s*', line):
                return True
        
        return False
    
    @classmethod
    def parse(cls, text: str) -> ParseResult:
        start_time = datetime.now()
        warnings = []
        
        try:
            data = cls._parse_yaml_simple(text)
            
            end_time = datetime.now()
            
            return ParseResult(
                format=cls.FORMAT,
                data=data,
                success=True,
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000
            )
        except Exception as e:
            end_time = datetime.now()
            return ParseResult(
                format=cls.FORMAT,
                data={},
                success=False,
                error_message=str(e),
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000
            )
    
    @classmethod
    def _parse_yaml_simple(cls, text: str) -> Dict[str, Any]:
        lines = text.strip().split('\n')
        result = {}
        current_key = None
        current_indent = 0
        list_items = []
        
        for line in lines:
            stripped = line.lstrip()
            if not stripped or stripped.startswith('#'):
                continue
            
            indent = len(line) - len(stripped)
            
            if stripped.startswith('- '):
                if indent == current_indent and current_key:
                    list_items.append(stripped[2:].strip())
                    result[current_key] = list_items
                continue
            
            if ':' in stripped:
                key, value = stripped.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if indent < current_indent:
                    list_items = []
                
                if value:
                    result[key] = cls._cast_value(value)
                else:
                    result[key] = {}
                
                current_key = key
                current_indent = indent
                list_items = []
        
        return result
    
    @classmethod
    def _cast_value(cls, value: str) -> Any:
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        if value.lower() == 'null' or value == '~':
            return None
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except ValueError:
            pass
        
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        return value

class FormUrlEncodedParser(BaseParser):
    FORMAT = DataFormat.FORM_URLENCODED
    
    @classmethod
    def can_parse(cls, text: str) -> bool:
        if '=' in text and '&' in text:
            return True
        return '=' in text and len(text) < 1000
    
    @classmethod
    def parse(cls, text: str) -> ParseResult:
        start_time = datetime.now()
        warnings = []
        data = {}
        
        try:
            pairs = text.split('&')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key.endswith('[]'):
                        key = key[:-2]
                        if key not in data:
                            data[key] = []
                        data[key].append(value)
                    elif key in data:
                        if isinstance(data[key], list):
                            data[key].append(value)
                        else:
                            data[key] = [data[key], value]
                    else:
                        data[key] = value
            
            end_time = datetime.now()
            
            return ParseResult(
                format=cls.FORMAT,
                data=data,
                success=True,
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000,
                metadata={
                    'key_count': len(data),
                    'has_array_keys': any(isinstance(v, list) for v in data.values())
                }
            )
        except Exception as e:
            end_time = datetime.now()
            return ParseResult(
                format=cls.FORMAT,
                data={},
                success=False,
                error_message=str(e),
                warnings=warnings,
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000
            )

class TextParser(BaseParser):
    FORMAT = DataFormat.TEXT
    
    @classmethod
    def can_parse(cls, text: str) -> bool:
        return True
    
    @classmethod
    def parse(cls, text: str) -> ParseResult:
        start_time = datetime.now()
        
        try:
            lines = text.strip().split('\n') if '\n' in text else [text.strip()]
            
            sentences = cls._extract_sentences(text)
            words = cls._extract_words(text)
            
            data = {
                'raw_text': text,
                'lines': lines,
                'sentences': sentences,
                'words': words,
                'stats': {
                    'line_count': len(lines),
                    'sentence_count': len(sentences),
                    'word_count': len(words),
                    'char_count': len(text),
                }
            }
            
            end_time = datetime.now()
            
            return ParseResult(
                format=cls.FORMAT,
                data=data,
                success=True,
                warnings=[],
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000,
                metadata={
                    'is_multiline': len(lines) > 1,
                    'average_sentence_length': sum(len(s) for s in sentences) / len(sentences) if sentences else 0
                }
            )
        except Exception as e:
            end_time = datetime.now()
            return ParseResult(
                format=cls.FORMAT,
                data={'raw_text': text},
                success=False,
                error_message=str(e),
                warnings=[],
                raw_length=len(text),
                parse_time_ms=(end_time - start_time).total_seconds() * 1000
            )
    
    @classmethod
    def _extract_sentences(cls, text: str) -> List[str]:
        sentence_endings = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]
    
    @classmethod
    def _extract_words(cls, text: str) -> List[str]:
        words = re.findall(r'\b\w+\b', text)
        return words

class StructuredParser:
    PARSERS: Dict[DataFormat, Type[BaseParser]] = {
        DataFormat.JSON: JSONParser,
        DataFormat.XML: XMLParser,
        DataFormat.CSV: CSVParser,
        DataFormat.YAML: YAMLParser,
        DataFormat.FORM_URLENCODED: FormUrlEncodedParser,
        DataFormat.TEXT: TextParser,
    }
    
    @classmethod
    def auto_parse(cls, text: str) -> ParseResult:
        format_scores = FormatDetector.detect(text)
        best_format = max(format_scores.items(), key=lambda x: x[1])[0]
        format_enum = DataFormat(best_format)
        
        parser = cls.PARSERS.get(format_enum, TextParser)
        
        try:
            result = parser.parse(text)
            
            if not result.success and format_enum != DataFormat.TEXT:
                text_parser = cls.PARSERS[DataFormat.TEXT]
                result = text_parser.parse(text)
                result.warnings.append(f'Fallback to text parser due to parse error')
            
            return result
        except Exception as e:
            text_parser = cls.PARSERS[DataFormat.TEXT]
            result = text_parser.parse(text)
            result.warnings.append(f'Error during parsing: {str(e)}')
            return result
    
    @classmethod
    def parse_as(cls, text: str, format_type: DataFormat) -> ParseResult:
        parser = cls.PARSERS.get(format_type, TextParser)
        return parser.parse(text)
    
    @classmethod
    def detect_format(cls, text: str) -> tuple:
        return FormatDetector.detect_with_confidence(text)

structured_parser = StructuredParser()
