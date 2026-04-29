from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading
import time
import hashlib
from services.data_processing_pipeline import (
    ValidationLevel, ProcessingStatus, ProcessingResult
)
from services.three_layer_validator import ValidationStatus, ValidationReport
from services.dual_channel_repair import RepairStatus, InterventionType

class QualityDimension(str, Enum):
    COMPLETENESS = 'completeness'
    CORRECTNESS = 'correctness'
    CONSISTENCY = 'consistency'
    TIMELINESS = 'timeliness'
    UNIQUENESS = 'uniqueness'
    VALIDITY = 'validity'
    INTEGRITY = 'integrity'

class AlertLevel(str, Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'

class AlertType(str, Enum):
    QUALITY_DROP = 'quality_drop'
    ERROR_SPIKE = 'error_spike'
    LATENCY_THRESHOLD = 'latency_threshold'
    VALIDATION_FAILURE = 'validation_failure'
    REPAIR_FAILURE = 'repair_failure'
    HUMAN_REVIEW_BACKLOG = 'human_review_backlog'
    DATA_INCONSISTENCY = 'data_inconsistency'
    SLA_BREACH = 'sla_breach'

@dataclass
class QualityMetric:
    name: str
    dimension: QualityDimension
    value: float
    threshold: float
    target: float
    unit: str = 'percent'
    is_passing: bool = True
    trend: str = 'stable'
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityAlert:
    alert_id: str
    alert_level: AlertLevel
    alert_type: AlertType
    message: str
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    affected_records: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    parent_alert_id: Optional[str] = None
    related_alert_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DataQualitySnapshot:
    snapshot_id: str
    timestamp: datetime
    metrics: List[QualityMetric] = field(default_factory=list)
    alerts: List[QualityAlert] = field(default_factory=list)
    overall_score: float = 100.0
    passing_rate: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityRule:
    rule_id: str
    name: str
    dimension: QualityDimension
    metric_name: str
    threshold: float
    operator: str = '>='
    alert_level: AlertLevel = AlertLevel.WARNING
    description: str = ''
    enabled: bool = True
    sampling_rate: float = 1.0
    window_minutes: int = 5
    min_violations: int = 1
    auto_resolve: bool = False
    auto_resolve_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class QualityMetricCalculator:
    @staticmethod
    def calculate_completeness(
        total_records: int,
        null_count: int,
        empty_count: int = 0
    ) -> float:
        if total_records == 0:
            return 100.0
        missing = null_count + empty_count
        return ((total_records - missing) / total_records) * 100
    
    @staticmethod
    def calculate_correctness(
        total_records: int,
        validation_errors: int
    ) -> float:
        if total_records == 0:
            return 100.0
        return ((total_records - validation_errors) / total_records) * 100
    
    @staticmethod
    def calculate_consistency(
        total_records: int,
        inconsistent_records: int
    ) -> float:
        if total_records == 0:
            return 100.0
        return ((total_records - inconsistent_records) / total_records) * 100
    
    @staticmethod
    def calculate_timeliness(
        expected_time_ms: float,
        actual_time_ms: float
    ) -> float:
        if expected_time_ms <= 0:
            return 100.0
        ratio = min(actual_time_ms / expected_time_ms, 1.0)
        return max(0.0, 100.0 - (ratio * 100.0))
    
    @staticmethod
    def calculate_uniqueness(
        total_records: int,
        duplicate_count: int
    ) -> float:
        if total_records == 0:
            return 100.0
        return ((total_records - duplicate_count) / total_records) * 100
    
    @staticmethod
    def calculate_validity(
        total_records: int,
        invalid_count: int
    ) -> float:
        if total_records == 0:
            return 100.0
        return ((total_records - invalid_count) / total_records) * 100
    
    @staticmethod
    def calculate_integrity(
        total_references: int,
        broken_references: int
    ) -> float:
        if total_references == 0:
            return 100.0
        return ((total_references - broken_references) / total_references) * 100

class SlidingWindowMetrics:
    def __init__(self, window_size_minutes: int = 60):
        self.window_size = timedelta(minutes=window_size_minutes)
        self.data_points: List[tuple] = []
        self._lock = threading.Lock()
    
    def add_point(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        with self._lock:
            ts = timestamp or datetime.now()
            self.data_points.append((ts, metric_name, value))
            self._cleanup()
    
    def _cleanup(self):
        cutoff = datetime.now() - self.window_size
        self.data_points = [
            (ts, name, val) for ts, name, val in self.data_points
            if ts >= cutoff
        ]
    
    def get_metric_stats(self, metric_name: str, 
                         minutes: Optional[int] = None) -> Dict[str, float]:
        with self._lock:
            cutoff = datetime.now() - timedelta(minutes=minutes or 60)
            points = [
                val for ts, name, val in self.data_points
                if name == metric_name and ts >= cutoff
            ]
            
            if not points:
                return {'count': 0, 'avg': 0.0, 'min': 0.0, 'max': 0.0, 'latest': 0.0}
            
            return {
                'count': len(points),
                'avg': sum(points) / len(points),
                'min': min(points),
                'max': max(points),
                'latest': points[-1]
            }
    
    def get_all_metrics(self, minutes: Optional[int] = None) -> Dict[str, Dict[str, float]]:
        metric_names = set(name for _, name, _ in self.data_points)
        return {
            name: self.get_metric_stats(name, minutes)
            for name in metric_names
        }

class QualityAlertManager:
    def __init__(self):
        self.alerts: Dict[str, QualityAlert] = {}
        self._lock = threading.Lock()
        self.alert_handlers: Dict[AlertType, List[Callable]] = {}
    
    def _generate_alert_id(self) -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        import random
        random_suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
        return f'ALT-{timestamp}-{random_suffix}'
    
    def create_alert(self, 
                     alert_type: AlertType,
                     alert_level: AlertLevel,
                     message: str,
                     metric_name: Optional[str] = None,
                     current_value: Optional[float] = None,
                     threshold_value: Optional[float] = None,
                     affected_records: Optional[List[str]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> QualityAlert:
        with self._lock:
            alert_id = self._generate_alert_id()
            alert = QualityAlert(
                alert_id=alert_id,
                alert_level=alert_level,
                alert_type=alert_type,
                message=message,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=threshold_value,
                affected_records=affected_records or [],
                metadata=metadata or {}
            )
            self.alerts[alert_id] = alert
            self._trigger_handlers(alert)
            return alert
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Optional[QualityAlert]:
        with self._lock:
            if alert_id not in self.alerts:
                return None
            
            alert = self.alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now()
            return alert
    
    def resolve_alert(self, alert_id: str, resolved_by: str, 
                      resolution_notes: Optional[str] = None) -> Optional[QualityAlert]:
        with self._lock:
            if alert_id not in self.alerts:
                return None
            
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_by = resolved_by
            alert.resolved_at = datetime.now()
            alert.resolution_notes = resolution_notes
            return alert
    
    def register_handler(self, alert_type: AlertType, handler: Callable):
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        self.alert_handlers[alert_type].append(handler)
    
    def _trigger_handlers(self, alert: QualityAlert):
        if alert.alert_type in self.alert_handlers:
            for handler in self.alert_handlers[alert.alert_type]:
                try:
                    handler(alert)
                except Exception as e:
                    print(f"Alert handler error: {e}")
    
    def get_active_alerts(self) -> List[QualityAlert]:
        with self._lock:
            return [
                alert for alert in self.alerts.values()
                if not alert.resolved
            ]
    
    def get_alerts_by_level(self, level: AlertLevel) -> List[QualityAlert]:
        with self._lock:
            return [
                alert for alert in self.alerts.values()
                if alert.alert_level == level and not alert.resolved
            ]
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active = [a for a in self.alerts.values() if not a.resolved]
            
            by_level = {
                level.value: sum(1 for a in active if a.alert_level == level)
                for level in AlertLevel
            }
            
            by_type = {
                t.value: sum(1 for a in active if a.alert_type == t)
                for t in AlertType
            }
            
            return {
                'total_alerts': len(self.alerts),
                'active_alerts': len(active),
                'resolved_alerts': len(self.alerts) - len(active),
                'by_level': by_level,
                'by_type': by_type
            }

class DefaultQualityRules:
    @staticmethod
    def get_rules() -> List[QualityRule]:
        return [
            QualityRule(
                rule_id='QR-001',
                name='Minimum Completeness',
                dimension=QualityDimension.COMPLETENESS,
                metric_name='completeness',
                threshold=95.0,
                operator='>=',
                alert_level=AlertLevel.WARNING,
                description='Data completeness must be at least 95%',
                window_minutes=5
            ),
            QualityRule(
                rule_id='QR-002',
                name='Minimum Correctness',
                dimension=QualityDimension.CORRECTNESS,
                metric_name='correctness',
                threshold=90.0,
                operator='>=',
                alert_level=AlertLevel.ERROR,
                description='Data correctness must be at least 90%',
                window_minutes=5
            ),
            QualityRule(
                rule_id='QR-003',
                name='Response Time SLA',
                dimension=QualityDimension.TIMELINESS,
                metric_name='response_time_ms',
                threshold=5000.0,
                operator='<=',
                alert_level=AlertLevel.WARNING,
                description='Response time must be within 5000ms',
                window_minutes=1
            ),
            QualityRule(
                rule_id='QR-004',
                name='Error Rate Threshold',
                dimension=QualityDimension.CORRECTNESS,
                metric_name='error_rate',
                threshold=5.0,
                operator='<=',
                alert_level=AlertLevel.CRITICAL,
                description='Error rate must not exceed 5%',
                window_minutes=1,
                min_violations=3
            ),
            QualityRule(
                rule_id='QR-005',
                name='Validation Failure Spike',
                dimension=QualityDimension.VALIDITY,
                metric_name='validation_failures',
                threshold=10.0,
                operator='<=',
                alert_level=AlertLevel.ERROR,
                description='Validation failures must not spike above 10%',
                window_minutes=2
            ),
            QualityRule(
                rule_id='QR-006',
                name='Human Review Backlog',
                dimension=QualityDimension.TIMELINESS,
                metric_name='review_backlog',
                threshold=20,
                operator='<=',
                alert_level=AlertLevel.WARNING,
                description='Human review backlog must stay under 20 items',
                window_minutes=5
            ),
        ]

class DataQualityMonitor:
    def __init__(self, rules: Optional[List[QualityRule]] = None):
        self.rules = rules or DefaultQualityRules.get_rules()
        self.enabled_rules = {r.rule_id: r for r in self.rules if r.enabled}
        
        self.metrics = SlidingWindowMetrics(window_size_minutes=1440)
        self.alerts = QualityAlertManager()
        self.snapshots: List[DataQualitySnapshot] = []
        
        self._stats = {
            'total_records_processed': 0,
            'records_with_errors': 0,
            'records_with_warnings': 0,
            'auto_repairs_attempted': 0,
            'auto_repairs_successful': 0,
            'human_reviews_completed': 0,
        }
        
        self._lock = threading.Lock()
    
    def record_processing(self, 
                          result: ProcessingResult,
                          validation_report: Optional[Dict[str, Any]] = None,
                          repair_result: Optional[Dict[str, Any]] = None):
        with self._lock:
            self._stats['total_records_processed'] += 1
            
            if result.has_errors:
                self._stats['records_with_errors'] += 1
            
            if result.warnings:
                self._stats['records_with_warnings'] += 1
            
            self.metrics.add_point(
                'processing_time_ms',
                result.processing_time_ms
            )
            
            if validation_report:
                self._record_validation_metrics(validation_report)
            
            if repair_result:
                self._record_repair_metrics(repair_result)
            
            self._check_rules()
    
    def _record_validation_metrics(self, report: Dict[str, Any]):
        total_errors = report.get('total_errors', 0)
        total_warnings = report.get('total_warnings', 0)
        
        if total_errors > 0:
            error_rate = (total_errors / max(self._stats['total_records_processed'], 1)) * 100
            self.metrics.add_point('error_rate', error_rate)
        
        self.metrics.add_point(
            'validation_time_ms',
            report.get('execution_time_ms', 0)
        )
        
        format_errors = report.get('format_report', {}).get('total_errors', 0)
        logic_errors = report.get('logic_report', {}).get('total_errors', 0)
        business_errors = report.get('business_report', {}).get('total_errors', 0)
        
        self.metrics.add_point('format_errors', format_errors)
        self.metrics.add_point('logic_errors', logic_errors)
        self.metrics.add_point('business_errors', business_errors)
        
        total = format_errors + logic_errors + business_errors
        if total > 0:
            self.metrics.add_point('validation_failures', total)
    
    def _record_repair_metrics(self, result: Dict[str, Any]):
        auto_repair = result.get('auto_repair', {})
        if auto_repair.get('attempted'):
            self._stats['auto_repairs_attempted'] += 1
            if auto_repair.get('success'):
                self._stats['auto_repairs_successful'] += 1
        
        human_review = result.get('human_review', {})
        if human_review.get('required'):
            tasks_count = len(human_review.get('tasks', []))
            self.metrics.add_point('review_backlog', tasks_count)
    
    def _check_rules(self):
        current_metrics = self.metrics.get_all_metrics(minutes=5)
        
        for rule_id, rule in self.enabled_rules.items():
            if rule.metric_name not in current_metrics:
                continue
            
            stats = current_metrics[rule.metric_name]
            if stats['count'] == 0:
                continue
            
            latest_value = stats['latest']
            avg_value = stats['avg']
            
            if rule.operator == '>=':
                violation = latest_value < rule.threshold
            elif rule.operator == '<=':
                violation = latest_value > rule.threshold
            elif rule.operator == '>':
                violation = latest_value <= rule.threshold
            elif rule.operator == '<':
                violation = latest_value >= rule.threshold
            else:
                violation = False
            
            if violation:
                self._create_alert_for_rule(rule, latest_value, avg_value)
    
    def _create_alert_for_rule(self, rule: QualityRule, 
                                current_value: float, avg_value: float):
        alert_type = self._rule_to_alert_type(rule.dimension)
        
        message = (
            f"Quality rule '{rule.name}' violated. "
            f"Current value: {current_value}, Threshold: {rule.threshold} {rule.operator}"
        )
        
        self.alerts.create_alert(
            alert_type=alert_type,
            alert_level=rule.alert_level,
            message=message,
            metric_name=rule.metric_name,
            current_value=current_value,
            threshold_value=rule.threshold,
            metadata={
                'rule_id': rule.rule_id,
                'avg_value': avg_value,
                'dimension': rule.dimension.value
            }
        )
    
    def _rule_to_alert_type(self, dimension: QualityDimension) -> AlertType:
        mapping = {
            QualityDimension.COMPLETENESS: AlertType.QUALITY_DROP,
            QualityDimension.CORRECTNESS: AlertType.QUALITY_DROP,
            QualityDimension.CONSISTENCY: AlertType.DATA_INCONSISTENCY,
            QualityDimension.TIMELINESS: AlertType.LATENCY_THRESHOLD,
            QualityDimension.UNIQUENESS: AlertType.QUALITY_DROP,
            QualityDimension.VALIDITY: AlertType.VALIDATION_FAILURE,
            QualityDimension.INTEGRITY: AlertType.DATA_INCONSISTENCY,
        }
        return mapping.get(dimension, AlertType.QUALITY_DROP)
    
    def take_snapshot(self) -> DataQualitySnapshot:
        with self._lock:
            snapshot_id = self._generate_snapshot_id()
            
            all_metrics = []
            
            latest_stats = self.metrics.get_all_metrics(minutes=5)
            
            for metric_name, stats in latest_stats.items():
                if stats['count'] == 0:
                    continue
                
                dimension = self._metric_to_dimension(metric_name)
                threshold = self._get_default_threshold(metric_name)
                target = self._get_default_target(metric_name)
                
                all_metrics.append(QualityMetric(
                    name=metric_name,
                    dimension=dimension,
                    value=stats['latest'],
                    threshold=threshold,
                    target=target,
                    is_passing=self._is_passing(stats['latest'], threshold, dimension),
                    trend=self._calculate_trend(metric_name)
                ))
            
            active_alerts = self.alerts.get_active_alerts()
            
            if all_metrics:
                passing_count = sum(1 for m in all_metrics if m.is_passing)
                overall_score = (passing_count / len(all_metrics)) * 100
                passing_rate = overall_score
            else:
                overall_score = 100.0
                passing_rate = 100.0
            
            snapshot = DataQualitySnapshot(
                snapshot_id=snapshot_id,
                timestamp=datetime.now(),
                metrics=all_metrics,
                alerts=active_alerts,
                overall_score=overall_score,
                passing_rate=passing_rate,
                metadata={
                    'stats': self._stats.copy()
                }
            )
            
            self.snapshots.append(snapshot)
            if len(self.snapshots) > 100:
                self.snapshots = self.snapshots[-100:]
            
            return snapshot
    
    def _generate_snapshot_id(self) -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        import random
        random_suffix = ''.join(random.choices('0123456789', k=4))
        return f'SNAP-{timestamp}-{random_suffix}'
    
    def _metric_to_dimension(self, metric_name: str) -> QualityDimension:
        mapping = {
            'completeness': QualityDimension.COMPLETENESS,
            'correctness': QualityDimension.CORRECTNESS,
            'consistency': QualityDimension.CONSISTENCY,
            'response_time_ms': QualityDimension.TIMELINESS,
            'processing_time_ms': QualityDimension.TIMELINESS,
            'error_rate': QualityDimension.CORRECTNESS,
            'validation_failures': QualityDimension.VALIDITY,
            'format_errors': QualityDimension.VALIDITY,
            'logic_errors': QualityDimension.CONSISTENCY,
            'business_errors': QualityDimension.CORRECTNESS,
            'review_backlog': QualityDimension.TIMELINESS,
        }
        return mapping.get(metric_name, QualityDimension.CORRECTNESS)
    
    def _get_default_threshold(self, metric_name: str) -> float:
        defaults = {
            'completeness': 95.0,
            'correctness': 90.0,
            'consistency': 95.0,
            'response_time_ms': 5000.0,
            'processing_time_ms': 3000.0,
            'error_rate': 5.0,
            'validation_failures': 10.0,
            'review_backlog': 20.0,
        }
        return defaults.get(metric_name, 90.0)
    
    def _get_default_target(self, metric_name: str) -> float:
        targets = {
            'completeness': 100.0,
            'correctness': 100.0,
            'consistency': 100.0,
            'response_time_ms': 1000.0,
            'processing_time_ms': 500.0,
            'error_rate': 0.0,
            'validation_failures': 0.0,
            'review_backlog': 0.0,
        }
        return targets.get(metric_name, 100.0)
    
    def _is_passing(self, value: float, threshold: float, dimension: QualityDimension) -> bool:
        if dimension == QualityDimension.TIMELINESS:
            return value <= threshold
        return value >= threshold
    
    def _calculate_trend(self, metric_name: str) -> str:
        recent = self.metrics.get_metric_stats(metric_name, minutes=1)
        earlier = self.metrics.get_metric_stats(metric_name, minutes=5)
        
        if recent['count'] == 0 or earlier['count'] < 2:
            return 'stable'
        
        change = recent['avg'] - earlier['avg']
        if abs(change) < 0.1:
            return 'stable'
        elif change > 0:
            return 'improving'
        else:
            return 'declining'
    
    def get_quality_report(self, minutes: int = 60) -> Dict[str, Any]:
        with self._lock:
            metrics_stats = self.metrics.get_all_metrics(minutes=minutes)
            alert_stats = self.alerts.get_stats()
            
            return {
                'period_minutes': minutes,
                'generated_at': datetime.now().isoformat(),
                'overall_stats': self._stats.copy(),
                'metrics': metrics_stats,
                'alerts': alert_stats,
                'latest_snapshot': (
                    self.snapshots[-1].to_dict() if self.snapshots else None
                )
            }
    
    def get_alerts(self) -> List[QualityAlert]:
        return self.alerts.get_active_alerts()
    
    def acknowledge_alert(self, alert_id: str, user_id: str) -> Optional[QualityAlert]:
        return self.alerts.acknowledge_alert(alert_id, user_id)
    
    def resolve_alert(self, alert_id: str, user_id: str, notes: Optional[str] = None) -> Optional[QualityAlert]:
        return self.alerts.resolve_alert(alert_id, user_id, notes)

data_quality_monitor = DataQualityMonitor()
