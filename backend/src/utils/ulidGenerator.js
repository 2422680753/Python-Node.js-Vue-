const crypto = require('crypto');
const { performance } = require('perf_hooks');

const CROCKFORD_BASE32 = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
const CROCKFORD_DECODE = {};
for (let i = 0; i < CROCKFORD_BASE32.length; i++) {
  CROCKFORD_DECODE[CROCKFORD_BASE32[i]] = i;
}

const TIMESTAMP_BITS = 48;
const RANDOM_BITS = 80;
const EPOCH = 1704067200000n;

let lastTimestamp = 0n;
let sequence = 0n;
const nodeId = BigInt(crypto.randomBytes(3).readUIntBE(0, 3));
const lock = { acquired: false };

class ULID {
  constructor(timestamp, randomness) {
    this.timestamp = BigInt(timestamp);
    this.randomness = BigInt(randomness);
  }

  toString() {
    return encodeULID(this.timestamp, this.randomness);
  }

  valueOf() {
    return (this.timestamp << BigInt(RANDOM_BITS)) | this.randomness;
  }

  static fromString(ulidStr) {
    if (ulidStr.length !== 26) {
      throw new Error('ULID must be 26 characters');
    }

    const timestampPart = ulidStr.slice(0, 10);
    const randomnessPart = ulidStr.slice(10);

    const timestamp = decodeBase32(timestampPart);
    const randomness = decodeBase32(randomnessPart);

    return new ULID(timestamp, randomness);
  }

  static now() {
    return generateULID();
  }

  getTimestampMs() {
    return Number(this.timestamp + EPOCH);
  }

  static compare(a, b) {
    if (a.timestamp !== b.timestamp) {
      return a.timestamp < b.timestamp ? -1 : 1;
    }
    return a.randomness < b.randomness ? -1 : 
           a.randomness > b.randomness ? 1 : 0;
  }
}

function encodeBase32(value, length = 10) {
  value = BigInt(value);
  let result = '';
  for (let i = 0; i < length; i++) {
    result = CROCKFORD_BASE32[Number(value & 31n)] + result;
    value = value >> 5n;
  }
  return result;
}

function decodeBase32(encoded) {
  let result = 0n;
  for (const char of encoded.toUpperCase()) {
    if (!(char in CROCKFORD_DECODE)) {
      throw new Error(`Invalid character: ${char}`);
    }
    result = (result << 5n) | BigInt(CROCKFORD_DECODE[char]);
  }
  return result;
}

function randomBytesToBigInt(byteCount) {
  const bytes = crypto.randomBytes(byteCount);
  let result = 0n;
  for (let i = 0; i < byteCount; i++) {
    result = (result << 8n) | BigInt(bytes[i]);
  }
  return result;
}

function acquireLock() {
  while (lock.acquired) {
    const start = performance.now();
    while (performance.now() - start < 1);
  }
  lock.acquired = true;
}

function releaseLock() {
  lock.acquired = false;
}

function generateULID(timestampMs = null) {
  let timestamp;
  
  if (timestampMs === null) {
    acquireLock();
    
    const currentMs = BigInt(Date.now());
    timestamp = currentMs - EPOCH;
    
    if (timestamp < lastTimestamp) {
      timestamp = lastTimestamp;
    }
    
    if (timestamp === lastTimestamp) {
      sequence = (sequence + 1n) & 0xFFFFn;
      if (sequence === 0n) {
        timestamp = timestamp + 1n;
      }
    } else {
      sequence = 0n;
    }
    
    lastTimestamp = timestamp;
    
    const randomHigh = (nodeId << 32n) | (randomBytesToBigInt(2) << 48n);
    const randomness = (randomHigh | sequence) & ((1n << BigInt(RANDOM_BITS)) - 1n);
    
    releaseLock();
    
    return new ULID(timestamp, randomness);
  } else {
    timestamp = BigInt(timestampMs) - EPOCH;
    if (timestamp < 0 || timestamp > (1n << BigInt(TIMESTAMP_BITS)) - 1n) {
      throw new Error(`Timestamp out of range: ${timestampMs}`);
    }
    const randomness = randomBytesToBigInt(10);
    return new ULID(timestamp, randomness);
  }
}

function encodeULID(timestamp, randomness) {
  const timestampEncoded = encodeBase32(timestamp, 10);
  const randomnessEncoded = encodeBase32(randomness, 16);
  return timestampEncoded + randomnessEncoded;
}

function parseULID(ulidStr) {
  return ULID.fromString(ulidStr);
}

function getTimestampFromULID(ulidStr) {
  const ulid = ULID.fromString(ulidStr);
  return ulid.getTimestampMs();
}

function isValidULID(ulidStr) {
  try {
    ULID.fromString(ulidStr);
    return true;
  } catch {
    return false;
  }
}

function generateMonotonicULID(previousULID = null) {
  if (!previousULID) {
    return generateULID();
  }

  const currentMs = BigInt(Date.now());
  const currentTimestamp = currentMs - EPOCH;

  if (currentTimestamp > previousULID.timestamp) {
    return generateULID(Number(currentMs));
  }

  let newTimestamp = previousULID.timestamp;
  let newRandomness = (previousULID.randomness + 1n) & ((1n << BigInt(RANDOM_BITS)) - 1n);

  if (newRandomness === 0n) {
    newTimestamp = newTimestamp + 1n;
    newRandomness = randomBytesToBigInt(10);
  }

  return new ULID(newTimestamp, newRandomness);
}

class MessageIdGenerator {
  constructor(prefix = 'msg') {
    this.prefix = prefix;
    this.conversationSequences = new Map();
  }

  generateMessageId(conversationId = null) {
    const ulid = generateULID();
    return `${this.prefix}_${ulid.toString()}`;
  }

  generateConversationId() {
    const ulid = generateULID();
    return `conv_${ulid.toString()}`;
  }

  generateUserId() {
    const ulid = generateULID();
    return `user_${ulid.toString()}`;
  }

  generateSequenceNumber(conversationId) {
    const current = this.conversationSequences.get(conversationId) || 0;
    const next = current + 1;
    this.conversationSequences.set(conversationId, next);
    return next;
  }

  getNextSequence(conversationId) {
    return (this.conversationSequences.get(conversationId) || 0) + 1;
  }

  resetSequence(conversationId) {
    this.conversationSequences.delete(conversationId);
  }
}

const messageIdGenerator = new MessageIdGenerator();

function generateMessageId(conversationId = null) {
  return messageIdGenerator.generateMessageId(conversationId);
}

function generateConversationId() {
  return messageIdGenerator.generateConversationId();
}

function generateUserId() {
  return messageIdGenerator.generateUserId();
}

function generateSequenceNumber(conversationId) {
  return messageIdGenerator.generateSequenceNumber(conversationId);
}

function extractTimestampFromId(idStr) {
  const parts = idStr.split('_');
  if (parts.length < 2) {
    return null;
  }

  const ulidPart = parts[parts.length - 1];
  if (ulidPart.length !== 26) {
    return null;
  }

  try {
    return getTimestampFromULID(ulidPart);
  } catch {
    return null;
  }
}

function compareIds(id1, id2) {
  try {
    const ulid1 = parseULID(id1.split('_')[id1.split('_').length - 1]);
    const ulid2 = parseULID(id2.split('_')[id2.split('_').length - 1]);
    return ULID.compare(ulid1, ulid2);
  } catch {
    return 0;
  }
}

module.exports = {
  ULID,
  generateULID,
  encodeULID,
  decodeBase32,
  parseULID,
  getTimestampFromULID,
  isValidULID,
  generateMonotonicULID,
  MessageIdGenerator,
  messageIdGenerator,
  generateMessageId,
  generateConversationId,
  generateUserId,
  generateSequenceNumber,
  extractTimestampFromId,
  compareIds
};
