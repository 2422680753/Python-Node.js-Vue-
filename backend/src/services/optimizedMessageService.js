const Queue = require('bull');
const config = require('../config');
const { redisClient } = require('../config/redis');
const Message = require('../models/Message');
const Conversation = require('../models/Conversation');
const pythonService = require('./pythonService');
const contextManager = require('./conversationContextManager');
const { maskSensitiveInfo } = require('../utils/sensitiveMask');
const { 
  generateMessageId, 
  generateConversationId,
  generateSequenceNumber,
  extractTimestampFromId
} = require('../utils/helpers');

const messageQueue = new Queue('message-processing', config.redis.url);
const sequentialQueue = new Queue('sequential-message-processing', config.redis.url);

class OptimizedMessageService {
  constructor() {
    this.setupQueueProcessors();
    this.io = null;
  }

  setIO(ioInstance) {
    this.io = ioInstance;
  }

  setupQueueProcessors() {
    messageQueue.process(config.messageQueue.concurrency, async (job) => {
      const { conversationId, messageId, content, language, sender, sequenceNumber } = job.data;
      return this.processMessageJob(conversationId, messageId, content, language, sender, sequenceNumber);
    });

    sequentialQueue.process(1, async (job) => {
      const { conversationId, messageIds } = job.data;
      return this.processSequentialBatch(conversationId, messageIds);
    });

    messageQueue.on('completed', (job, result) => {
      if (result && result.escalated && this.io) {
        this.io.to(job.data.conversationId).emit('conversation-escalated', {
          conversationId: job.data.conversationId,
          reason: result.escalationReason || 'Unknown reason'
        });
      }
    });

    messageQueue.on('failed', (job, error) => {
      console.error(`Job ${job.id} failed:`, error);
    });
  }

  async processMessageJob(conversationId, messageId, content, language, sender, sequenceNumber) {
    try {
      const lockAcquired = await contextManager.acquireProcessingLock(conversationId);
      
      if (!lockAcquired) {
        const context = await contextManager.getContext(conversationId);
        const expectedSequence = context.sequenceNumber + 1;
        
        if (sequenceNumber > expectedSequence) {
          await contextManager.addPendingMessage(conversationId, {
            messageId,
            content,
            language,
            sender,
            sequenceNumber
          });
          
          return {
            success: true,
            held: true,
            messageId,
            sequenceNumber,
            expectedSequence
          };
        }
      }

      try {
        const sequenceCheck = await contextManager.checkAndRepairSequence(
          conversationId, 
          sequenceNumber, 
          messageId
        );

        if (sequenceCheck.action === 'duplicate') {
          console.warn(`Duplicate message detected: ${messageId}`);
          return {
            success: true,
            duplicate: true,
            messageId
          };
        }

        const result = await this.processSingleMessage(
          conversationId, 
          messageId, 
          content, 
          language, 
          sender,
          sequenceNumber
        );

        const pendingResult = await contextManager.tryProcessPending(conversationId);
        
        if (pendingResult.messagesToProcess.length > 0) {
          await sequentialQueue.add({
            conversationId,
            messageIds: pendingResult.messagesToProcess.map(m => m.messageId)
          }, {
            priority: 1
          });
        }

        return result;

      } finally {
        await contextManager.releaseProcessingLock(conversationId);
      }

    } catch (error) {
      console.error('Message processing error:', error);
      throw error;
    }
  }

  async processSingleMessage(conversationId, messageId, content, language, sender, sequenceNumber) {
    const maskedResult = maskSensitiveInfo(content);
    
    const langResult = await pythonService.detectLanguage(maskedResult.maskedText);
    const detectedLanguage = langResult.language || language;
    
    const intentResult = await pythonService.analyzeIntent(
      maskedResult.maskedText,
      detectedLanguage
    );
    
    const escalationCheck = await pythonService.shouldEscalate(
      intentResult.intent,
      intentResult.confidence
    );
    
    let responseContent = '';
    if (escalationCheck.shouldEscalate) {
      responseContent = this.getEscalationMessage(detectedLanguage);
    } else {
      const responseResult = await pythonService.generateResponse(
        maskedResult.maskedText,
        {},
        detectedLanguage
      );
      responseContent = responseResult.response;
    }
    
    const userMessage = await Message.findOneAndUpdate(
      { messageId },
      {
        $set: {
          content: maskedResult.maskedText,
          originalContent: content,
          language: detectedLanguage,
          intent: intentResult.intent,
          confidence: intentResult.confidence,
          entities: intentResult.entities,
          isSensitive: maskedResult.isSensitive,
          sensitiveInfo: maskedResult.sensitiveTypes,
          isEscalated: escalationCheck.shouldEscalate,
          sequenceNumber,
          isCodeSwitching: intentResult.isCodeSwitching,
          languageDistribution: intentResult.languageDistribution
        }
      },
      { new: true }
    );
    
    if (escalationCheck.shouldEscalate) {
      await Conversation.findOneAndUpdate(
        { conversationId },
        { $set: { status: 'escalated' } }
      );
      await contextManager.updateContext(conversationId, { isEscalated: true });
    }
    
    const botMessageId = generateMessageId();
    const botSequenceNumber = sequenceNumber + 0.5;
    
    const botMessage = new Message({
      messageId: botMessageId,
      conversationId,
      sender: 'bot',
      content: responseContent,
      language: detectedLanguage,
      isEscalated: escalationCheck.shouldEscalate,
      escalatedTo: escalationCheck.shouldEscalate ? 'agent' : null,
      sequenceNumber: botSequenceNumber,
      metadata: {
        intent: intentResult.intent,
        confidence: intentResult.confidence,
        escalationReason: escalationCheck.reason,
        isCodeSwitching: intentResult.isCodeSwitching
      }
    });
    
    await botMessage.save();
    
    await contextManager.updateContext(conversationId, {
      lastMessageId: messageId,
      lastMessageTime: Date.now(),
      intent: intentResult.intent,
      entities: intentResult.entities,
      languageDistribution: intentResult.languageDistribution,
      contextWindowEntry: {
        messageId,
        role: sender,
        intent: intentResult.intent,
        language: detectedLanguage,
        timestamp: Date.now()
      }
    });
    
    await Conversation.findOneAndUpdate(
      { conversationId },
      {
        $inc: { messageCount: 2 },
        $set: { lastMessageTime: new Date() },
        $addToSet: { intents: intentResult.intent }
      }
    );
    
    return {
      success: true,
      userMessage: userMessage.toObject(),
      botMessage: botMessage.toObject(),
      escalated: escalationCheck.shouldEscalate,
      escalationReason: escalationCheck.reason,
      sequenceNumber,
      isCodeSwitching: intentResult.isCodeSwitching
    };
  }

  async processSequentialBatch(conversationId, messageIds) {
    const results = [];
    
    for (const messageId of messageIds) {
      const message = await Message.findOne({ messageId }).lean();
      
      if (message) {
        const result = await this.processMessageJob(
          conversationId,
          messageId,
          message.content,
          message.language,
          message.sender,
          message.sequenceNumber
        );
        results.push(result);
      }
    }
    
    return {
      success: true,
      conversationId,
      processedCount: results.length,
      results
    };
  }

  async processMessage(conversationId, content, language = 'en') {
    await contextManager.initializeConversation(conversationId);
    
    const sequenceNumber = await contextManager.incrementSequence(conversationId);
    const messageId = generateMessageId(conversationId);
    
    const message = new Message({
      messageId,
      conversationId,
      sender: 'user',
      content,
      language,
      sequenceNumber,
      status: 'queued',
      queuedAt: new Date()
    });
    
    await message.save();
    
    const job = await messageQueue.add({
      conversationId,
      messageId,
      content,
      language,
      sender: 'user',
      sequenceNumber
    }, {
      attempts: config.messageQueue.attempts,
      backoff: {
        type: 'exponential',
        delay: 1000
      },
      priority: 5
    });
    
    return {
      messageId,
      sequenceNumber,
      jobId: job.id,
      status: 'queued'
    };
  }

  async getConversationContext(conversationId) {
    return contextManager.getContextSummary(conversationId);
  }

  async repairConversationSequence(conversationId) {
    const messages = await Message.find({ conversationId })
      .sort({ timestamp: 1 })
      .lean();
    
    let expectedSequence = 1;
    const repairs = [];
    
    for (const msg of messages) {
      if (!msg.sequenceNumber || msg.sequenceNumber !== expectedSequence) {
        await Message.findOneAndUpdate(
          { messageId: msg.messageId },
          { $set: { sequenceNumber: expectedSequence } }
        );
        repairs.push({
          messageId: msg.messageId,
          oldSequence: msg.sequenceNumber,
          newSequence: expectedSequence
        });
      }
      expectedSequence++;
    }
    
    await contextManager.updateContext(conversationId, {
      sequenceNumber: expectedSequence - 1
    });
    
    return {
      success: true,
      conversationId,
      repairsCount: repairs.length,
      repairs
    };
  }

  async verifyConversationCoherence(conversationId) {
    const context = await contextManager.getContext(conversationId);
    const messages = await Message.find({ conversationId })
      .sort({ sequenceNumber: 1 })
      .lean();
    
    const issues = [];
    let lastSequence = 0;
    
    for (const msg of messages) {
      if (msg.sequenceNumber !== lastSequence + 1) {
        issues.push({
          type: 'sequence_gap',
          expected: lastSequence + 1,
          actual: msg.sequenceNumber,
          messageId: msg.messageId
        });
      }
      lastSequence = msg.sequenceNumber;
    }
    
    if (context.sequenceNumber !== lastSequence) {
      issues.push({
        type: 'context_mismatch',
        contextSequence: context.sequenceNumber,
        actualSequence: lastSequence
      });
    }
    
    const pendingCount = await redisClient.zCard(
      contextManager.getPendingKey(conversationId)
    );
    
    return {
      conversationId,
      totalMessages: messages.length,
      contextSequence: context.sequenceNumber,
      actualSequence: lastSequence,
      pendingMessages: pendingCount,
      hasIssues: issues.length > 0,
      issues
    };
  }

  getEscalationMessage(language) {
    const messages = {
      zh: '您的问题需要我们专业客服人员协助，正在为您转接人工客服，请稍候...',
      en: 'Your question requires assistance from our professional customer service team. Transferring you to a human agent, please wait...',
      ja: 'お問い合わせ内容について、専門のカスタマーサービス担当者が対応いたします。人間のオペレーターにお繋ぎしております。少々お待ちください。',
      ko: '문의하신 내용에 대해 전문 상담원이 도와드려야 합니다. 인간 상담원으로 연결해 드리고 있으니 잠시만 기다려 주세요...',
      fr: 'Votre question nécessite l\'assistance de notre service clientèle professionnel. Nous vous transférons à un agent humain, veuillez patienter...',
      de: 'Ihre Frage erfordert die Unterstützung unseres professionellen Kundendienstes. Wir verbinden Sie mit einem menschlichen Agenten, bitte warten Sie...',
      es: 'Su pregunta requiere la asistencia de nuestro servicio al cliente profesional. Lo estamos transfiriendo a un agente humano, por favor espere...',
      pt: 'Sua pergunta requer a assistência do nosso serviço de atendimento ao cliente profissional. Estamos transferindo você para um agente humano, por favor aguarde...',
      ar: 'سؤالك يتطلب مساعدة من فريق خدمة العملاء المحترف لدينا. نقوم بتحويلك إلى وكيل بشري، يرجى الانتظار...',
      ru: 'Ваш вопрос требует помощи нашей профессиональной службы поддержки. Переключаем вас на человеческого агента, пожалуйста, подождите...'
    };
    return messages[language] || messages.en;
  }

  async getConversationMessages(conversationId, limit = 50, offset = 0) {
    return Message.find({ conversationId })
      .sort({ sequenceNumber: 1, timestamp: 1 })
      .skip(offset)
      .limit(limit)
      .select('-originalContent -sensitiveInfo')
      .lean();
  }

  async searchMessages(query, filters = {}) {
    const searchQuery = {
      $text: { $search: query }
    };
    
    if (filters.conversationId) {
      searchQuery.conversationId = filters.conversationId;
    }
    if (filters.language) {
      searchQuery.language = filters.language;
    }
    if (filters.sender) {
      searchQuery.sender = filters.sender;
    }
    if (filters.startDate && filters.endDate) {
      searchQuery.timestamp = {
        $gte: new Date(filters.startDate),
        $lte: new Date(filters.endDate)
      };
    }
    
    return Message.find(searchQuery)
      .sort({ sequenceNumber: -1, timestamp: -1 })
      .limit(100)
      .select('-originalContent')
      .lean();
  }

  async getActiveConversations(limit = 50) {
    return Conversation.find({ status: 'active' })
      .sort({ lastMessageTime: -1 })
      .limit(limit)
      .lean();
  }

  async getEscalatedConversations(limit = 50) {
    return Conversation.find({ status: 'escalated' })
      .sort({ lastMessageTime: -1 })
      .limit(limit)
      .lean();
  }

  async createConversation(userId, language = 'en') {
    const conversationId = generateConversationId();
    
    const conversation = new Conversation({
      conversationId,
      userId,
      userLanguage: language,
      status: 'active'
    });
    
    await conversation.save();
    
    await contextManager.initializeConversation(conversationId);
    
    return conversation.toObject();
  }
}

const optimizedMessageService = new OptimizedMessageService();

module.exports = optimizedMessageService;
