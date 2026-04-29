const Conversation = require('../models/Conversation');
const Message = require('../models/Message');
const { generateConversationId, formatError, formatSuccess } = require('../utils/helpers');

class ConversationService {
  async createConversation(userId, language = 'en') {
    try {
      const conversationId = generateConversationId();
      
      const conversation = new Conversation({
        conversationId,
        userId,
        userLanguage: language,
        status: 'active',
        messageCount: 0,
        startTime: new Date()
      });
      
      await conversation.save();
      
      return formatSuccess(conversation.toObject(), 'Conversation created successfully');
    } catch (error) {
      return formatError('Failed to create conversation', 500, { error: error.message });
    }
  }

  async getConversation(conversationId) {
    try {
      const conversation = await Conversation.findOne({ conversationId }).lean();
      
      if (!conversation) {
        return formatError('Conversation not found', 404);
      }
      
      return formatSuccess(conversation);
    } catch (error) {
      return formatError('Failed to get conversation', 500, { error: error.message });
    }
  }

  async getUserConversations(userId, status = null, limit = 50, offset = 0) {
    try {
      const query = { userId };
      if (status) {
        query.status = status;
      }
      
      const conversations = await Conversation.find(query)
        .sort({ lastMessageTime: -1 })
        .skip(offset)
        .limit(limit)
        .lean();
      
      return formatSuccess(conversations);
    } catch (error) {
      return formatError('Failed to get conversations', 500, { error: error.message });
    }
  }

  async updateConversationStatus(conversationId, status) {
    try {
      const validStatuses = ['active', 'closed', 'escalated'];
      if (!validStatuses.includes(status)) {
        return formatError('Invalid status', 400, { validStatuses });
      }
      
      const updateData = { status };
      if (status === 'closed') {
        updateData.endTime = new Date();
      }
      
      const conversation = await Conversation.findOneAndUpdate(
        { conversationId },
        { $set: updateData },
        { new: true }
      ).lean();
      
      if (!conversation) {
        return formatError('Conversation not found', 404);
      }
      
      return formatSuccess(conversation, `Conversation status updated to ${status}`);
    } catch (error) {
      return formatError('Failed to update conversation status', 500, { error: error.message });
    }
  }

  async assignAgent(conversationId, agentId) {
    try {
      const conversation = await Conversation.findOneAndUpdate(
        { conversationId },
        { 
          $set: { 
            currentAgent: agentId,
            status: 'escalated'
          } 
        },
        { new: true }
      ).lean();
      
      if (!conversation) {
        return formatError('Conversation not found', 404);
      }
      
      return formatSuccess(conversation, `Agent ${agentId} assigned to conversation`);
    } catch (error) {
      return formatError('Failed to assign agent', 500, { error: error.message });
    }
  }

  async getActiveConversations(limit = 50) {
    try {
      const conversations = await Conversation.find({ status: 'active' })
        .sort({ lastMessageTime: -1 })
        .limit(limit)
        .lean();
      
      return formatSuccess(conversations);
    } catch (error) {
      return formatError('Failed to get active conversations', 500, { error: error.message });
    }
  }

  async getEscalatedConversations(limit = 50) {
    try {
      const conversations = await Conversation.find({ status: 'escalated' })
        .sort({ lastMessageTime: -1 })
        .limit(limit)
        .lean();
      
      return formatSuccess(conversations);
    } catch (error) {
      return formatError('Failed to get escalated conversations', 500, { error: error.message });
    }
  }

  async getConversationStats(userId = null) {
    try {
      const match = userId ? { userId } : {};
      
      const stats = await Conversation.aggregate([
        { $match: match },
        {
          $group: {
            _id: '$status',
            count: { $sum: 1 }
          }
        }
      ]);
      
      const totalMessages = await Message.countDocuments(match);
      
      return formatSuccess({
        byStatus: stats,
        totalMessages
      });
    } catch (error) {
      return formatError('Failed to get conversation stats', 500, { error: error.message });
    }
  }

  async closeConversation(conversationId, satisfactionScore = null) {
    try {
      const updateData = {
        status: 'closed',
        endTime: new Date()
      };
      
      if (satisfactionScore !== null) {
        updateData.satisfactionScore = satisfactionScore;
      }
      
      const conversation = await Conversation.findOneAndUpdate(
        { conversationId },
        { $set: updateData },
        { new: true }
      ).lean();
      
      if (!conversation) {
        return formatError('Conversation not found', 404);
      }
      
      return formatSuccess(conversation, 'Conversation closed successfully');
    } catch (error) {
      return formatError('Failed to close conversation', 500, { error: error.message });
    }
  }
}

module.exports = new ConversationService();
