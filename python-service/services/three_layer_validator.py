from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re
from services.data_processing_pipeline import ValidationLevel, ValidationError, ProcessingContext

class ValidationSeverity(str, Enum):
    CRITICAL = 'critical'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'

class ValidationStatus(str, Enum):
    PASSED = 'passed'
    FAILED = 'failed'
    WARNINGS = 'warnings'
    SKIPPED = 'skipped'

@dataclass
class ValidationRule:
    name: str
    level: ValidationLevel
    severity: ValidationSeverity = ValidationSeverity.ERROR
    description: str = ''
    enabled: bool = True
    auto_repairable: bool = False
    repair_strategy: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    rule: ValidationRule
    status: ValidationStatus
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

@dataclass
class ValidationReport:
    level: ValidationLevel
    overall_status: ValidationStatus
    results: List[ValidationResult] = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def total_errors(self) -> int:
        return sum(len(r.errors) for r in self.results)
    
    @property
    def total_warnings(self) -> int:
        return sum(len(r.warnings) for r in self.results)
    
    @property
    def passed_rules(self) -> int:
        return sum(1 for r in self.results if r.status == ValidationStatus.PASSED)
    
    @property
    def failed_rules(self) -> int:
        return sum(1 for r in self.results if r.status == ValidationStatus.FAILED)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'level': self.level.value,
            'overall_status': self.overall_status.value,
            'total_errors': self.total_errors,
            'total_warnings': self.total_warnings,
            'passed_rules': self.passed_rules,
            'failed_rules': self.failed_rules,
            'execution_time_ms': self.execution_time_ms,
            'timestamp': self.timestamp.isoformat(),
            'results': [
                {
                    'rule_name': r.rule.name,
                    'status': r.status.value,
                    'errors': [
                        {
                            'code': e.code,
                            'message': e.message,
                            'field': e.field,
                            'value': e.value,
                            'auto_repairable': e.auto_repairable
                        }
                        for e in r.errors
                    ],
                    'warnings': [
                        {
                            'code': w.code,
                            'message': w.message,
                            'field': w.field
                        }
                        for w in r.warnings
                    ],
                    'execution_time_ms': r.execution_time_ms
                }
                for r in self.results
            ]
        }

class BaseValidator:
    LEVEL: ValidationLevel = ValidationLevel.FORMAT
    RULES: List[ValidationRule] = []
    
    @classmethod
    def validate(cls, data: Dict[str, Any], context: Optional[ProcessingContext] = None) -> List[ValidationError]:
        raise NotImplementedError
    
    @classmethod
    def run_all_rules(cls, data: Dict[str, Any], 
                      context: Optional[ProcessingContext] = None) -> ValidationReport:
        start_time = datetime.now()
        results = []
        context = context or ProcessingContext()
        
        for rule in cls.RULES:
            if not rule.enabled:
                continue
            
            rule_start = datetime.now()
            try:
                errors = cls._run_rule(data, rule, context)
                rule_end = datetime.now()
                
                if errors:
                    actual_errors = [e for e in errors if e.severity in ['critical', 'error']]
                    warnings = [e for e in errors if e.severity == 'warning']
                    
                    status = ValidationStatus.FAILED if actual_errors else ValidationStatus.WARNINGS
                    
                    results.append(ValidationResult(
                        rule=rule,
                        status=status,
                        errors=actual_errors,
                        warnings=warnings,
                        execution_time_ms=(rule_end - rule_start).total_seconds() * 1000
                    ))
                else:
                    results.append(ValidationResult(
                        rule=rule,
                        status=ValidationStatus.PASSED,
                        execution_time_ms=(rule_end - rule_start).total_seconds() * 1000
                    ))
            except Exception as e:
                rule_end = datetime.now()
                results.append(ValidationResult(
                    rule=rule,
                    status=ValidationStatus.FAILED,
                    errors=[
                        ValidationError(
                            level=cls.LEVEL,
                            code='RUNTIME_ERROR',
                            message=f'Validator runtime error: {str(e)}',
                            severity='error',
                            auto_repairable=False
                        )
                    ],
                    execution_time_ms=(rule_end - rule_start).total_seconds() * 1000
                ))
        
        end_time = datetime.now()
        
        has_errors = any(r.status == ValidationStatus.FAILED for r in results)
        has_warnings = any(r.status == ValidationStatus.WARNINGS for r in results)
        
        if has_errors:
            overall_status = ValidationStatus.FAILED
        elif has_warnings:
            overall_status = ValidationStatus.WARNINGS
        else:
            overall_status = ValidationStatus.PASSED
        
        return ValidationReport(
            level=cls.LEVEL,
            overall_status=overall_status,
            results=results,
            execution_time_ms=(end_time - start_time).total_seconds() * 1000
        )
    
    @classmethod
    def _run_rule(cls, data: Dict[str, Any], rule: ValidationRule, 
                  context: ProcessingContext) -> List[ValidationError]:
        raise NotImplementedError

class FormatValidator(BaseValidator):
    LEVEL = ValidationLevel.FORMAT
    
    RULES = [
        ValidationRule(
            name='required_fields',
            level=ValidationLevel.FORMAT,
            severity=ValidationSeverity.ERROR,
            description='Validate required fields exist',
            auto_repairable=False
        ),
        ValidationRule(
            name='field_types',
            level=ValidationLevel.FORMAT,
            severity=ValidationSeverity.ERROR,
            description='Validate field data types',
            auto_repairable=True,
            repair_strategy='type_conversion'
        ),
        ValidationRule(
            name='string_length',
            level=ValidationLevel.FORMAT,
            severity=ValidationSeverity.WARNING,
            description='Validate string field lengths',
            auto_repairable=True,
            repair_strategy='truncate'
        ),
        ValidationRule(
            name='numeric_ranges',
            level=ValidationLevel.FORMAT,
            severity=ValidationSeverity.ERROR,
            description='Validate numeric value ranges',
            auto_repairable=True,
            repair_strategy='clamp'
        ),
        ValidationRule(
            name='json_structure',
            level=ValidationLevel.FORMAT,
            severity=ValidationSeverity.ERROR,
            description='Validate JSON structure integrity',
            auto_repairable=False
        ),
        ValidationRule(
            name='encoding_format',
            level=ValidationLevel.FORMAT,
            severity=ValidationSeverity.WARNING,
            description='Validate character encoding',
            auto_repairable=True,
            repair_strategy='normalization'
        ),
    ]
    
    REQUIRED_FIELDS = {
        'message': ['content'],
        'order': ['order_id', 'user_id'],
        'user': ['user_id'],
    }
    
    FIELD_TYPES = {
        'content': str,
        'message_id': str,
        'conversation_id': str,
        'user_id': str,
        'order_id': str,
        'amount': (int, float),
        'quantity': int,
        'timestamp': (str, int, float),
        'language': str,
        'confidence': float,
    }
    
    STRING_LENGTHS = {
        'content': {'min': 1, 'max': 10000},
        'message_id': {'min': 10, 'max': 100},
        'conversation_id': {'min': 10, 'max': 100},
        'user_id': {'min': 5, 'max': 100},
        'order_id': {'min': 6, 'max': 50},
        'language': {'min': 2, 'max': 5},
    }
    
    NUMERIC_RANGES = {
        'amount': {'min': 0, 'max': 1000000},
        'quantity': {'min': 0, 'max': 10000},
        'confidence': {'min': 0.0, 'max': 1.0},
    }
    
    @classmethod
    def validate(cls, data: Dict[str, Any], 
                 context: Optional[ProcessingContext] = None) -> List[ValidationError]:
        report = cls.run_all_rules(data, context)
        return report.results[0].errors if report.results else []
    
    @classmethod
    def _run_rule(cls, data: Dict[str, Any], rule: ValidationRule,
                  context: ProcessingContext) -> List[ValidationError]:
        errors = []
        
        if rule.name == 'required_fields':
            errors.extend(cls._check_required_fields(data, context))
        elif rule.name == 'field_types':
            errors.extend(cls._check_field_types(data))
        elif rule.name == 'string_length':
            errors.extend(cls._check_string_lengths(data))
        elif rule.name == 'numeric_ranges':
            errors.extend(cls._check_numeric_ranges(data))
        
        return errors
    
    @classmethod
    def _check_required_fields(cls, data: Dict[str, Any], 
                               context: ProcessingContext) -> List[ValidationError]:
        errors = []
        
        if 'type' in data:
            data_type = data['type']
            if data_type in cls.REQUIRED_FIELDS:
                for field in cls.REQUIRED_FIELDS[data_type]:
                    if field not in data or data[field] is None:
                        errors.append(ValidationError(
                            level=ValidationLevel.FORMAT,
                            code='MISSING_REQUIRED_FIELD',
                            message=f'Required field missing: {field}',
                            field=field,
                            severity='error',
                            auto_repairable=False
                        ))
        
        if 'raw_text' in data and not data['raw_text'].strip():
            errors.append(ValidationError(
                level=ValidationLevel.FORMAT,
                code='EMPTY_CONTENT',
                message='Message content cannot be empty',
                field='raw_text',
                value='',
                severity='error',
                auto_repairable=False
            ))
        
        return errors
    
    @classmethod
    def _check_field_types(cls, data: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        
        for field, expected_type in cls.FIELD_TYPES.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    errors.append(ValidationError(
                        level=ValidationLevel.FORMAT,
                        code='TYPE_MISMATCH',
                        message=f'Field {field} has invalid type. Expected {expected_type}, got {type(data[field])}',
                        field=field,
                        value=data[field],
                        severity='error',
                        auto_repairable=True,
                        repair_suggestion=f'Convert to {expected_type}'
                    ))
        
        return errors
    
    @classmethod
    def _check_string_lengths(cls, data: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        
        for field, constraints in cls.STRING_LENGTHS.items():
            if field in data and isinstance(data[field], str):
                value = data[field]
                min_len = constraints.get('min', 0)
                max_len = constraints.get('max', float('inf'))
                
                if len(value) < min_len:
                    errors.append(ValidationError(
                        level=ValidationLevel.FORMAT,
                        code='STRING_TOO_SHORT',
                        message=f'Field {field} is too short. Min length: {min_len}',
                        field=field,
                        value=value,
                        severity='warning',
                        auto_repairable=True,
                        repair_suggestion='Pad with default value'
                    ))
                
                if len(value) > max_len:
                    errors.append(ValidationError(
                        level=ValidationLevel.FORMAT,
                        code='STRING_TOO_LONG',
                        message=f'Field {field} is too long. Max length: {max_len}',
                        field=field,
                        value=value[:50] + '...' if len(value) > 50 else value,
                        severity='warning',
                        auto_repairable=True,
                        repair_suggestion=f'Truncate to {max_len} characters'
                    ))
        
        return errors
    
    @classmethod
    def _check_numeric_ranges(cls, data: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        
        for field, constraints in cls.NUMERIC_RANGES.items():
            if field in data and isinstance(data[field], (int, float)):
                value = data[field]
                min_val = constraints.get('min', float('-inf'))
                max_val = constraints.get('max', float('inf'))
                
                if value < min_val:
                    errors.append(ValidationError(
                        level=ValidationLevel.FORMAT,
                        code='VALUE_BELOW_MIN',
                        message=f'Field {field} is below minimum: {min_val}',
                        field=field,
                        value=value,
                        severity='error',
                        auto_repairable=True,
                        repair_suggestion=f'Clamp to {min_val}'
                    ))
                
                if value > max_val:
                    errors.append(ValidationError(
                        level=ValidationLevel.FORMAT,
                        code='VALUE_ABOVE_MAX',
                        message=f'Field {field} exceeds maximum: {max_val}',
                        field=field,
                        value=value,
                        severity='error',
                        auto_repairable=True,
                        repair_suggestion=f'Clamp to {max_val}'
                    ))
        
        return errors

class LogicValidator(BaseValidator):
    LEVEL = ValidationLevel.LOGIC
    
    RULES = [
        ValidationRule(
            name='reference_integrity',
            level=ValidationLevel.LOGIC,
            severity=ValidationSeverity.ERROR,
            description='Validate references between entities',
            auto_repairable=False
        ),
        ValidationRule(
            name='temporal_consistency',
            level=ValidationLevel.LOGIC,
            severity=ValidationSeverity.ERROR,
            description='Validate temporal relationships',
            auto_repairable=False
        ),
        ValidationRule(
            name='business_constraints',
            level=ValidationLevel.LOGIC,
            severity=ValidationSeverity.ERROR,
            description='Validate business logic constraints',
            auto_repairable=False
        ),
        ValidationRule(
            name='data_completeness',
            level=ValidationLevel.LOGIC,
            severity=ValidationSeverity.WARNING,
            description='Validate data completeness',
            auto_repairable=True,
            repair_strategy='fill_defaults'
        ),
        ValidationRule(
            name='duplicate_detection',
            level=ValidationLevel.LOGIC,
            severity=ValidationSeverity.WARNING,
            description='Detect duplicate data',
            auto_repairable=True,
            repair_strategy='deduplicate'
        ),
    ]
    
    @classmethod
    def validate(cls, data: Dict[str, Any], 
                 context: Optional[ProcessingContext] = None) -> List[ValidationError]:
        report = cls.run_all_rules(data, context)
        all_errors = []
        for result in report.results:
            all_errors.extend(result.errors)
        return all_errors
    
    @classmethod
    def _run_rule(cls, data: Dict[str, Any], rule: ValidationRule,
                  context: ProcessingContext) -> List[ValidationError]:
        errors = []
        
        if rule.name == 'reference_integrity':
            errors.extend(cls._check_reference_integrity(data, context))
        elif rule.name == 'temporal_consistency':
            errors.extend(cls._check_temporal_consistency(data, context))
        elif rule.name == 'data_completeness':
            errors.extend(cls._check_data_completeness(data))
        
        return errors
    
    @classmethod
    def _check_reference_integrity(cls, data: Dict[str, Any], 
                                    context: ProcessingContext) -> List[ValidationError]:
        errors = []
        
        if 'order_id' in data:
            order_id = data['order_id']
            if not cls._is_valid_order_id_format(order_id):
                errors.append(ValidationError(
                    level=ValidationLevel.LOGIC,
                    code='INVALID_ORDER_ID_FORMAT',
                    message=f'Order ID format is invalid: {order_id}',
                    field='order_id',
                    value=order_id,
                    severity='error',
                    auto_repairable=False
                ))
        
        if 'user_id' in data:
            user_id = data['user_id']
            if not cls._is_valid_user_id_format(user_id):
                errors.append(ValidationError(
                    level=ValidationLevel.LOGIC,
                    code='INVALID_USER_ID_FORMAT',
                    message=f'User ID format is invalid: {user_id}',
                    field='user_id',
                    value=user_id,
                    severity='error',
                    auto_repairable=False
                ))
        
        return errors
    
    @classmethod
    def _is_valid_order_id_format(cls, order_id: str) -> bool:
        if not order_id or not isinstance(order_id, str):
            return False
        pattern = r'^[A-Z0-9_-]{6,30}$'
        return bool(re.match(pattern, order_id, re.IGNORECASE))
    
    @classmethod
    def _is_valid_user_id_format(cls, user_id: str) -> bool:
        if not user_id or not isinstance(user_id, str):
            return False
        if len(user_id) < 5 or len(user_id) > 100:
            return False
        return True
    
    @classmethod
    def _check_temporal_consistency(cls, data: Dict[str, Any], 
                                     context: ProcessingContext) -> List[ValidationError]:
        errors = []
        
        if 'start_time' in data and 'end_time' in data:
            start = data['start_time']
            end = data['end_time']
            
            try:
                start_ts = cls._to_timestamp(start)
                end_ts = cls._to_timestamp(end)
                
                if start_ts > end_ts:
                    errors.append(ValidationError(
                        level=ValidationLevel.LOGIC,
                        code='TEMPORAL_INCONSISTENCY',
                        message=f'Start time ({start}) is after end time ({end})',
                        field='start_time',
                        value=start,
                        severity='error',
                        auto_repairable=False
                    ))
            except (ValueError, TypeError):
                pass
        
        if context.sequence_number is not None and context.history:
            last_seq = max(h.get('sequence_number', 0) for h in context.history) if context.history else 0
            if context.sequence_number <= last_seq:
                errors.append(ValidationError(
                    level=ValidationLevel.LOGIC,
                    code='SEQUENCE_OUT_OF_ORDER',
                    message=f'Sequence number {context.sequence_number} is not after last sequence {last_seq}',
                    field='sequence_number',
                    value=context.sequence_number,
                    severity='error',
                    auto_repairable=True,
                    repair_suggestion=f'Use next sequence: {last_seq + 1}'
                ))
        
        return errors
    
    @classmethod
    def _to_timestamp(cls, value) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.timestamp()
            except ValueError:
                return 0
        return 0
    
    @classmethod
    def _check_data_completeness(cls, data: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        
        if 'entities' in data and not data['entities']:
            errors.append(ValidationError(
                level=ValidationLevel.LOGIC,
                code='NO_ENTITIES_EXTRACTED',
                message='No entities were extracted from the data',
                field='entities',
                value=[],
                severity='warning',
                auto_repairable=True,
                repair_suggestion='Re-extract with different parameters'
            ))
        
        if 'intent' in data and data.get('intent') == 'unknown':
            if data.get('confidence', 1.0) < 0.5:
                errors.append(ValidationError(
                    level=ValidationLevel.LOGIC,
                    code='LOW_CONFIDENCE_INTENT',
                    message=f'Intent classification has low confidence: {data.get("confidence")}',
                    field='intent',
                    value=data.get('intent'),
                    severity='warning',
                    auto_repairable=False
                ))
        
        return errors

class BusinessValidator(BaseValidator):
    LEVEL = ValidationLevel.BUSINESS
    
    RULES = [
        ValidationRule(
            name='order_validation',
            level=ValidationLevel.BUSINESS,
            severity=ValidationSeverity.ERROR,
            description='Validate order business rules',
            auto_repairable=False
        ),
        ValidationRule(
            name='payment_validation',
            level=ValidationLevel.BUSINESS,
            severity=ValidationSeverity.CRITICAL,
            description='Validate payment business rules',
            auto_repairable=False
        ),
        ValidationRule(
            name='shipping_validation',
            level=ValidationLevel.BUSINESS,
            severity=ValidationSeverity.ERROR,
            description='Validate shipping business rules',
            auto_repairable=False
        ),
        ValidationRule(
            name='user_policy',
            level=ValidationLevel.BUSINESS,
            severity=ValidationSeverity.ERROR,
            description='Validate user policies',
            auto_repairable=False
        ),
        ValidationRule(
            name='content_policy',
            level=ValidationLevel.BUSINESS,
            severity=ValidationSeverity.ERROR,
            description='Validate content policies',
            auto_repairable=True,
            repair_strategy='sanitize'
        ),
        ValidationRule(
            name='escalation_rules',
            level=ValidationLevel.BUSINESS,
            severity=ValidationSeverity.WARNING,
            description='Validate escalation business rules',
            auto_repairable=False
        ),
    ]
    
    MAX_ORDER_AMOUNT = 100000
    MIN_ORDER_AMOUNT = 0
    MAX_REFUND_PERIOD_DAYS = 30
    SENSITIVE_KEYWORDS = ['密码', 'password', 'secret', 'token', '凭证', '密钥']
    
    @classmethod
    def validate(cls, data: Dict[str, Any], 
                 context: Optional[ProcessingContext] = None) -> List[ValidationError]:
        report = cls.run_all_rules(data, context)
        all_errors = []
        for result in report.results:
            all_errors.extend(result.errors)
        return all_errors
    
    @classmethod
    def _run_rule(cls, data: Dict[str, Any], rule: ValidationRule,
                  context: ProcessingContext) -> List[ValidationError]:
        errors = []
        
        if rule.name == 'order_validation':
            errors.extend(cls._validate_order_rules(data, context))
        elif rule.name == 'content_policy':
            errors.extend(cls._validate_content_policy(data, context))
        elif rule.name == 'escalation_rules':
            errors.extend(cls._validate_escalation_rules(data, context))
        
        return errors
    
    @classmethod
    def _validate_order_rules(cls, data: Dict[str, Any], 
                               context: ProcessingContext) -> List[ValidationError]:
        errors = []
        
        if 'amount' in data:
            amount = data['amount']
            if isinstance(amount, (int, float)):
                if amount < cls.MIN_ORDER_AMOUNT:
                    errors.append(ValidationError(
                        level=ValidationLevel.BUSINESS,
                        code='ORDER_AMOUNT_TOO_LOW',
                        message=f'Order amount {amount} is below minimum {cls.MIN_ORDER_AMOUNT}',
                        field='amount',
                        value=amount,
                        severity='error',
                        auto_repairable=False
                    ))
                
                if amount > cls.MAX_ORDER_AMOUNT:
                    errors.append(ValidationError(
                        level=ValidationLevel.BUSINESS,
                        code='ORDER_AMOUNT_TOO_HIGH',
                        message=f'Order amount {amount} exceeds maximum {cls.MAX_ORDER_AMOUNT}. Manual review required.',
                        field='amount',
                        value=amount,
                        severity='error',
                        auto_repairable=False
                    ))
        
        if 'intent' in data:
            intent = data['intent']
            
            if intent in ['refund', 'return', 'exchange']:
                if context and context.history:
                    order_time = cls._extract_order_time(context)
                    if order_time:
                        days_since = (datetime.now() - order_time).days
                        if days_since > cls.MAX_REFUND_PERIOD_DAYS:
                            errors.append(ValidationError(
                                level=ValidationLevel.BUSINESS,
                                code='REFUND_PERIOD_EXPIRED',
                                message=f'Refund period of {cls.MAX_REFUND_PERIOD_DAYS} days has expired',
                                field='intent',
                                value=intent,
                                severity='error',
                                auto_repairable=False
                            ))
        
        return errors
    
    @classmethod
    def _extract_order_time(cls, context: ProcessingContext) -> Optional[datetime]:
        for item in context.history:
            if 'timestamp' in item:
                try:
                    if isinstance(item['timestamp'], str):
                        return datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                    elif isinstance(item['timestamp'], (int, float)):
                        return datetime.fromtimestamp(item['timestamp'])
                except (ValueError, TypeError):
                    continue
        return None
    
    @classmethod
    def _validate_content_policy(cls, data: Dict[str, Any], 
                                  context: ProcessingContext) -> List[ValidationError]:
        errors = []
        
        text_fields = ['content', 'raw_text', 'text', 'message']
        
        for field in text_fields:
            if field in data and isinstance(data[field], str):
                text = data[field].lower()
                
                for keyword in cls.SENSITIVE_KEYWORDS:
                    if keyword.lower() in text:
                        errors.append(ValidationError(
                            level=ValidationLevel.BUSINESS,
                            code='SENSITIVE_CONTENT_DETECTED',
                            message=f'Sensitive keyword detected: {keyword}',
                            field=field,
                            value=keyword,
                            severity='error',
                            auto_repairable=True,
                            repair_suggestion='Sanitize sensitive content'
                        ))
        
        return errors
    
    @classmethod
    def _validate_escalation_rules(cls, data: Dict[str, Any], 
                                     context: ProcessingContext) -> List[ValidationError]:
        errors = []
        
        if 'shouldEscalate' in data and data['shouldEscalate']:
            confidence = data.get('confidence', 1.0)
            intent = data.get('intent', 'unknown')
            
            escalation_threshold = context.business_rules.get('escalation_threshold', 0.4) if context else 0.4
            
            if confidence >= escalation_threshold:
                if intent in ['refund', 'complaint', 'technical_support']:
                    pass
                else:
                    errors.append(ValidationError(
                        level=ValidationLevel.BUSINESS,
                        code='UNNECESSARY_ESCALATION',
                        message=f'Escalation may not be necessary for intent: {intent} with confidence: {confidence}',
                        field='shouldEscalate',
                        value=data['shouldEscalate'],
                        severity='warning',
                        auto_repairable=True,
                        repair_suggestion='Review escalation decision'
                    ))
        
        if context and len(context.history) > 5:
            recent_intents = [h.get('intent') for h in context.history[-5:] if h.get('intent')]
            if len(recent_intents) >= 3 and len(set(recent_intents)) == 1:
                if recent_intents[0] not in ['greeting', 'goodbye']:
                    errors.append(ValidationError(
                        level=ValidationLevel.BUSINESS,
                        code='REPETITIVE_INTENT',
                        message=f'User is asking about the same intent ({recent_intents[0]}) multiple times. Consider escalation.',
                        field='intent',
                        value=recent_intents[0],
                        severity='warning',
                        auto_repairable=False
                    ))
        
        return errors

class ThreeLayerValidator:
    def __init__(self):
        self.format_validator = FormatValidator()
        self.logic_validator = LogicValidator()
        self.business_validator = BusinessValidator()
    
    def validate_all(self, data: Dict[str, Any], 
                     context: Optional[ProcessingContext] = None) -> Dict[str, Any]:
        context = context or ProcessingContext()
        overall_start = datetime.now()
        
        format_report = self.format_validator.run_all_rules(data, context)
        
        if format_report.overall_status == ValidationStatus.FAILED:
            return {
                'valid': False,
                'level': ValidationLevel.FORMAT.value,
                'format_report': format_report.to_dict(),
                'logic_report': None,
                'business_report': None,
                'overall_status': ValidationStatus.FAILED.value,
                'total_errors': format_report.total_errors,
                'execution_time_ms': (datetime.now() - overall_start).total_seconds() * 1000
            }
        
        logic_report = self.logic_validator.run_all_rules(data, context)
        
        if logic_report.overall_status == ValidationStatus.FAILED:
            return {
                'valid': False,
                'level': ValidationLevel.LOGIC.value,
                'format_report': format_report.to_dict(),
                'logic_report': logic_report.to_dict(),
                'business_report': None,
                'overall_status': ValidationStatus.FAILED.value,
                'total_errors': format_report.total_errors + logic_report.total_errors,
                'execution_time_ms': (datetime.now() - overall_start).total_seconds() * 1000
            }
        
        business_report = self.business_validator.run_all_rules(data, context)
        
        total_errors = (
            format_report.total_errors + 
            logic_report.total_errors + 
            business_report.total_errors
        )
        
        overall_status = ValidationStatus.PASSED.value
        if business_report.overall_status == ValidationStatus.FAILED:
            overall_status = ValidationStatus.FAILED.value
        elif (format_report.overall_status == ValidationStatus.WARNINGS or
              logic_report.overall_status == ValidationStatus.WARNINGS or
              business_report.overall_status == ValidationStatus.WARNINGS):
            overall_status = ValidationStatus.WARNINGS.value
        
        return {
            'valid': total_errors == 0,
            'level': ValidationLevel.BUSINESS.value,
            'format_report': format_report.to_dict(),
            'logic_report': logic_report.to_dict(),
            'business_report': business_report.to_dict(),
            'overall_status': overall_status,
            'total_errors': total_errors,
            'total_warnings': (
                format_report.total_warnings +
                logic_report.total_warnings +
                business_report.total_warnings
            ),
            'execution_time_ms': (datetime.now() - overall_start).total_seconds() * 1000
        }
    
    def validate_at_level(self, data: Dict[str, Any], level: ValidationLevel,
                          context: Optional[ProcessingContext] = None) -> ValidationReport:
        context = context or ProcessingContext()
        
        if level == ValidationLevel.FORMAT:
            return self.format_validator.run_all_rules(data, context)
        elif level == ValidationLevel.LOGIC:
            return self.logic_validator.run_all_rules(data, context)
        elif level == ValidationLevel.BUSINESS:
            return self.business_validator.run_all_rules(data, context)
        
        raise ValueError(f'Invalid validation level: {level}')

three_layer_validator = ThreeLayerValidator()
