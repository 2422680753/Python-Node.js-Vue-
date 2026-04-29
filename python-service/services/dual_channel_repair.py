from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re
import hashlib
from services.data_processing_pipeline import (
    ValidationLevel, ValidationError, ProcessingContext, ProcessingResult
)
from services.three_layer_validator import ValidationStatus, ValidationReport

class RepairStatus(str, Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'
    HUMAN_REVIEW = 'human_review'

class InterventionType(str, Enum):
    AUTO_REPAIR = 'auto_repair'
    HUMAN_REVIEW = 'human_review'
    HUMAN_EDIT = 'human_edit'
    HUMAN_APPROVAL = 'human_approval'
    HUMAN_REJECTION = 'human_rejection'

class RepairPriority(str, Enum):
    CRITICAL = 'critical'
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'

@dataclass
class RepairStrategy:
    name: str
    description: str
    repair_function: Optional[str] = None
    requires_approval: bool = False
    success_rate: float = 0.0
    total_attempts: int = 0
    successful_attempts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RepairTask:
    task_id: str
    data_id: str
    error_code: str
    error_message: str
    field: Optional[str] = None
    original_value: Optional[Any] = None
    suggested_repair: Optional[Any] = None
    repair_strategy: Optional[str] = None
    priority: RepairPriority = RepairPriority.MEDIUM
    status: RepairStatus = RepairStatus.PENDING
    intervention_type: InterventionType = InterventionType.AUTO_REPAIR
    requires_approval: bool = False
    approved: bool = False
    rejected: bool = False
    approver_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    repair_result: Optional[Dict[str, Any]] = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    parent_task_id: Optional[str] = None
    dependent_task_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HumanReviewQueue:
    queue_id: str
    name: str
    description: str
    tasks: List[RepairTask] = field(default_factory=list)
    assigned_agents: List[str] = field(default_factory=list)
    priority_threshold: RepairPriority = RepairPriority.MEDIUM
    sla_minutes: int = 60
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

class TypeConversionRepair:
    @staticmethod
    def repair(data: Dict[str, Any], error: ValidationError, 
               context: ProcessingContext) -> Dict[str, Any]:
        if not error.field:
            return data
        
        field = error.field
        value = error.value
        
        if value is None:
            return data
        
        if 'Convert to int' in (error.repair_suggestion or ''):
            try:
                if isinstance(value, str):
                    data[field] = int(float(value))
                elif isinstance(value, float):
                    data[field] = int(value)
            except (ValueError, TypeError):
                pass
        
        elif 'Convert to float' in (error.repair_suggestion or ''):
            try:
                if isinstance(value, str):
                    data[field] = float(value)
                elif isinstance(value, int):
                    data[field] = float(value)
            except (ValueError, TypeError):
                pass
        
        elif 'Convert to str' in (error.repair_suggestion or ''):
            try:
                data[field] = str(value)
            except (ValueError, TypeError):
                pass
        
        return data

class StringRepair:
    @staticmethod
    def truncate(data: Dict[str, Any], error: ValidationError,
                 context: ProcessingContext) -> Dict[str, Any]:
        if not error.field:
            return data
        
        field = error.field
        max_length = context.metadata.get('max_length', 1000)
        
        if field in data and isinstance(data[field], str):
            if len(data[field]) > max_length:
                data[field] = data[field][:max_length]
                if 'metadata' not in data:
                    data['metadata'] = {}
                data['metadata']['was_truncated'] = True
                data['metadata']['original_length'] = len(error.value or data[field])
        
        return data
    
    @staticmethod
    def normalize_whitespace(data: Dict[str, Any], error: ValidationError,
                             context: ProcessingContext) -> Dict[str, Any]:
        if not error.field:
            return data
        
        field = error.field
        
        if field in data and isinstance(data[field], str):
            data[field] = re.sub(r'\s+', ' ', data[field]).strip()
        
        return data
    
    @staticmethod
    def normalize_case(data: Dict[str, Any], error: ValidationError,
                       context: ProcessingContext) -> Dict[str, Any]:
        if not error.field:
            return data
        
        field = error.field
        target_case = context.metadata.get('target_case', 'lower')
        
        if field in data and isinstance(data[field], str):
            if target_case == 'upper':
                data[field] = data[field].upper()
            elif target_case == 'lower':
                data[field] = data[field].lower()
            elif target_case == 'title':
                data[field] = data[field].title()
        
        return data

class NumericRepair:
    @staticmethod
    def clamp(data: Dict[str, Any], error: ValidationError,
              context: ProcessingContext) -> Dict[str, Any]:
        if not error.field:
            return data
        
        field = error.field
        min_val = context.metadata.get('min', float('-inf'))
        max_val = context.metadata.get('max', float('inf'))
        
        if field in data and isinstance(data[field], (int, float)):
            if data[field] < min_val:
                data[field] = min_val
                if 'metadata' not in data:
                    data['metadata'] = {}
                data['metadata']['was_clamped'] = True
                data['metadata']['clamp_direction'] = 'min'
            elif data[field] > max_val:
                data[field] = max_val
                if 'metadata' not in data:
                    data['metadata'] = {}
                data['metadata']['was_clamped'] = True
                data['metadata']['clamp_direction'] = 'max'
        
        return data
    
    @staticmethod
    def round_precision(data: Dict[str, Any], error: ValidationError,
                        context: ProcessingContext) -> Dict[str, Any]:
        if not error.field:
            return data
        
        field = error.field
        decimal_places = context.metadata.get('decimal_places', 2)
        
        if field in data and isinstance(data[field], float):
            data[field] = round(data[field], decimal_places)
        
        return data

class SequenceRepair:
    @staticmethod
    def fix_sequence(data: Dict[str, Any], error: ValidationError,
                     context: ProcessingContext) -> Dict[str, Any]:
        if context.sequence_number is not None:
            history = context.history
            if history:
                last_seq = max(h.get('sequence_number', 0) for h in history)
                new_seq = last_seq + 1
                
                if 'sequence_number' in data:
                    data['sequence_number'] = new_seq
                
                if 'metadata' not in data:
                    data['metadata'] = {}
                data['metadata']['sequence_was_fixed'] = True
                data['metadata']['original_sequence'] = context.sequence_number
                data['metadata']['corrected_sequence'] = new_seq
        
        return data

class ContentRepair:
    SENSITIVE_REPLACEMENTS = {
        '密码': '[密码已隐藏]',
        'password': '[password hidden]',
        'secret': '[secret hidden]',
        'token': '[token hidden]',
        '凭证': '[凭证已隐藏]',
        '密钥': '[密钥已隐藏]',
    }
    
    @staticmethod
    def sanitize_sensitive(data: Dict[str, Any], error: ValidationError,
                           context: ProcessingContext) -> Dict[str, Any]:
        text_fields = ['content', 'raw_text', 'text', 'message']
        
        for field in text_fields:
            if field in data and isinstance(data[field], str):
                text = data[field]
                for keyword, replacement in ContentRepair.SENSITIVE_REPLACEMENTS.items():
                    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                    text = pattern.sub(replacement, text)
                data[field] = text
        
        if 'metadata' not in data:
            data['metadata'] = {}
        data['metadata']['was_sanitized'] = True
        
        return data
    
    @staticmethod
    def remove_duplicates(data: Dict[str, Any], error: ValidationError,
                          context: ProcessingContext) -> Dict[str, Any]:
        if 'entities' in data and isinstance(data['entities'], list):
            seen = set()
            unique_entities = []
            for entity in data['entities']:
                entity_key = f"{entity.get('entity_type')}:{entity.get('value')}"
                if entity_key not in seen:
                    seen.add(entity_key)
                    unique_entities.append(entity)
            data['entities'] = unique_entities
        
        return data

class AutoRepairEngine:
    REPAIR_STRATEGIES: Dict[str, Callable] = {
        'type_conversion': TypeConversionRepair.repair,
        'truncate': StringRepair.truncate,
        'normalize_whitespace': StringRepair.normalize_whitespace,
        'normalize_case': StringRepair.normalize_case,
        'clamp': NumericRepair.clamp,
        'round_precision': NumericRepair.round_precision,
        'fix_sequence': SequenceRepair.fix_sequence,
        'sanitize': ContentRepair.sanitize_sensitive,
        'deduplicate': ContentRepair.remove_duplicates,
    }
    
    ERROR_CODE_TO_STRATEGY: Dict[str, str] = {
        'TYPE_MISMATCH': 'type_conversion',
        'STRING_TOO_LONG': 'truncate',
        'VALUE_BELOW_MIN': 'clamp',
        'VALUE_ABOVE_MAX': 'clamp',
        'SEQUENCE_OUT_OF_ORDER': 'fix_sequence',
        'SENSITIVE_CONTENT_DETECTED': 'sanitize',
    }
    
    def __init__(self):
        self.repair_stats: Dict[str, Dict[str, int]] = {}
        self._init_stats()
    
    def _init_stats(self):
        for strategy in self.REPAIR_STRATEGIES.keys():
            self.repair_stats[strategy] = {
                'attempts': 0,
                'successes': 0,
                'failures': 0
            }
    
    def can_repair(self, error: ValidationError) -> bool:
        if not error.auto_repairable:
            return False
        
        if error.code in self.ERROR_CODE_TO_STRATEGY:
            return True
        
        if error.repair_suggestion:
            for strategy in self.REPAIR_STRATEGIES.keys():
                if strategy in error.repair_suggestion.lower():
                    return True
        
        return False
    
    def get_repair_strategy(self, error: ValidationError) -> Optional[str]:
        if error.code in self.ERROR_CODE_TO_STRATEGY:
            return self.ERROR_CODE_TO_STRATEGY[error.code]
        
        if error.repair_suggestion:
            suggestion_lower = error.repair_suggestion.lower()
            for strategy_name in self.REPAIR_STRATEGIES.keys():
                if strategy_name in suggestion_lower:
                    return strategy_name
        
        return None
    
    def attempt_repair(self, data: Dict[str, Any], error: ValidationError,
                       context: ProcessingContext) -> tuple:
        strategy_name = self.get_repair_strategy(error)
        
        if not strategy_name or strategy_name not in self.REPAIR_STRATEGIES:
            return data, False, 'No applicable repair strategy'
        
        strategy = self.REPAIR_STRATEGIES[strategy_name]
        stats = self.repair_stats[strategy_name]
        stats['attempts'] += 1
        
        try:
            original_hash = hashlib.md5(str(data).encode()).hexdigest()
            repaired_data = strategy(data, error, context)
            new_hash = hashlib.md5(str(repaired_data).encode()).hexdigest()
            
            if original_hash != new_hash:
                stats['successes'] += 1
                return repaired_data, True, f'Repaired using {strategy_name}'
            else:
                stats['failures'] += 1
                return data, False, f'Repair strategy {strategy_name} made no changes'
        
        except Exception as e:
            stats['failures'] += 1
            return data, False, f'Repair failed with exception: {str(e)}'
    
    def repair_all_auto(self, data: Dict[str, Any], errors: List[ValidationError],
                        context: ProcessingContext) -> tuple:
        repaired_data = data.copy()
        repair_results = []
        
        for error in errors:
            if self.can_repair(error):
                repaired_data, success, message = self.attempt_repair(
                    repaired_data, error, context
                )
                repair_results.append({
                    'error_code': error.code,
                    'error_message': error.message,
                    'success': success,
                    'message': message
                })
            else:
                repair_results.append({
                    'error_code': error.code,
                    'error_message': error.message,
                    'success': False,
                    'message': 'Auto-repair not available, requires human review'
                })
        
        all_repaired = all(r['success'] for r in repair_results)
        needs_human_review = any(
            not r['success'] and 'requires human review' in r['message'].lower()
            for r in repair_results
        )
        
        return repaired_data, all_repaired, needs_human_review, repair_results
    
    def get_stats(self) -> Dict[str, Any]:
        total_attempts = sum(s['attempts'] for s in self.repair_stats.values())
        total_successes = sum(s['successes'] for s in self.repair_stats.values())
        
        return {
            'total_attempts': total_attempts,
            'total_successes': total_successes,
            'success_rate': total_successes / total_attempts if total_attempts > 0 else 0,
            'strategies': self.repair_stats
        }

class HumanReviewManager:
    def __init__(self):
        self.queues: Dict[str, HumanReviewQueue] = {}
        self.tasks: Dict[str, RepairTask] = {}
        self._setup_default_queues()
    
    def _setup_default_queues(self):
        self.queues['critical'] = HumanReviewQueue(
            queue_id='critical',
            name='Critical Review Queue',
            description='For critical errors requiring immediate attention',
            priority_threshold=RepairPriority.CRITICAL,
            sla_minutes=15
        )
        
        self.queues['high'] = HumanReviewQueue(
            queue_id='high',
            name='High Priority Queue',
            description='For high priority errors',
            priority_threshold=RepairPriority.HIGH,
            sla_minutes=30
        )
        
        self.queues['standard'] = HumanReviewQueue(
            queue_id='standard',
            name='Standard Review Queue',
            description='For standard priority errors',
            priority_threshold=RepairPriority.MEDIUM,
            sla_minutes=60
        )
    
    def create_task(self, error: ValidationError, data: Dict[str, Any],
                    context: ProcessingContext) -> RepairTask:
        task_id = self._generate_task_id()
        
        priority = self._determine_priority(error)
        requires_approval = not error.auto_repairable
        
        task = RepairTask(
            task_id=task_id,
            data_id=context.message_id or self._generate_data_id(data),
            error_code=error.code,
            error_message=error.message,
            field=error.field,
            original_value=error.value,
            suggested_repair=error.repair_suggestion,
            priority=priority,
            intervention_type=(
                InterventionType.HUMAN_EDIT if requires_approval 
                else InterventionType.HUMAN_APPROVAL
            ),
            requires_approval=requires_approval,
            metadata={
                'context': {
                    'conversation_id': context.conversation_id,
                    'user_id': context.user_id,
                    'language': context.language
                },
                'original_data': data
            }
        )
        
        self.tasks[task_id] = task
        self._assign_to_queue(task)
        
        return task
    
    def _generate_task_id(self) -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        import random
        random_suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
        return f'REV-{timestamp}-{random_suffix}'
    
    def _generate_data_id(self, data: Dict[str, Any]) -> str:
        content = str(data.get('content', data.get('raw_text', '')))
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _determine_priority(self, error: ValidationError) -> RepairPriority:
        if error.severity == 'critical':
            return RepairPriority.CRITICAL
        elif error.severity == 'error':
            if error.code in ['MISSING_REQUIRED_FIELD', 'TEMPORAL_INCONSISTENCY']:
                return RepairPriority.HIGH
            return RepairPriority.MEDIUM
        else:
            return RepairPriority.LOW
    
    def _assign_to_queue(self, task: RepairTask):
        for queue in self.queues.values():
            if task.priority == queue.priority_threshold:
                queue.tasks.append(task)
                return
        
        self.queues['standard'].tasks.append(task)
    
    def get_tasks_for_agent(self, agent_id: str, limit: int = 10) -> List[RepairTask]:
        pending_tasks = [
            task for task in self.tasks.values()
            if task.status == RepairStatus.PENDING
        ]
        
        pending_tasks.sort(key=lambda t: (
            t.priority.value if hasattr(t.priority, 'value') else t.priority,
            t.created_at
        ))
        
        return pending_tasks[:limit]
    
    def claim_task(self, task_id: str, agent_id: str) -> Optional[RepairTask]:
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        if task.status != RepairStatus.PENDING:
            return None
        
        task.status = RepairStatus.IN_PROGRESS
        task.started_at = datetime.now()
        task.approver_id = agent_id
        
        return task
    
    def submit_review(self, task_id: str, agent_id: str, approved: bool,
                      corrected_data: Optional[Dict[str, Any]] = None,
                      rejection_reason: Optional[str] = None,
                      comment: Optional[str] = None) -> Optional[RepairTask]:
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        if task.status not in [RepairStatus.IN_PROGRESS, RepairStatus.PENDING]:
            return None
        
        task.status = RepairStatus.COMPLETED if approved else RepairStatus.HUMAN_REVIEW
        task.completed_at = datetime.now()
        task.approved = approved
        task.rejected = not approved
        task.approver_id = agent_id
        task.rejection_reason = rejection_reason
        
        if corrected_data:
            task.repair_result = {
                'corrected_data': corrected_data,
                'comment': comment
            }
        
        if task.started_at and task.completed_at:
            task.execution_time_ms = (
                task.completed_at - task.started_at
            ).total_seconds() * 1000
        
        return task
    
    def get_queue_stats(self) -> Dict[str, Any]:
        stats = {}
        
        for queue_id, queue in self.queues.items():
            pending = sum(1 for t in queue.tasks if t.status == RepairStatus.PENDING)
            in_progress = sum(1 for t in queue.tasks if t.status == RepairStatus.IN_PROGRESS)
            completed = sum(1 for t in queue.tasks if t.status == RepairStatus.COMPLETED)
            
            stats[queue_id] = {
                'name': queue.name,
                'description': queue.description,
                'pending': pending,
                'in_progress': in_progress,
                'completed': completed,
                'sla_minutes': queue.sla_minutes,
                'total_tasks': len(queue.tasks)
            }
        
        return stats

class DualChannelRepairManager:
    def __init__(self):
        self.auto_engine = AutoRepairEngine()
        self.human_manager = HumanReviewManager()
    
    def process_errors(self, data: Dict[str, Any], errors: List[ValidationError],
                       context: ProcessingContext) -> Dict[str, Any]:
        result = {
            'original_data': data,
            'repaired_data': None,
            'auto_repair': {
                'attempted': False,
                'success': False,
                'results': []
            },
            'human_review': {
                'required': False,
                'tasks': [],
                'queue': None
            },
            'final_status': 'pending'
        }
        
        auto_repairable_errors = [e for e in errors if e.auto_repairable]
        human_only_errors = [e for e in errors if not e.auto_repairable]
        
        if auto_repairable_errors:
            result['auto_repair']['attempted'] = True
            
            repaired_data, all_repaired, needs_review, repair_results = \
                self.auto_engine.repair_all_auto(data, auto_repairable_errors, context)
            
            result['auto_repair']['success'] = all_repaired
            result['auto_repair']['results'] = repair_results
            result['repaired_data'] = repaired_data
            
            if needs_review or not all_repaired:
                result['human_review']['required'] = True
        else:
            result['repaired_data'] = data
        
        if human_only_errors or result['human_review']['required']:
            result['human_review']['required'] = True
            
            all_errors_for_review = human_only_errors.copy()
            if result['auto_repair']['attempted'] and not result['auto_repair']['success']:
                for error in auto_repairable_errors:
                    error.auto_repairable = False
                    all_errors_for_review.append(error)
            
            tasks = []
            for error in all_errors_for_review:
                task = self.human_manager.create_task(error, result['repaired_data'], context)
                tasks.append({
                    'task_id': task.task_id,
                    'priority': task.priority.value,
                    'error_code': task.error_code,
                    'sla_minutes': self._get_sla_for_task(task)
                })
            
            result['human_review']['tasks'] = tasks
            result['human_review']['queue'] = 'critical' if any(
                t['priority'] == 'critical' for t in tasks
            ) else 'standard'
        
        if not result['human_review']['required'] and result['auto_repair']['success']:
            result['final_status'] = 'completed'
        elif result['human_review']['required']:
            result['final_status'] = 'awaiting_human_review'
        else:
            result['final_status'] = 'partially_repaired'
        
        return result
    
    def _get_sla_for_task(self, task: RepairTask) -> int:
        if task.priority == RepairPriority.CRITICAL:
            return 15
        elif task.priority == RepairPriority.HIGH:
            return 30
        else:
            return 60
    
    def get_overview(self) -> Dict[str, Any]:
        return {
            'auto_repair_stats': self.auto_engine.get_stats(),
            'human_review_queues': self.human_manager.get_queue_stats()
        }

dual_channel_manager = DualChannelRepairManager()
