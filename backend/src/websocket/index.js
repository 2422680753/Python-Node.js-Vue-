const { Server } = require('socket.io');
const messageService = require('../services/messageService');
const { generateUserId } = require('../utils/helpers');

const setupWebSocket = (app, httpServer) => {
  const io = new Server(httpServer, {
    cors: {
      origin: "*",
      methods: ["GET", "POST"]
    },
    transports: ['websocket', 'polling'],
    pingTimeout: 60000,
    pingInterval: 25000
  });

  messageService.setIO(io);

  io.on('connection', (socket) => {
    console.log('Client connected:', socket.id);
    
    let userId = socket.handshake.query.userId || generateUserId();
    socket.data.userId = userId;
    
    socket.on('join-conversation', async ({ conversationId }) => {
      socket.join(conversationId);
      socket.data.conversationId = conversationId;
      
      try {
        const messages = await messageService.getConversationMessages(conversationId, 50, 0);
        socket.emit('conversation-history', { conversationId, messages });
      } catch (error) {
        console.error('Error loading conversation history:', error);
        socket.emit('error', { message: 'Failed to load conversation history' });
      }
      
      console.log(`Socket ${socket.id} joined conversation ${conversationId}`);
    });
    
    socket.on('leave-conversation', ({ conversationId }) => {
      socket.leave(conversationId);
      console.log(`Socket ${socket.id} left conversation ${conversationId}`);
    });
    
    socket.on('send-message', async ({ conversationId, content, language }) => {
      try {
        if (!content || content.trim().length === 0) {
          socket.emit('error', { message: 'Message content is required' });
          return;
        }
        
        const result = await messageService.processMessage(conversationId, content, language || 'en');
        
        socket.emit('message-queued', {
          messageId: result.messageId,
          sequenceNumber: result.sequenceNumber,
          timestamp: new Date()
        });
        
      } catch (error) {
        console.error('Error sending message:', error);
        socket.emit('error', { message: 'Failed to send message', error: error.message });
      }
    });
    
    socket.on('get-context', async ({ conversationId }) => {
      try {
        const context = await messageService.getConversationContext(conversationId);
        socket.emit('context-data', { conversationId, context });
      } catch (error) {
        console.error('Error getting context:', error);
        socket.emit('error', { message: 'Failed to get conversation context' });
      }
    });
    
    socket.on('verify-coherence', async ({ conversationId }) => {
      try {
        const result = await messageService.verifyConversationCoherence(conversationId);
        socket.emit('coherence-result', { conversationId, result });
      } catch (error) {
        console.error('Error verifying coherence:', error);
        socket.emit('error', { message: 'Failed to verify coherence' });
      }
    });
    
    socket.on('typing', ({ conversationId, isTyping }) => {
      socket.to(conversationId).emit('user-typing', {
        userId: socket.data.userId,
        isTyping,
        conversationId
      });
    });
    
    socket.on('read-messages', ({ conversationId, lastReadMessageId }) => {
      socket.to(conversationId).emit('messages-read', {
        userId: socket.data.userId,
        lastReadMessageId,
        conversationId
      });
    });
    
    socket.on('disconnect', () => {
      console.log('Client disconnected:', socket.id);
    });
  });

  io.on('message-processed', (data) => {
    const { conversationId, botMessage, escalated, userMessage } = data;
    
    io.to(conversationId).emit('bot-response', {
      message: botMessage,
      escalated,
      timestamp: new Date()
    });
    
    if (escalated) {
      io.to(conversationId).emit('conversation-escalated', {
        conversationId,
        reason: botMessage.metadata?.escalationReason || 'Unknown reason',
        timestamp: new Date()
      });
    }
  });

  return io;
};

module.exports = setupWebSocket;
