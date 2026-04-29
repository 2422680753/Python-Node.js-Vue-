import os
from flask import Flask
from flask_cors import CORS
from config import config

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    os.makedirs(config.MODEL_PATH, exist_ok=True)
    os.makedirs(config.KNOWLEDGE_BASE_PATH, exist_ok=True)
    
    from routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    @app.route('/health')
    def health_check():
        return {
            'status': 'healthy',
            'service': 'nlp-translation-service',
            'languages': config.LANGUAGES
        }
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=config.PORT, debug=config.DEBUG)
