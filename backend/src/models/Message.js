const mongoose = require('mongoose');

const messageSchema = new mongoose.Schema({
  messageId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  conversationId: {
    type: String,
    required: true,
    index: true
  },
  sequenceNumber: {
    type: Number,
    index: true
  },
  sender: {
    type: String,
    required: true,
    enum: ['user', 'bot', 'agent']
  },
  content: {
    type: String,
    required: true
  },
  originalContent: {
    type: String
  },
  language: {
    type: String,
    required: true,
    default: 'en'
  },
  translatedContent: {
    type: String
  },
  intent: {
    type: String
  },
  entities: {
    type: mongoose.Schema.Types.Mixed
  },
  confidence: {
    type: Number,
    default: 0
  },
  isEscalated: {
    type: Boolean,
    default: false
  },
  escalatedTo: {
    type: String
  },
  isSensitive: {
    type: Boolean,
    default: false
  },
  sensitiveInfo: {
    type: [String]
  },
  isCodeSwitching: {
    type: Boolean,
    default: false
  },
  languageDistribution: {
    type: mongoose.Schema.Types.Mixed
  },
  status: {
    type: String,
    enum: ['queued', 'processing', 'processed', 'failed', 'held'],
    default: 'queued'
  },
  queuedAt: {
    type: Date
  },
  processedAt: {
    type: Date
  },
  timestamp: {
    type: Date,
    default: Date.now,
    index: true
  },
  metadata: {
    type: mongoose.Schema.Types.Mixed,
    default: {}
  }
}, {
  timestamps: true
});

messageSchema.index({ conversationId: 1, sequenceNumber: 1 }, { unique: true, sparse: true });
messageSchema.index({ conversationId: 1, timestamp: -1 });
messageSchema.index({ language: 1 });
messageSchema.index({ 'content': 'text' });
messageSchema.index({ status: 1 });

module.exports = mongoose.model('Message', messageSchema);
