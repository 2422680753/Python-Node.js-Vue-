from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from services.data_processing_pipeline import (
    DataProcessingPipeline, ProcessingResult, ProcessingStatus,
    ProcessingContext, ValidationLevel, ValidationError, DataFormat
)
from services.structured_parser import (
    StructuredParser, ParseResult, FormatDetector
)
from services.three_layer_validator import (
    ThreeLayerValidator, three_layer_validator, ValidationStatus
)
from services.dual_channel_repair import (
    DualChannelRepairManager, dual_channel_manager, RepairStatus, InterventionType
)
from services.data_quality_monitor import (
    DataQualityMonitor, data_quality_monitor, QualityDimension, AlertLevel
)

@dataclass
class EnhancedProcessingResult:
    success: bool
    raw_data: Any
    structured_data: Dict[str, Any] = field(default_factory=dict)
    format_detected: str = DataFormat.UNKNOWN.value
    format_confidence: float = 0.0
    
    validation_report: Optional[Dict[str, Any]] = None
    validation_passed: bool = False
    validation_errors: List[Dict[str, Any]] = field(default_factory=list)
    validation_warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    repair_result: Optional[Dict[str, Any]] = None
    auto_repaired: bool = False
    needs_human_review: bool = False
    repair_tasks: List[Dict[str, Any]] = field(default_factory=list)
    
    extracted_entities: List[Dict[str, Any]] = field(default_factory=list)
    intent_info: Dict[str, Any] = field(default_factory=dict)
    language_info: Dict[str, Any] = field(default_factory=dict)
    
    final_data: Dict[str, Any] = field(default_factory=dict)
    final_status: str = ProcessingStatus.FAILED.value
    
    processing_time_ms: float = 0.0
    stage_times: Dict[str, float] = field(default_factory=dict)
    
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    alert_triggered: bool = False
    
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'raw_data': str(self.raw_data) if self.raw_data else None,
            'structured_data': self.structured_data,
            'format_detected': self.format_detected,
            'format_confidence': self.format_confidence,
            'validation_report': self.validation_report,
            'validation_passed': self.validation_passed,
            'validation_errors': self.validation_errors,
            'validation_warnings': self.validation_warnings,
            'repair_result': self.repair_result,
            'auto_repaired': self.auto_repaired,
            'needs_human_review': self.needs_human_review,
            'repair_tasks': self.repair_tasks,
            'extracted_entities': self.extracted_entities,
            'intent_info': self.intent_info,
            'language_info': self.language_info,
            'final_data': self.final_data,
            'final_status': self.final_status,
            'processing_time_ms': self.processing_time_ms,
            'stage_times': self.stage_times,
            'quality_metrics': self.quality_metrics,
            'alert_triggered': self.alert_triggered,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }

class EnhancedDataPipeline:
    def __init__(self):
        self.parser = StructuredParser()
        self.validator = three_layer_validator
        self.repair_manager = dual_channel_manager
        self.quality_monitor = data_quality_monitor
        
        self.pre_process_hooks: List[Callable] = []
        self.post_process_hooks: List[Callable] = []
        self.error_hooks: List[Callable] = []
        
        self.pipeline_config = {
            'enable_parsing': True,
            'enable_validation': True,
            'enable_auto_repair': True,
            'enable_human_review': True,
            'enable_quality_monitoring': True,
            'stop_on_error': False,
            'max_repair_attempts': 3,
        }
    
    def register_pre_hook(self, hook: Callable):
        self.pre_process_hooks.append(hook)
    
    def register_post_hook(self, hook: Callable):
        self.post_process_hooks.append(hook)
    
    def register_error_hook(self, hook: Callable):
        self.error_hooks.append(hook)
    
    def _run_pre_hooks(self, data: Any, context: ProcessingContext) -> tuple:
        processed_data = data
        for hook in self.pre_process_hooks:
            try:
                processed_data = hook(processed_data, context)
            except Exception as e:
                print(f"Pre-process hook error: {e}")
        return processed_data, context
    
    def _run_post_hooks(self, result: EnhancedProcessingResult, context: ProcessingContext):
        for hook in self.post_process_hooks:
            try:
                hook(result, context)
            except Exception as e:
                print(f"Post-process hook error: {e}")
    
    def _run_error_hooks(self, error: Exception, result: EnhancedProcessingResult, context: ProcessingContext):
        for hook in self.error_hooks:
            try:
                hook(error, result, context)
            except Exception as e:
                print(f"Error hook error: {e}")
    
    def process(self, raw_data: Any, 
                context: Optional[ProcessingContext] = None,
                config_overrides: Optional[Dict[str, Any]] = None) -> EnhancedProcessingResult:
        overall_start = datetime.now()
        stage_times = {}
        context = context or ProcessingContext()
        
        config = {**self.pipeline_config, **(config_overrides or {})}
        
        result = EnhancedProcessingResult(
            success=False,
            raw_data=raw_data
        )
        
        try:
            data, context = self._run_pre_hooks(raw_data, context)
            
            if config['enable_parsing']:
                parse_start = datetime.now()
                parse_result = self._parse_data(data)
                stage_times['parsing'] = (datetime.now() - parse_start).total_seconds() * 1000
                
                result.format_detected = parse_result.format.value
                result.format_confidence = parse_result.metadata.get('confidence', 0.0)
                result.structured_data = parse_result.data
                
                if not parse_result.success:
                    result.error_message = parse_result.error_message
                    if config['stop_on_error']:
                        result.final_status = ProcessingStatus.FAILED.value
                        return result
            
            if config['enable_validation']:
                validate_start = datetime.now()
                validation_result = self._validate_data(
                    result.structured_data, context, config
                )
                stage_times['validation'] = (datetime.now() - validate_start).total_seconds() * 1000
                
                result.validation_report = validation_result
                result.validation_passed = validation_result.get('valid', False)
                result.validation_errors = self._extract_validation_errors(validation_result)
                result.validation_warnings = self._extract_validation_warnings(validation_result)
                
                if not result.validation_passed and config['enable_auto_repair']:
                    repair_start = datetime.now()
                    repair_result = self._repair_data(
                        result.structured_data,
                        result.validation_errors,
                        context,
                        config
                    )
                    stage_times['repair'] = (datetime.now() - repair_start).total_seconds() * 1000
                    
                    result.repair_result = repair_result
                    result.auto_repaired = repair_result.get('auto_repair', {}).get('success', False)
                    result.needs_human_review = repair_result.get('human_review', {}).get('required', False)
                    result.repair_tasks = repair_result.get('human_review', {}).get('tasks', [])
                    
                    if result.auto_repaired and repair_result.get('repaired_data'):
                        result.final_data = repair_result['repaired_data']
                    elif not result.needs_human_review:
                        result.final_data = result.structured_data
                else:
                    result.final_data = result.structured_data
            else:
                result.final_data = result.structured_data
                result.validation_passed = True
            
            if config['enable_quality_monitoring']:
                monitor_start = datetime.now()
                quality_metrics = self._monitor_quality(result, context)
                stage_times['quality_monitoring'] = (datetime.now() - monitor_start).total_seconds() * 1000
                result.quality_metrics = quality_metrics
            
            if result.needs_human_review:
                result.final_status = 'pending_human_review'
                result.success = False
            elif result.validation_passed or result.auto_repaired:
                result.final_status = ProcessingStatus.COMPLETED.value
                result.success = True
            else:
                result.final_status = ProcessingStatus.FAILED.value
                result.success = False
            
            overall_end = datetime.now()
            result.processing_time_ms = (overall_end - overall_start).total_seconds() * 1000
            result.stage_times = stage_times
            
            self._run_post_hooks(result, context)
            
            return result
            
        except Exception as e:
            import traceback
            result.success = False
            result.error_message = str(e)
            result.stack_trace = traceback.format_exc()
            result.final_status = ProcessingStatus.FAILED.value
            
            overall_end = datetime.now()
            result.processing_time_ms = (overall_end - overall_start).total_seconds() * 1000
            result.stage_times = stage_times
            
            self._run_error_hooks(e, result, context)
            
            return result
    
    def _parse_data(self, raw_data: Any) -> ParseResult:
        if isinstance(raw_data, dict):
            return ParseResult(
                format=DataFormat.JSON,
                data=raw_data,
                success=True,
                metadata={'source': 'already_structured'}
            )
        
        if isinstance(raw_data, str):
            return self.parser.auto_parse(raw_data)
        
        return ParseResult(
            format=DataFormat.TEXT,
            data={'raw_value': str(raw_data)},
            success=True,
            metadata={'source': 'converted_to_string'}
        )
    
    def _validate_data(self, data: Dict[str, Any], context: ProcessingContext,
                       config: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self.validator.validate_all(data, context)
        except Exception as e:
            return {
                'valid': False,
                'level': ValidationLevel.FORMAT.value,
                'overall_status': ValidationStatus.FAILED.value,
                'total_errors': 1,
                'format_report': {
                    'overall_status': ValidationStatus.FAILED.value,
                    'total_errors': 1,
                    'results': []
                },
                'logic_report': None,
                'business_report': None,
                'execution_time_ms': 0
            }
    
    def _extract_validation_errors(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        errors = []
        
        for level in ['format_report', 'logic_report', 'business_report']:
            level_report = report.get(level)
            if not level_report:
                continue
            
            for result in level_report.get('results', []):
                for error in result.get('errors', []):
                    errors.append({
                        'level': level_report.get('level'),
                        'rule_name': result.get('rule_name'),
                        'code': error.get('code'),
                        'message': error.get('message'),
                        'field': error.get('field'),
                        'value': error.get('value'),
                        'auto_repairable': error.get('auto_repairable', False),
                        'repair_suggestion': error.get('repair_suggestion')
                    })
        
        return errors
    
    def _extract_validation_warnings(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        warnings = []
        
        for level in ['format_report', 'logic_report', 'business_report']:
            level_report = report.get(level)
            if not level_report:
                continue
            
            for result in level_report.get('results', []):
                for warning in result.get('warnings', []):
                    warnings.append({
                        'level': level_report.get('level'),
                        'rule_name': result.get('rule_name'),
                        'code': warning.get('code'),
                        'message': warning.get('message'),
                        'field': warning.get('field'),
                        'value': warning.get('value')
                    })
        
        return warnings
    
    def _repair_data(self, data: Dict[str, Any], errors: List[Dict[str, Any]],
                     context: ProcessingContext, config: Dict[str, Any]) -> Dict[str, Any]:
        validation_errors = []
        for err in errors:
            level_map = {
                'format': ValidationLevel.FORMAT,
                'logic': ValidationLevel.LOGIC,
                'business': ValidationLevel.BUSINESS
            }
            level = level_map.get(err.get('level', 'format'), ValidationLevel.FORMAT)
            
            validation_errors.append(ValidationError(
                level=level,
                code=err.get('code', 'UNKNOWN_ERROR'),
                message=err.get('message', 'Validation error'),
                field=err.get('field'),
                value=err.get('value'),
                severity='error',
                auto_repairable=err.get('auto_repairable', False),
                repair_suggestion=err.get('repair_suggestion')
            ))
        
        return self.repair_manager.process_errors(data, validation_errors, context)
    
    def _monitor_quality(self, result: EnhancedProcessingResult, context: ProcessingContext) -> Dict[str, Any]:
        basic_result = ProcessingResult(
            status=ProcessingStatus(result.final_status),
            data=result.final_data,
            processing_time_ms=result.processing_time_ms
        )
        
        self.quality_monitor.record_processing(
            basic_result,
            result.validation_report,
            result.repair_result
        )
        
        return {
            'completeness': self._calculate_completeness(result),
            'correctness': self._calculate_correctness(result),
            'processing_time': result.processing_time_ms,
            'has_errors': len(result.validation_errors) > 0,
            'has_warnings': len(result.validation_warnings) > 0,
            'was_repaired': result.auto_repaired,
            'needs_review': result.needs_human_review
        }
    
    def _calculate_completeness(self, result: EnhancedProcessingResult) -> float:
        if not result.structured_data:
            return 0.0
        
        data = result.structured_data
        required_fields = ['content', 'text', 'message']
        
        found_count = sum(1 for field in required_fields if field in data)
        if found_count > 0:
            return 100.0
        
        if 'raw_text' in data or 'raw_value' in data:
            return 100.0
        
        if data:
            return 75.0
        
        return 0.0
    
    def _calculate_correctness(self, result: EnhancedProcessingResult) -> float:
        if not result.validation_errors:
            return 100.0
        
        total_possible = len(result.validation_errors) + 1
        errors = len(result.validation_errors)
        
        if result.auto_repaired:
            return max(50.0, 100.0 - (errors * 10))
        
        return max(0.0, 100.0 - (errors * 20))

enhanced_pipeline = EnhancedDataPipeline()
