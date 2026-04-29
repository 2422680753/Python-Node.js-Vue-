const axios = require('axios');
const config = require('../config');

class PythonService {
  constructor() {
    this.baseUrl = config.pythonService.url;
    this.timeout = 5000;
  }

  async detectLanguage(text) {
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/detect-language`,
        { text },
        { timeout: this.timeout }
      );
      return response.data;
    } catch (error) {
      console.error('Language detection error:', error.message);
      return { language: 'en', confidence: 0.5 };
    }
  }

  async translate(text, targetLang, sourceLang = null) {
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/translate`,
        { text, targetLang, sourceLang },
        { timeout: this.timeout }
      );
      return response.data;
    } catch (error) {
      console.error('Translation error:', error.message);
      return { translatedText: text, sourceLang, targetLang };
    }
  }

  async analyzeIntent(text, language = 'en') {
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/intent`,
        { text, language },
        { timeout: this.timeout }
      );
      return response.data;
    } catch (error) {
      console.error('Intent analysis error:', error.message);
      return {
        intent: 'unknown',
        confidence: 0.3,
        entities: [],
        suggestedResponses: []
      };
    }
  }

  async generateResponse(text, context = {}, language = 'en') {
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/generate-response`,
        { text, context, language },
        { timeout: this.timeout }
      );
      return response.data;
    } catch (error) {
      console.error('Response generation error:', error.message);
      return {
        response: '我理解您的问题，正在为您转接人工客服...',
        shouldEscalate: true,
        reason: 'Cannot generate automated response'
      };
    }
  }

  async extractEntities(text, language = 'en') {
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/entities`,
        { text, language },
        { timeout: this.timeout }
      );
      return response.data;
    } catch (error) {
      console.error('Entity extraction error:', error.message);
      return { entities: [] };
    }
  }

  async shouldEscalate(intent, confidence, messageCount = 0) {
    const escalationRules = [
      { condition: () => intent === 'complaint', reason: 'Customer complaint' },
      { condition: () => intent === 'refund' && confidence < 0.6, reason: 'Low confidence refund request' },
      { condition: () => intent === 'technical_support', reason: 'Technical support needed' },
      { condition: () => confidence < 0.4, reason: 'Low intent confidence' },
      { condition: () => messageCount > 5, reason: 'Long conversation history' }
    ];

    for (const rule of escalationRules) {
      if (rule.condition()) {
        return { shouldEscalate: true, reason: rule.reason };
      }
    }

    return { shouldEscalate: false, reason: null };
  }
}

module.exports = new PythonService();
