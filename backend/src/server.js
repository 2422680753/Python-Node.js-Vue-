const express = require('express');
const http = require('http');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const config = require('./config');
const connectDB = require('./config/database');
const { connectRedis } = require('./config/redis');
const apiRoutes = require('./routes/api');
const setupWebSocket = require('./websocket');

const app = express();
const server = http.createServer(app);

app.use(helmet());
app.use(cors({
  origin: config.nodeEnv === 'production' ? ['https://your-domain.com'] : '*',
  credentials: true
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

const limiter = rateLimit({
  windowMs: config.rateLimit.windowMs,
  max: config.rateLimit.max,
  message: { success: false, error: 'Too many requests, please try again later.' },
  standardHeaders: true,
  legacyHeaders: false,
});

app.use(limiter);

app.use('/api/v1', apiRoutes);

app.get('/health', (req, res) => {
  res.json({
    success: true,
    message: 'Customer service backend is running',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(err.status || 500).json({
    success: false,
    error: config.nodeEnv === 'development' ? err.message : 'Internal server error',
    timestamp: new Date().toISOString()
  });
});

app.use('*', (req, res) => {
  res.status(404).json({
    success: false,
    error: 'Route not found',
    timestamp: new Date().toISOString()
  });
});

const io = setupWebSocket(app, server);
app.set('io', io);

const startServer = async () => {
  try {
    console.log('Starting customer service backend...');
    console.log(`Environment: ${config.nodeEnv}`);
    
    await connectDB();
    console.log('MongoDB connected successfully');
    
    await connectRedis();
    console.log('Redis connected successfully');
    
    server.listen(config.port, () => {
      console.log(`Server running on port ${config.port}`);
      console.log(`WebSocket server running on ws://localhost:${config.port}`);
      console.log(`API endpoint: http://localhost:${config.port}/api/v1`);
      console.log('Supported languages: zh, en, ja, ko, fr, de, es, pt, ar, ru');
    });
    
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
};

startServer();

process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

module.exports = { app, server, io };
