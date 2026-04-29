from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import re

class DataFormat(str, Enum):
    TEXT = 'text'
    JSON = 'json'
    XML = 'xml'
    CSV = 'csv'
    FORM_URLENCODED = 'form_urlencoded'
    MULTIPART = 'multipart'
    YAML = 'yaml'
    UNKNOWN = 'unknown'

class ValidationLevel(str, Enum):
    FORMAT = 'format'
    LOGIC = 'logic'
    BUSINESS = 'business'

class ProcessingStatus(str, Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    VALIDATING = 'validating'
    VALIDATED = 'validated'
    EXTRACTING = 'extracting'
    EXTRACTED = 'extracted'
    REPAIRING = 'repairing'
    REPAIRED = 'repaired'
    HUMAN_REVIEW = 'human_review'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'

@dataclass
class ValidationError:
    level: ValidationLevel
    code: str
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    severity: str = 'error'
    auto_repairable: bool = False
    repair_suggestion: Optional[str] = None

@dataclass
class ExtractedEntity:
    entity_type: str
    value: Any
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    confidence: float = 1.0
    source: str = 'extractor'
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProcessingResult:
    status: ProcessingStatus
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    entities: List[ExtractedEntity] = field(default_factory=list)
    format: DataFormat = DataFormat.UNKNOWN
    raw_data: Optional[str] = None
    structured_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0
    
    @property
    def has_errors(self) -> bool:
        return any(e.severity == 'error' for e in self.errors)
    
    @property
    def critical_errors(self) -> List[ValidationError]:
        return [e for e in self.errors if e.severity == 'error']
    
    @property
    def needs_human_review(self) -> bool:
        return any(e.auto_repairable == False and e.severity == 'error' for e in self.errors)
    
    def get_errors_by_level(self, level: ValidationLevel) -> List[ValidationError]:
        return [e for e in self.errors if e.level == level]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'data': self.data,
            'errors': [
                {
                    'level': e.level.value,
                    'code': e.code,
                    'message': e.message,
                    'field': e.field,
                    'value': e.value,
                    'severity': e.severity,
                    'auto_repairable': e.auto_repairable,
                    'repair_suggestion': e.repair_suggestion
                }
                for e in self.errors
            ],
            'warnings': [
                {
                    'level': w.level.value,
                    'code': w.code,
                    'message': w.message,
                    'field': w.field,
                    'value': w.value,
                    'severity': w.severity
                }
                for w in self.warnings
            ],
            'entities': [
                {
                    'entity_type': e.entity_type,
                    'value': e.value,
                    'start_index': e.start_index,
                    'end_index': e.end_index,
                    'confidence': e.confidence,
                    'source': e.source,
                    'metadata': e.metadata
                }
                for e in self.entities
            ],
            'format': self.format.value,
            'structured_data': self.structured_data,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'processing_time_ms': self.processing_time_ms,
            'has_errors': self.has_errors,
            'needs_human_review': self.needs_human_review
        }

@dataclass
class ProcessingContext:
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    message_id: Optional[str] = None
    sequence_number: Optional[int] = None
    language: str = 'en'
    history: List[Dict[str, Any]] = field(default_factory=list)
    session_data: Dict[str, Any] = field(default_factory=dict)
    user_profile: Dict[str, Any] = field(default_factory=dict)
    business_rules: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

class DataProcessingPipeline:
    def __init__(self):
        self.processors: Dict[str, Callable] = {}
        self.validators: Dict[ValidationLevel, List[Callable]] = {
            ValidationLevel.FORMAT: [],
            ValidationLevel.LOGIC: [],
            ValidationLevel.BUSINESS: []
        }
        self.extractors: List[Callable] = []
        self.repairers: Dict[str, Callable] = {}
        self.hooks: Dict[str, List[Callable]] = {
            'before_process': [],
            'after_process': [],
            'on_error': [],
            'on_repair': [],
            'on_human_review': []
        }
    
    def register_processor(self, name: str, processor: Callable):
        self.processors[name] = processor
    
    def register_validator(self, level: ValidationLevel, validator: Callable):
        self.validators[level].append(validator)
    
    def register_extractor(self, extractor: Callable):
        self.extractors.append(extractor)
    
    def register_repairer(self, error_code: str, repairer: Callable):
        self.repairers[error_code] = repairer
    
    def register_hook(self, hook_type: str, hook: Callable):
        if hook_type in self.hooks:
            self.hooks[hook_type].append(hook)
    
    def _run_hooks(self, hook_type: str, *args, **kwargs):
        for hook in self.hooks.get(hook_type, []):
            try:
                hook(*args, **kwargs)
            except Exception as e:
                print(f"Hook {hook_type} error: {e}")
    
    def process(self, raw_data: Any, context: Optional[ProcessingContext] = None) -> ProcessingResult:
        start_time = datetime.now()
        context = context or ProcessingContext()
        
        result = ProcessingResult(
            status=ProcessingStatus.PENDING,
            raw_data=str(raw_data) if raw_data is not None else None
        )
        
        self._run_hooks('before_process', raw_data, context, result)
        
        try:
            result.status = ProcessingStatus.PROCESSING
            result = self._process_format(raw_data, result, context)
            
            result.status = ProcessingStatus.VALIDATING
            result = self._validate_all_levels(result, context)
            
            if result.has_errors:
                result.status = ProcessingStatus.REPAIRING
                result = self._attempt_auto_repair(result, context)
            
            if result.has_errors:
                if result.needs_human_review:
                    result.status = ProcessingStatus.HUMAN_REVIEW
                    self._run_hooks('on_human_review', result, context)
                else:
                    result.status = ProcessingStatus.FAILED
                    self._run_hooks('on_error', result, context)
            else:
                result.status = ProcessingStatus.EXTRACTING
                result = self._extract_information(result, context)
                
                result.status = ProcessingStatus.VALIDATED
                result = self._finalize_processing(result, context)
                
                result.status = ProcessingStatus.COMPLETED
        
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.errors.append(ValidationError(
                level=ValidationLevel.FORMAT,
                code='PROCESSING_EXCEPTION',
                message=f'Processing failed with exception: {str(e)}',
                severity='error',
                auto_repairable=False
            ))
            self._run_hooks('on_error', result, context, e)
        
        end_time = datetime.now()
        result.processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        self._run_hooks('after_process', result, context)
        
        return result
    
    def _process_format(self, raw_data: Any, result: ProcessingResult, 
                        context: ProcessingContext) -> ProcessingResult:
        if isinstance(raw_data, dict):
            result.format = DataFormat.JSON
            result.structured_data = raw_data
        elif isinstance(raw_data, str):
            result.format = self._detect_format(raw_data)
            result.structured_data = self._parse_format(raw_data, result.format)
        else:
            result.format = DataFormat.TEXT
            result.structured_data = {'raw_text': str(raw_data)}
        
        result.metadata['format_detected'] = result.format.value
        return result
    
    def _detect_format(self, text: str) -> DataFormat:
        text_stripped = text.strip()
        
        if text_stripped.startswith('{') and text_stripped.endswith('}'):
            try:
                json.loads(text)
                return DataFormat.JSON
            except json.JSONDecodeError:
                pass
        
        if text_stripped.startswith('<') and text_stripped.endswith('>'):
            return DataFormat.XML
        
        if ',' in text_stripped and '\n' in text_stripped[:500]:
            return DataFormat.CSV
        
        if '=' in text_stripped and '&' in text_stripped[:200]:
            return DataFormat.FORM_URLENCODED
        
        if 'Content-Disposition' in text_stripped[:500] or '--' in text_stripped[:100]:
            return DataFormat.MULTIPART
        
        if text_stripped.startswith('---') or ':' in text_stripped.split('\n')[0] if '\n' in text_stripped else False:
            return DataFormat.YAML
        
        return DataFormat.TEXT
    
    def _parse_format(self, text: str, format_type: DataFormat) -> Dict[str, Any]:
        if format_type == DataFormat.JSON:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {'raw_text': text, 'parse_error': 'Invalid JSON'}
        
        if format_type == DataFormat.FORM_URLENCODED:
            result = {}
            for pair in text.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    result[key.strip()] = value.strip()
            return result if result else {'raw_text': text}
        
        if format_type == DataFormat.CSV:
            lines = text.strip().split('\n')
            if len(lines) < 2:
                return {'raw_text': text}
            headers = lines[0].split(',')
            rows = []
            for line in lines[1:]:
                cells = line.split(',')
                rows.append(dict(zip(headers, cells)))
            return {'headers': headers, 'rows': rows, 'row_count': len(rows)}
        
        return {'raw_text': text}
    
    def _validate_all_levels(self, result: ProcessingResult, 
                              context: ProcessingContext) -> ProcessingResult:
        for level in [ValidationLevel.FORMAT, ValidationLevel.LOGIC, ValidationLevel.BUSINESS]:
            for validator in self.validators[level]:
                try:
                    errors = validator(result.structured_data, context)
                    for error in errors:
                        if error.severity == 'warning':
                            result.warnings.append(error)
                        else:
                            result.errors.append(error)
                except Exception as e:
                    result.errors.append(ValidationError(
                        level=level,
                        code='VALIDATOR_EXCEPTION',
                        message=f'Validator failed: {str(e)}',
                        severity='error',
                        auto_repairable=False
                    ))
        
        result.metadata['validation_errors_by_level'] = {
            level.value: len(result.get_errors_by_level(level))
            for level in ValidationLevel
        }
        
        return result
    
    def _attempt_auto_repair(self, result: ProcessingResult, 
                              context: ProcessingContext) -> ProcessingResult:
        repairs_made = 0
        unrepairable_errors = []
        
        for error in result.errors:
            if error.auto_repairable and error.code in self.repairers:
                try:
                    repairer = self.repairers[error.code]
                    repaired_data = repairer(result.structured_data, error, context)
                    result.structured_data = repaired_data
                    repairs_made += 1
                    result.metadata[f'repaired_{error.code}'] = True
                    self._run_hooks('on_repair', error, result, context)
                except Exception as e:
                    unrepairable_errors.append(error)
            else:
                unrepairable_errors.append(error)
        
        result.errors = unrepairable_errors
        result.metadata['repairs_made'] = repairs_made
        
        return result
    
    def _extract_information(self, result: ProcessingResult, 
                              context: ProcessingContext) -> ProcessingResult:
        for extractor in self.extractors:
            try:
                entities = extractor(result.structured_data, context)
                result.entities.extend(entities)
            except Exception as e:
                result.warnings.append(ValidationError(
                    level=ValidationLevel.LOGIC,
                    code='EXTRACTOR_WARNING',
                    message=f'Extractor failed: {str(e)}',
                    severity='warning'
                ))
        
        result.metadata['entities_extracted'] = len(result.entities)
        result.metadata['entity_types'] = list(set(e.entity_type for e in result.entities))
        
        return result
    
    def _finalize_processing(self, result: ProcessingResult, 
                             context: ProcessingContext) -> ProcessingResult:
        result.data = {
            'raw': result.raw_data,
            'structured': result.structured_data,
            'entities': [
                {'type': e.entity_type, 'value': e.value, 'confidence': e.confidence}
                for e in result.entities
            ],
            'context': {
                'conversation_id': context.conversation_id,
                'user_id': context.user_id,
                'language': context.language
            } if context else {}
        }
        
        return result

data_pipeline = DataProcessingPipeline()
