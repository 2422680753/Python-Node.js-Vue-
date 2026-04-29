const { v4: uuidv4 } = require('uuid');

const generateId = () => uuidv4();

const generateMessageId = () => `msg_${uuidv4().replace(/-/g, '')}`;

const generateConversationId = () => `conv_${uuidv4().replace(/-/g, '')}`;

const generateUserId = () => `user_${uuidv4().replace(/-/g, '')}`;

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const retry = async (fn, maxAttempts = 3, delayMs = 1000) => {
  let lastError;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (attempt < maxAttempts) {
        await delay(delayMs * attempt);
      }
    }
  }
  
  throw lastError;
};

const formatError = (message, statusCode = 500, details = {}) => ({
  success: false,
  error: message,
  statusCode,
  details,
  timestamp: new Date().toISOString()
});

const formatSuccess = (data, message = 'Success') => ({
  success: true,
  message,
  data,
  timestamp: new Date().toISOString()
});

const extractLanguage = (acceptLanguage) => {
  if (!acceptLanguage) return 'en';
  
  const languages = acceptLanguage.split(',')[0];
  const langCode = languages.split(';')[0].split('-')[0].toLowerCase();
  
  const supportedLangs = ['zh', 'en', 'ja', 'ko', 'fr', 'de', 'es', 'pt', 'ar', 'ru'];
  
  return supportedLangs.includes(langCode) ? langCode : 'en';
};

const safeJsonParse = (str, defaultValue = {}) => {
  try {
    return JSON.parse(str);
  } catch {
    return defaultValue;
  }
};

const isProduction = () => process.env.NODE_ENV === 'production';

const measureExecutionTime = (label) => {
  const start = process.hrtime();
  return () => {
    const diff = process.hrtime(start);
    const ms = diff[0] * 1000 + diff[1] / 1e6;
    return { label, ms };
  };
};

module.exports = {
  generateId,
  generateMessageId,
  generateConversationId,
  generateUserId,
  delay,
  retry,
  formatError,
  formatSuccess,
  extractLanguage,
  safeJsonParse,
  isProduction,
  measureExecutionTime
};
