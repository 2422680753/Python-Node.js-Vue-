const express = require('express');
const messageService = require('../services/messageService');
const conversationService = require('../services/conversationService');
const { formatError, formatSuccess, generateUserId } = require('../utils/helpers');
const config = require('../config');

const router = express.Router();

router.post('/conversations', async (req, res) => {
  try {
    const { userId, language } = req.body;
    const userIdentifier = userId || generateUserId();
    const result = await conversationService.createConversation(
      userIdentifier,
      language || 'en'
    );
    res.status(result.success ? 200 : 400).json(result);
  } catch (error) {
    res.status(500).json(formatError('Failed to create conversation', 500, { error: error.message }));
  }
});

router.get('/conversations/:conversationId', async (req, res) => {
  try {
    const { conversationId } = req.params;
    const result = await conversationService.getConversation(conversationId);
    res.status(result.success ? 200 : 404).json(result);
  } catch (error) {
    res.status(500).json(formatError('Failed to get conversation', 500, { error: error.message }));
  }
});

router.get('/conversations/:conversationId/messages', async (req, res) => {
  try {
    const { conversationId } = req.params;
    const { limit = 50, offset = 0 } = req.query;
    const messages = await messageService.getConversationMessages(
      conversationId,
      parseInt(limit),
      parseInt(offset)
    );
    res.json(formatSuccess(messages));
  } catch (error) {
    res.status(500).json(formatError('Failed to get messages', 500, { error: error.message }));
  }
});

router.post('/conversations/:conversationId/messages', async (req, res) => {
  try {
    const { conversationId } = req.params;
    const { content, language } = req.body;
    
    if (!content || content.trim().length === 0) {
      return res.status(400).json(formatError('Message content is required', 400));
    }
    
    const result = await messageService.processMessage(
      conversationId,
      content,
      language || 'en'
    );
    
    res.json(formatSuccess(result, 'Message queued for processing'));
  } catch (error) {
    res.status(500).json(formatError('Failed to send message', 500, { error: error.message }));
  }
});

router.post('/conversations/:conversationId/close', async (req, res) => {
  try {
    const { conversationId } = req.params;
    const { satisfactionScore } = req.body;
    
    const result = await conversationService.closeConversation(
      conversationId,
      satisfactionScore
    );
    
    res.status(result.success ? 200 : 404).json(result);
  } catch (error) {
    res.status(500).json(formatError('Failed to close conversation', 500, { error: error.message }));
  }
});

router.get('/conversations/status/active', async (req, res) => {
  try {
    const result = await conversationService.getActiveConversations();
    res.json(result);
  } catch (error) {
    res.status(500).json(formatError('Failed to get active conversations', 500, { error: error.message }));
  }
});

router.get('/conversations/status/escalated', async (req, res) => {
  try {
    const result = await conversationService.getEscalatedConversations();
    res.json(result);
  } catch (error) {
    res.status(500).json(formatError('Failed to get escalated conversations', 500, { error: error.message }));
  }
});

router.post('/conversations/:conversationId/assign-agent', async (req, res) => {
  try {
    const { conversationId } = req.params;
    const { agentId } = req.body;
    
    if (!agentId) {
      return res.status(400).json(formatError('Agent ID is required', 400));
    }
    
    const result = await conversationService.assignAgent(conversationId, agentId);
    res.status(result.success ? 200 : 404).json(result);
  } catch (error) {
    res.status(500).json(formatError('Failed to assign agent', 500, { error: error.message }));
  }
});

router.get('/search/messages', async (req, res) => {
  try {
    const { query, conversationId, language, sender, startDate, endDate } = req.query;
    
    if (!query || query.trim().length === 0) {
      return res.status(400).json(formatError('Search query is required', 400));
    }
    
    const filters = {};
    if (conversationId) filters.conversationId = conversationId;
    if (language) filters.language = language;
    if (sender) filters.sender = sender;
    if (startDate) filters.startDate = startDate;
    if (endDate) filters.endDate = endDate;
    
    const messages = await messageService.searchMessages(query, filters);
    res.json(formatSuccess(messages));
  } catch (error) {
    res.status(500).json(formatError('Failed to search messages', 500, { error: error.message }));
  }
});

router.get('/languages', (req, res) => {
  const languages = [
    { code: 'zh', name: '中文', englishName: 'Chinese' },
    { code: 'en', name: 'English', englishName: 'English' },
    { code: 'ja', name: '日本語', englishName: 'Japanese' },
    { code: 'ko', name: '한국어', englishName: 'Korean' },
    { code: 'fr', name: 'Français', englishName: 'French' },
    { code: 'de', name: 'Deutsch', englishName: 'German' },
    { code: 'es', name: 'Español', englishName: 'Spanish' },
    { code: 'pt', name: 'Português', englishName: 'Portuguese' },
    { code: 'ar', name: 'العربية', englishName: 'Arabic' },
    { code: 'ru', name: 'Русский', englishName: 'Russian' }
  ];
  
  res.json(formatSuccess(languages));
});

module.exports = router;
