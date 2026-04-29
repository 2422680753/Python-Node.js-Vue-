const mongoose = require('mongoose');

const conversationSchema = new mongoose.Schema({
  conversationId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  userId: {
    type: String,
    required: true,
    index: true
  },
  userLanguage: {
    type: String,
    required: true,
    default: 'en'
  },
  status: {
    type: String,
    required: true,
    enum: ['active', 'closed', 'escalated'],
    default: 'active'
  },
  currentAgent: {
    type: String
  },
  messageCount: {
    type: Number,
    default: 0
  },
  intents: {
    type: [String]
  },
  startTime: {
    type: Date,
    default: Date.now
  },
  endTime: {
    type: Date
  },
  lastMessageTime: {
    type: Date,
    default: Date.now
  },
  satisfactionScore: {
    type: Number
  },
  metadata: {
    type: mongoose.Schema.Types.Mixed,
    default: {}
  }
}, {
  timestamps: true
});

conversationSchema.index({ userId: 1, status: 1 });
conversationSchema.index({ status: 1, lastMessageTime: -1 });

module.exports = mongoose.model('Conversation', conversationSchema);
