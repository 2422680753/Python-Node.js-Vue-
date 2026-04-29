require('dotenv').config();

module.exports = {
  port: process.env.PORT || 3001,
  nodeEnv: process.env.NODE_ENV || 'development',
  mongodb: {
    uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/customer_service'
  },
  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379'
  },
  pythonService: {
    url: process.env.PYTHON_SERVICE_URL || 'http://localhost:5000'
  },
  jwtSecret: process.env.JWT_SECRET || 'your_jwt_secret_key_here',
  languages: ['zh', 'en', 'ja', 'ko', 'fr', 'de', 'es', 'pt', 'ar', 'ru'],
  messageQueue: {
    concurrency: 50,
    delay: 0,
    attempts: 3
  },
  rateLimit: {
    windowMs: 60000,
    max: 100
  }
};
