from flask import Blueprint, request, jsonify
from services.language_detector import detect_language
from services.multilingual_detector import multilingual_detector, CodeSwitchAnalysis
from services.intent_classifier import intent_classifier
from services.bilingual_intent_classifier import bilingual_intent_classifier
from services.response_generator import translate_text, generate_response
from services.knowledge_base import get_knowledge_base, should_escalate_intent
from services.structured_parser import structured_parser, FormatDetector, DataFormat
from services.three_layer_validator import three_layer_validator, ValidationLevel, ValidationStatus
from services.dual_channel_repair import dual_channel_manager, RepairStatus, InterventionType
from services.data_quality_monitor import data_quality_monitor, QualityDimension, AlertLevel
from services.enhanced_data_pipeline import enhanced_pipeline, ProcessingContext
from config import config

api_bp = Blueprint('api', __name__)

@api_bp.route('/detect-language', methods=['POST'])
def api_detect_language():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    result = detect_language(text)
    
    return jsonify({
        'success': True,
        'data': result
    })

@api_bp.route('/detect-multilingual', methods=['POST'])
def api_detect_multilingual():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    check_code_switching = data.get('checkCodeSwitching', True)
    
    analysis = multilingual_detector.analyze_multilingual(text, check_code_switching)
    
    convert_analysis = {
        'hasCodeSwitching': analysis.has_code_switching,
        'detectedLanguages': analysis.detected_languages,
        'languageDistribution': analysis.language_distribution,
        'segments': [
            {
                'language': seg.language,
                'text': seg.text,
                'startIndex': seg.start_index,
                'endIndex': seg.end_index,
                'confidence': seg.confidence
            }
            for seg in analysis.segments
        ],
        'dominantLanguage': analysis.dominant_language,
        'dominantIntentLanguage': analysis.dominant_intent_language,
        'isBilingual': analysis.is_bilingual,
        'switchPoints': analysis.switch_points,
        'languageSequence': analysis.language_sequence
    }
    
    return jsonify({
        'success': True,
        'data': convert_analysis
    })

@api_bp.route('/translate', methods=['POST'])
def api_translate():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    target_lang = data.get('targetLang', 'en')
    source_lang = data.get('sourceLang', None)
    
    if target_lang not in config.LANGUAGES:
        return jsonify({
            'success': False,
            'error': f'Invalid target language. Supported: {config.LANGUAGES}'
        }), 400
    
    result = translate_text(text, target_lang, source_lang)
    
    return jsonify({
        'success': True,
        'data': result
    })

@api_bp.route('/intent', methods=['POST'])
def api_intent():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    language = data.get('language', 'en')
    use_bilingual = data.get('useBilingual', True)
    context_intents = data.get('contextIntents', None)
    
    if use_bilingual:
        result = bilingual_intent_classifier.classify_bilingual_intent(
            text, language, context_intents
        )
    else:
        result = intent_classifier.classify(text, language)
    
    should_escalate = should_escalate_intent(result.get('intent', 'unknown')) or \
                       result.get('confidence', 0) < config.ESCALATION_THRESHOLD
    
    return jsonify({
        'success': True,
        'data': {
            **result,
            'shouldEscalate': should_escalate,
            'escalationThreshold': config.ESCALATION_THRESHOLD
        }
    })

@api_bp.route('/entities', methods=['POST'])
def api_entities():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    language = data.get('language', 'en')
    
    result = intent_classifier.classify(text, language)
    
    return jsonify({
        'success': True,
        'data': {
            'entities': result.get('entities', []),
            'text': text,
            'language': language
        }
    })

@api_bp.route('/generate-response', methods=['POST'])
def api_generate_response():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    context = data.get('context', {})
    language = data.get('language', 'en')
    
    result = generate_response(text, context, language)
    
    return jsonify({
        'success': True,
        'data': result
    })

@api_bp.route('/intents', methods=['GET'])
def api_list_intents():
    intents = intent_classifier.get_all_intents()
    
    return jsonify({
        'success': True,
        'data': {
            'intents': intents,
            'total': len(intents),
            'languages': config.LANGUAGES
        }
    })

@api_bp.route('/languages', methods=['GET'])
def api_list_languages():
    languages_info = [
        {'code': 'zh', 'name': '中文', 'englishName': 'Chinese'},
        {'code': 'en', 'name': 'English', 'englishName': 'English'},
        {'code': 'ja', 'name': '日本語', 'englishName': 'Japanese'},
        {'code': 'ko', 'name': '한국어', 'englishName': 'Korean'},
        {'code': 'fr', 'name': 'Français', 'englishName': 'French'},
        {'code': 'de', 'name': 'Deutsch', 'englishName': 'German'},
        {'code': 'es', 'name': 'Español', 'englishName': 'Spanish'},
        {'code': 'pt', 'name': 'Português', 'englishName': 'Portuguese'},
        {'code': 'ar', 'name': 'العربية', 'englishName': 'Arabic'},
        {'code': 'ru', 'name': 'Русский', 'englishName': 'Russian'}
    ]
    
    return jsonify({
        'success': True,
        'data': {
            'languages': languages_info,
            'total': len(languages_info)
        }
    })

@api_bp.route('/analyze', methods=['POST'])
def api_full_analyze():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'Text parameter is required'
        }), 400
    
    text = data.get('text', '')
    target_lang = data.get('targetLang', 'en')
    context = data.get('context', {})
    use_bilingual = data.get('useBilingual', True)
    context_intents = data.get('contextIntents', None)
    
    multilingual_analysis = multilingual_detector.analyze_multilingual(text, True)
    
    language_result = detect_language(text)
    source_lang = language_result.get('language', 'en')
    
    if use_bilingual:
        intent_result = bilingual_intent_classifier.classify_bilingual_intent(
            text, source_lang, context_intents
        )
    else:
        intent_result = intent_classifier.classify(text, source_lang)
    
    translation_result = translate_text(text, target_lang, source_lang)
    
    response_result = generate_response(text, context, source_lang)
    
    return jsonify({
        'success': True,
        'data': {
            'language': language_result,
            'multilingualAnalysis': {
                'hasCodeSwitching': multilingual_analysis.has_code_switching,
                'detectedLanguages': multilingual_analysis.detected_languages,
                'languageDistribution': multilingual_analysis.language_distribution,
                'dominantLanguage': multilingual_analysis.dominant_language,
                'dominantIntentLanguage': multilingual_analysis.dominant_intent_language,
                'isBilingual': multilingual_analysis.is_bilingual,
                'segments': [
                    {
                        'language': seg.language,
                        'text': seg.text,
                        'confidence': seg.confidence
                    }
                    for seg in multilingual_analysis.segments
                ]
            },
            'intent': intent_result,
            'translation': translation_result,
            'response': response_result
        }
    })

@api_bp.route('/parse', methods=['POST'])
def api_parse():
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({
            'success': False,
            'error': 'Content parameter is required'
        }), 400
    
    content = data.get('content', '')
    target_format = data.get('targetFormat', None)
    
    if target_format:
        try:
            format_enum = DataFormat(target_format.lower())
            parse_result = structured_parser.parse_as(content, format_enum)
        except ValueError:
            parse_result = structured_parser.auto_parse(content)
    else:
        parse_result = structured_parser.auto_parse(content)
    
    result = {
        'success': parse_result.success,
        'format': parse_result.format.value,
        'data': parse_result.data,
        'raw_length': parse_result.raw_length,
        'parse_time_ms': parse_result.parse_time_ms,
        'warnings': parse_result.warnings,
        'metadata': parse_result.metadata
    }
    
    if not parse_result.success:
        result['error_message'] = parse_result.error_message
    
    return jsonify({
        'success': parse_result.success,
        'data': result
    })

@api_bp.route('/detect-format', methods=['POST'])
def api_detect_format():
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({
            'success': False,
            'error': 'Content parameter is required'
        }), 400
    
    content = data.get('content', '')
    
    format_scores = FormatDetector.detect(content)
    best_format, confidence = FormatDetector.detect_with_confidence(content)
    
    return jsonify({
        'success': True,
        'data': {
            'best_format': best_format.value,
            'confidence': confidence,
            'all_scores': {
                k.value: v for k, v in format_scores.items()
            }
        }
    })

@api_bp.route('/validate', methods=['POST'])
def api_validate():
    data = request.get_json()
    
    if not data or 'data' not in data:
        return jsonify({
            'success': False,
            'error': 'Data parameter is required'
        }), 400
    
    input_data = data.get('data', {})
    level = data.get('level', 'all')
    
    context = ProcessingContext(
        conversation_id=data.get('conversationId'),
        user_id=data.get('userId'),
        message_id=data.get('messageId'),
        sequence_number=data.get('sequenceNumber'),
        language=data.get('language', 'en'),
        history=data.get('history', []),
        business_rules=data.get('businessRules', {})
    )
    
    if level == 'format':
        report = three_layer_validator.validate_at_level(
            input_data, ValidationLevel.FORMAT, context
        )
        result = report.to_dict()
    elif level == 'logic':
        report = three_layer_validator.validate_at_level(
            input_data, ValidationLevel.LOGIC, context
        )
        result = report.to_dict()
    elif level == 'business':
        report = three_layer_validator.validate_at_level(
            input_data, ValidationLevel.BUSINESS, context
        )
        result = report.to_dict()
    else:
        result = three_layer_validator.validate_all(input_data, context)
    
    return jsonify({
        'success': True,
        'level': level,
        'data': result
    })

@api_bp.route('/auto-repair', methods=['POST'])
def api_auto_repair():
    data = request.get_json()
    
    if not data or 'data' not in data:
        return jsonify({
            'success': False,
            'error': 'Data parameter is required'
        }), 400
    
    input_data = data.get('data', {})
    errors = data.get('errors', [])
    
    context = ProcessingContext(
        conversation_id=data.get('conversationId'),
        user_id=data.get('userId'),
        message_id=data.get('messageId'),
        sequence_number=data.get('sequenceNumber'),
        language=data.get('language', 'en')
    )
    
    result = dual_channel_manager.process_errors(input_data, errors, context)
    
    return jsonify({
        'success': True,
        'data': result
    })

@api_bp.route('/review-tasks', methods=['GET'])
def api_get_review_tasks():
    agent_id = request.args.get('agentId')
    limit = int(request.args.get('limit', 10))
    
    tasks = dual_channel_manager.human_manager.get_tasks_for_agent(agent_id, limit)
    
    tasks_dict = [
        {
            'task_id': t.task_id,
            'data_id': t.data_id,
            'error_code': t.error_code,
            'error_message': t.error_message,
            'field': t.field,
            'original_value': t.original_value,
            'suggested_repair': t.suggested_repair,
            'priority': t.priority.value,
            'status': t.status.value,
            'intervention_type': t.intervention_type.value,
            'requires_approval': t.requires_approval,
            'approved': t.approved,
            'rejected': t.rejected,
            'approver_id': t.approver_id,
            'rejection_reason': t.rejection_reason,
            'created_at': t.created_at.isoformat() if t.created_at else None,
            'started_at': t.started_at.isoformat() if t.started_at else None,
            'completed_at': t.completed_at.isoformat() if t.completed_at else None,
            'repair_result': t.repair_result,
            'execution_time_ms': t.execution_time_ms,
            'retry_count': t.retry_count
        }
        for t in tasks
    ]
    
    return jsonify({
        'success': True,
        'data': {
            'tasks': tasks_dict,
            'total': len(tasks_dict)
        }
    })

@api_bp.route('/review-tasks/<task_id>/claim', methods=['POST'])
def api_claim_task(task_id):
    data = request.get_json() or {}
    agent_id = data.get('agentId') or request.args.get('agentId')
    
    if not agent_id:
        return jsonify({
            'success': False,
            'error': 'Agent ID is required'
        }), 400
    
    task = dual_channel_manager.human_manager.claim_task(task_id, agent_id)
    
    if not task:
        return jsonify({
            'success': False,
            'error': 'Task not found or already claimed'
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'task_id': task.task_id,
            'status': task.status.value,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'approver_id': task.approver_id
        }
    })

@api_bp.route('/review-tasks/<task_id>/submit', methods=['POST'])
def api_submit_review(task_id):
    data = request.get_json()
    
    if not data or 'agentId' not in data or 'approved' not in data:
        return jsonify({
            'success': False,
            'error': 'agentId and approved parameters are required'
        }), 400
    
    agent_id = data.get('agentId')
    approved = data.get('approved')
    corrected_data = data.get('correctedData')
    rejection_reason = data.get('rejectionReason')
    comment = data.get('comment')
    
    task = dual_channel_manager.human_manager.submit_review(
        task_id=task_id,
        agent_id=agent_id,
        approved=approved,
        corrected_data=corrected_data,
        rejection_reason=rejection_reason,
        comment=comment
    )
    
    if not task:
        return jsonify({
            'success': False,
            'error': 'Task not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'task_id': task.task_id,
            'status': task.status.value,
            'approved': task.approved,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        }
    })

@api_bp.route('/quality/report', methods=['GET'])
def api_quality_report():
    minutes = int(request.args.get('minutes', 60))
    
    report = data_quality_monitor.get_quality_report(minutes=minutes)
    
    return jsonify({
        'success': True,
        'data': report
    })

@api_bp.route('/quality/snapshot', methods=['POST'])
def api_take_snapshot():
    snapshot = data_quality_monitor.take_snapshot()
    
    return jsonify({
        'success': True,
        'data': {
            'snapshot_id': snapshot.snapshot_id,
            'timestamp': snapshot.timestamp.isoformat(),
            'overall_score': snapshot.overall_score,
            'passing_rate': snapshot.passing_rate,
            'metric_count': len(snapshot.metrics),
            'active_alerts': len(snapshot.alerts)
        }
    })

@api_bp.route('/quality/alerts', methods=['GET'])
def api_get_alerts():
    level = request.args.get('level')
    
    if level:
        try:
            alert_level = AlertLevel(level.lower())
            alerts = data_quality_monitor.alerts.get_alerts_by_level(alert_level)
        except ValueError:
            alerts = data_quality_monitor.get_alerts()
    else:
        alerts = data_quality_monitor.get_alerts()
    
    alerts_dict = [
        {
            'alert_id': a.alert_id,
            'alert_level': a.alert_level.value,
            'alert_type': a.alert_type.value,
            'message': a.message,
            'metric_name': a.metric_name,
            'current_value': a.current_value,
            'threshold_value': a.threshold_value,
            'affected_records': a.affected_records,
            'created_at': a.created_at.isoformat() if a.created_at else None,
            'acknowledged': a.acknowledged,
            'acknowledged_by': a.acknowledged_by,
            'acknowledged_at': a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            'resolved': a.resolved,
            'resolved_by': a.resolved_by,
            'resolved_at': a.resolved_at.isoformat() if a.resolved_at else None,
            'resolution_notes': a.resolution_notes
        }
        for a in alerts
    ]
    
    return jsonify({
        'success': True,
        'data': {
            'alerts': alerts_dict,
            'total': len(alerts_dict)
        }
    })

@api_bp.route('/quality/alerts/<alert_id>/acknowledge', methods=['POST'])
def api_acknowledge_alert(alert_id):
    data = request.get_json() or {}
    user_id = data.get('userId') or request.args.get('userId')
    
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User ID is required'
        }), 400
    
    alert = data_quality_monitor.acknowledge_alert(alert_id, user_id)
    
    if not alert:
        return jsonify({
            'success': False,
            'error': 'Alert not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'alert_id': alert.alert_id,
            'acknowledged': alert.acknowledged,
            'acknowledged_by': alert.acknowledged_by,
            'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
        }
    })

@api_bp.route('/quality/alerts/<alert_id>/resolve', methods=['POST'])
def api_resolve_alert(alert_id):
    data = request.get_json() or {}
    user_id = data.get('userId') or request.args.get('userId')
    notes = data.get('notes')
    
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User ID is required'
        }), 400
    
    alert = data_quality_monitor.resolve_alert(alert_id, user_id, notes)
    
    if not alert:
        return jsonify({
            'success': False,
            'error': 'Alert not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'alert_id': alert.alert_id,
            'resolved': alert.resolved,
            'resolved_by': alert.resolved_by,
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
            'resolution_notes': alert.resolution_notes
        }
    })

@api_bp.route('/enhanced-process', methods=['POST'])
def api_enhanced_process():
    data = request.get_json()
    
    if not data or 'rawData' not in data:
        return jsonify({
            'success': False,
            'error': 'rawData parameter is required'
        }), 400
    
    raw_data = data.get('rawData')
    
    context = ProcessingContext(
        conversation_id=data.get('conversationId'),
        user_id=data.get('userId'),
        message_id=data.get('messageId'),
        sequence_number=data.get('sequenceNumber'),
        language=data.get('language', 'en'),
        history=data.get('history', []),
        business_rules=data.get('businessRules', {})
    )
    
    config_overrides = data.get('config', {})
    
    result = enhanced_pipeline.process(
        raw_data=raw_data,
        context=context,
        config_overrides=config_overrides
    )
    
    return jsonify({
        'success': result.success,
        'data': result.to_dict()
    })

@api_bp.route('/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'healthy',
        'service': 'nlp-translation-service',
        'languages': config.LANGUAGES,
        'intentThreshold': config.INTENT_THRESHOLD,
        'escalationThreshold': config.ESCALATION_THRESHOLD,
        'features': {
            'codeSwitchingDetection': True,
            'bilingualIntentClassification': True,
            'multilingualAnalysis': True,
            'structuredParsing': True,
            'threeLayerValidation': True,
            'dualChannelRepair': True,
            'dataQualityMonitoring': True,
            'enhancedProcessing': True
        },
        'endpoints': {
            'structured_parsing': ['/parse', '/detect-format'],
            'validation': ['/validate'],
            'repair': ['/auto-repair', '/review-tasks'],
            'quality_monitoring': ['/quality/report', '/quality/snapshot', '/quality/alerts'],
            'enhanced': ['/enhanced-process']
        }
    })
