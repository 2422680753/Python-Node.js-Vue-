const Queue = require('bull');
const config = require('../config');
const { redisClient } = require('../config/redis');
const Message = require('../models/Message');
const Conversation = require('../models/Conversation');
const pythonService = require('./pythonService');
const { maskSensitiveInfo } = require('../utils/sensitiveMask');
const { generateMessageId, generateConversationId } = require('../utils/helpers');

const messageQueue = new Queue('message-processing', config.redis.url);

class MessageService {
  constructor() {
    this.setupQueueProcessors();
  }

  setupQueueProcessors() {
    messageQueue.process(config.messageQueue.concurrency, async (job) => {
      const { conversationId, messageId, content, language, sender } = job.data;
      
      try {
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
              isEscalated: escalationCheck.shouldEscalate
            }
          },
          { new: true }
        );
        
        if (escalationCheck.shouldEscalate) {
          await Conversation.findOneAndUpdate(
            { conversationId },
            { $set: { status: 'escalated' } }
          );
        }
        
        const botMessageId = generateMessageId();
        const botMessage = new Message({
          messageId: botMessageId,
          conversationId,
          sender: 'bot',
          content: responseContent,
          language: detectedLanguage,
          isEscalated: escalationCheck.shouldEscalate,
          escalatedTo: escalationCheck.shouldEscalate ? 'agent' : null,
          metadata: {
            intent: intentResult.intent,
            confidence: intentResult.confidence,
            escalationReason: escalationCheck.reason
          }
        });
        
        await botMessage.save();
        
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
          escalated: escalationCheck.shouldEscalate
        };
        
      } catch (error) {
        console.error('Message processing error:', error);
        throw error;
      }
    });
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

  async processMessage(conversationId, content, language = 'en') {
    const messageId = generateMessageId();
    
    const message = new Message({
      messageId,
      conversationId,
      sender: 'user',
      content,
      language
    });
    
    await message.save();
    
    const job = await messageQueue.add({
      conversationId,
      messageId,
      content,
      language,
      sender: 'user'
    }, {
      attempts: config.messageQueue.attempts,
      backoff: {
        type: 'exponential',
        delay: 1000
      }
    });
    
    return {
      messageId,
      jobId: job.id,
      status: 'queued'
    };
  }

  async getConversationMessages(conversationId, limit = 50, offset = 0) {
    return Message.find({ conversationId })
      .sort({ timestamp: 1 })
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
      .sort({ timestamp: -1 })
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
    
    return conversation.toObject();
  }
}

module.exports = new MessageService();
