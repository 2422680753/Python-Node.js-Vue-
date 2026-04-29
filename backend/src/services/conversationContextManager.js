const { redisClient } = require('../config/redis');
const { generateSequenceNumber, extractTimestampFromId, compareIds } = require('../utils/helpers');
const config = require('../config');

class ConversationContextManager {
  constructor() {
    this.contextCache = new Map();
    this.pendingMessages = new Map();
    this.processingConversations = new Set();
  }

  getContextKey(conversationId) {
    return `conv:context:${conversationId}`;
  }

  getSequenceKey(conversationId) {
    return `conv:sequence:${conversationId}`;
  }

  getPendingKey(conversationId) {
    return `conv:pending:${conversationId}`;
  }

  async initializeConversation(conversationId) {
    const contextKey = this.getContextKey(conversationId);
    const sequenceKey = this.getSequenceKey(conversationId);
    
    const exists = await redisClient.exists(contextKey);
    
    if (!exists) {
      const initialContext = {
        conversationId,
        sequenceNumber: 0,
        lastMessageId: null,
        lastMessageTime: Date.now(),
        intents: [],
        entities: {},
        languageDistribution: {},
        isEscalated: false,
        contextWindow: [],
        createdAt: Date.now()
      };
      
      await redisClient.set(contextKey, JSON.stringify(initialContext));
      await redisClient.set(sequenceKey, '0');
    }
    
    return this.getContext(conversationId);
  }

  async getContext(conversationId) {
    const contextKey = this.getContextKey(conversationId);
    const data = await redisClient.get(contextKey);
    
    if (data) {
      return JSON.parse(data);
    }
    
    return this.initializeConversation(conversationId);
  }

  async updateContext(conversationId, updates) {
    const contextKey = this.getContextKey(conversationId);
    const context = await this.getContext(conversationId);
    
    const updatedContext = {
      ...context,
      ...updates,
      updatedAt: Date.now()
    };
    
    if (updates.intent) {
      if (!updatedContext.intents.includes(updates.intent)) {
        updatedContext.intents.push(updates.intent);
      }
    }
    
    if (updates.entities) {
      updatedContext.entities = {
        ...updatedContext.entities,
        ...updates.entities
      };
    }
    
    if (updates.languageDistribution) {
      updatedContext.languageDistribution = {
        ...updatedContext.languageDistribution,
        ...updates.languageDistribution
      };
    }
    
    if (updates.contextWindowEntry) {
      updatedContext.contextWindow.push(updates.contextWindowEntry);
      if (updatedContext.contextWindow.length > 20) {
        updatedContext.contextWindow = updatedContext.contextWindow.slice(-20);
      }
    }
    
    await redisClient.set(contextKey, JSON.stringify(updatedContext));
    
    return updatedContext;
  }

  async incrementSequence(conversationId) {
    const sequenceKey = this.getSequenceKey(conversationId);
    const newSequence = await redisClient.incr(sequenceKey);
    return newSequence;
  }

  async getCurrentSequence(conversationId) {
    const sequenceKey = this.getSequenceKey(conversationId);
    const value = await redisClient.get(sequenceKey);
    return value ? parseInt(value, 10) : 0;
  }

  async addPendingMessage(conversationId, message) {
    const pendingKey = this.getPendingKey(conversationId);
    
    const messageWithMeta = {
      ...message,
      pendingSince: Date.now(),
      status: 'pending'
    };
    
    await redisClient.zAdd(pendingKey, {
      score: message.sequenceNumber || extractTimestampFromId(message.messageId) || Date.now(),
      value: JSON.stringify(messageWithMeta)
    });
    
    return messageWithMeta;
  }

  async getPendingMessages(conversationId) {
    const pendingKey = this.getPendingKey(conversationId);
    const messages = await redisClient.zRangeWithScores(pendingKey, 0, -1);
    
    return messages.map(m => ({
      ...JSON.parse(m.value),
      score: m.score
    }));
  }

  async removePendingMessage(conversationId, messageId) {
    const pendingKey = this.getPendingKey(conversationId);
    const pendingMessages = await this.getPendingMessages(conversationId);
    
    for (const msg of pendingMessages) {
      if (msg.messageId === messageId) {
        await redisClient.zRem(pendingKey, JSON.stringify(msg));
        return true;
      }
    }
    
    return false;
  }

  async checkAndRepairSequence(conversationId, messageSequence, messageId) {
    const context = await this.getContext(conversationId);
    const expectedSequence = context.sequenceNumber + 1;
    
    if (messageSequence === expectedSequence) {
      await this.updateContext(conversationId, {
        sequenceNumber: messageSequence,
        lastMessageId: messageId
      });
      return { isOrderly: true, expectedSequence };
    }
    
    if (messageSequence > expectedSequence) {
      return { 
        isOrderly: false, 
        expectedSequence,
        action: 'hold'
      };
    }
    
    if (messageSequence < expectedSequence) {
      return { 
        isOrderly: false, 
        expectedSequence,
        action: 'duplicate'
      };
    }
    
    return { isOrderly: false, expectedSequence };
  }

  async tryProcessPending(conversationId) {
    const context = await this.getContext(conversationId);
    let expectedSequence = context.sequenceNumber + 1;
    
    const pendingMessages = await this.getPendingMessages(conversationId);
    const messagesToProcess = [];
    
    pendingMessages.sort((a, b) => a.sequenceNumber - b.sequenceNumber);
    
    for (const msg of pendingMessages) {
      if (msg.sequenceNumber === expectedSequence) {
        messagesToProcess.push(msg);
        expectedSequence++;
      } else if (msg.sequenceNumber > expectedSequence) {
        break;
      }
    }
    
    return {
      messagesToProcess,
      nextExpectedSequence: expectedSequence
    };
  }

  async acquireProcessingLock(conversationId) {
    const lockKey = `lock:processing:${conversationId}`;
    const result = await redisClient.set(
      lockKey,
      '1',
      {
        EX: 30,
        NX: true
      }
    );
    
    return result === 'OK';
  }

  async releaseProcessingLock(conversationId) {
    const lockKey = `lock:processing:${conversationId}`;
    await redisClient.del(lockKey);
  }

  async clearContext(conversationId) {
    const contextKey = this.getContextKey(conversationId);
    const sequenceKey = this.getSequenceKey(conversationId);
    const pendingKey = this.getPendingKey(conversationId);
    
    await redisClient.del(contextKey);
    await redisClient.del(sequenceKey);
    await redisClient.del(pendingKey);
    
    this.contextCache.delete(conversationId);
    this.pendingMessages.delete(conversationId);
    this.processingConversations.delete(conversationId);
  }

  async getContextSummary(conversationId) {
    const context = await this.getContext(conversationId);
    const pendingCount = await redisClient.zCard(this.getPendingKey(conversationId));
    
    return {
      conversationId,
      sequenceNumber: context.sequenceNumber,
      lastMessageId: context.lastMessageId,
      intents: context.intents,
      intentCount: context.intents.length,
      isEscalated: context.isEscalated,
      pendingMessagesCount: pendingCount,
      contextWindowSize: context.contextWindow?.length || 0
    };
  }
}

module.exports = new ConversationContextManager();
