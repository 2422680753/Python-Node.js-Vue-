const redis = require('redis');
const config = require('../config');

const redisClient = redis.createClient({
  url: config.redis.url
});

redisClient.on('error', (err) => {
  console.error('Redis Client Error:', err);
});

redisClient.on('connect', () => {
  console.log('Redis Connected');
});

const connectRedis = async () => {
  await redisClient.connect();
};

module.exports = { redisClient, connectRedis };
