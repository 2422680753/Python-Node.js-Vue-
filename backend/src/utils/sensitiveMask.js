const SENSITIVE_PATTERNS = {
  creditCard: {
    regex: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g,
    replacement: '****-****-****-****',
    description: 'Credit card number'
  },
  bankAccount: {
    regex: /\b\d{8,18}\b/g,
    replacement: '************',
    description: 'Bank account number'
  },
  email: {
    regex: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    replacement: '***@***.***',
    description: 'Email address'
  },
  phone: {
    regex: /(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}/g,
    replacement: '****-****',
    description: 'Phone number'
  },
  idCard: {
    regex: /\b\d{17}[\dXx]\b/g,
    replacement: '******************',
    description: 'ID card number'
  },
  passport: {
    regex: /\b[A-Z]{1,2}\d{7,9}\b/g,
    replacement: '*********',
    description: 'Passport number'
  }
};

const maskSensitiveInfo = (text) => {
  if (!text || typeof text !== 'string') {
    return { maskedText: text, isSensitive: false, sensitiveTypes: [] };
  }

  let maskedText = text;
  const sensitiveTypes = [];
  const foundSensitive = [];

  for (const [type, pattern] of Object.entries(SENSITIVE_PATTERNS)) {
    const matches = [...maskedText.matchAll(pattern.regex)];
    if (matches.length > 0) {
      matches.forEach(match => {
        foundSensitive.push({
          type,
          value: match[0],
          description: pattern.description
        });
      });
      maskedText = maskedText.replace(pattern.regex, pattern.replacement);
      sensitiveTypes.push(type);
    }
  }

  return {
    maskedText,
    isSensitive: sensitiveTypes.length > 0,
    sensitiveTypes: [...new Set(sensitiveTypes)],
    foundSensitive
  };
};

const validateSensitivePatterns = (text) => {
  const violations = [];
  
  for (const [type, pattern] of Object.entries(SENSITIVE_PATTERNS)) {
    const matches = text.match(pattern.regex);
    if (matches) {
      violations.push({
        type,
        description: pattern.description,
        count: matches.length,
        examples: matches.slice(0, 3)
      });
    }
  }

  return {
    hasViolations: violations.length > 0,
    violations
  };
};

module.exports = {
  maskSensitiveInfo,
  validateSensitivePatterns,
  SENSITIVE_PATTERNS
};
