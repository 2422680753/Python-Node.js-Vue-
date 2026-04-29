import os
import json

KNOWLEDGE_BASE = {
    'intents': {
        'greeting': {
            'keywords': ['你好', '您好', 'hello', 'hi', '嗨', '您好吗', 'how are you'],
            'responses': {
                'zh': '您好！欢迎咨询我们的客服服务。有什么可以帮助您的吗？',
                'en': 'Hello! Welcome to our customer service. How can I assist you today?',
                'ja': 'こんにちは！カスタマーサービスへようこそ。今日はどのようなご用件でしょうか？',
                'ko': '안녕하세요! 고객 서비스에 오신 것을 환영합니다. 오늘 어떻게 도와드릴까요?',
                'fr': 'Bonjour! Bienvenue dans notre service clientèle. Comment puis-je vous aider aujourd\'hui?',
                'de': 'Hallo! Willkommen bei unserem Kundenservice. Wie kann ich Ihnen heute helfen?',
                'es': '¡Hola! Bienvenido a nuestro servicio al cliente. ¿Cómo puedo ayudarle hoy?',
                'pt': 'Olá! Bem-vindo ao nosso serviço de atendimento ao cliente. Como posso ajudá-lo hoje?',
                'ar': 'مرحباً! أهلاً بك في خدمة العملاء لدينا. كيف يمكنني مساعدتك اليوم؟',
                'ru': 'Привет! Добро пожаловать в нашу службу поддержки. Чем я могу помочь вам сегодня?'
            }
        },
        'order_status': {
            'keywords': ['订单', 'order', '物流', 'delivery', '发货', 'ship', '配送', 'track', 'tracking'],
            'responses': {
                'zh': '您可以在"我的订单"页面查看订单状态。如需查询物流信息，请提供订单号，我可以帮您查询。',
                'en': 'You can check your order status on the "My Orders" page. If you need to track your delivery, please provide your order number and I can help you check.',
                'ja': '「マイオーダー」ページで注文状況を確認できます。配送状況を追跡する必要がある場合は、注文番号をご提供ください。',
                'ko': '"내 주문" 페이지에서 주문 상태를 확인할 수 있습니다. 배송 조회가 필요하시면 주문 번호를 알려주세요.',
                'fr': 'Vous pouvez vérifier le statut de votre commande sur la page "Mes Commandes". Si vous avez besoin de suivre votre livraison, veuillez fournir votre numéro de commande.',
                'de': 'Sie können Ihren Bestellstatus auf der Seite "Meine Bestellungen" überprüfen. Wenn Sie Ihre Lieferung verfolgen müssen, geben Sie bitte Ihre Bestellnummer an.',
                'es': 'Puede consultar el estado de su pedido en la página "Mis Pedidos". Si necesita seguir su envío, por favor proporcione su número de pedido.',
                'pt': 'Você pode verificar o status do seu pedido na página "Meus Pedidos". Se precisar rastrear sua entrega, forneça o número do pedido.',
                'ar': 'يمكنك التحقق من حالة طلبك على صفحة "طلباتي". إذا كنت بحاجة لتتبع شحنتك، يرجى تزويدي برقم الطلب.',
                'ru': 'Вы можете проверить статус своего заказа на странице "Мои заказы". Если вам нужно отследить доставку, пожалуйста, предоставьте номер заказа.'
            }
        },
        'refund': {
            'keywords': ['退款', 'refund', '退货', 'return', '退换', 'exchange', '退款申请', '退钱'],
            'responses': {
                'zh': '了解您需要退款或退货服务。请提供订单号和退款原因，我将为您处理或转接专业客服人员协助。',
                'en': 'I understand you need refund or return service. Please provide your order number and reason for refund, and I will process it or transfer you to a professional customer service representative.',
                'ja': '返金または返品が必要なことを理解しました。注文番号と返金理由をご提供ください。専門のカスタマーサービス担当者にお繋ぎします。',
                'ko': '환불 또는 반품이 필요하신 것을 이해했습니다. 주문 번호와 환불 사유를 알려주시면 처리해 드리거나 전문 상담원에게 연결해 드리겠습니다.',
                'fr': 'Je comprends que vous avez besoin d\'un service de remboursement ou de retour. Veuillez fournir votre numéro de commande et la raison du remboursement.',
                'de': 'Ich verstehe, dass Sie einen Rückerstattungs- oder Rückgabeservice benötigen. Bitte geben Sie Ihre Bestellnummer und den Grund für die Rückerstattung an.',
                'es': 'Entiendo que necesita un servicio de reembolso o devolución. Por favor proporcione su número de pedido y el motivo del reembolso.',
                'pt': 'Entendo que você precisa de um serviço de reembolso ou devolução. Por favor, forneça seu número do pedido e o motivo do reembolso.',
                'ar': 'أفهم أنك تحتاج إلى خدمة استرداد أو إرجاع. يرجى تزويدي برقم الطلب وسبب الاسترداد.',
                'ru': 'Я понимаю, что вам нужна услуга возврата средств или товара. Пожалуйста, предоставьте номер заказа и причину возврата.'
            },
            'should_escalate': True
        },
        'complaint': {
            'keywords': ['投诉', 'complaint', '问题', 'problem', '不满意', 'unsatisfied', 'bad', '糟糕', '差', '劣质'],
            'responses': {
                'zh': '非常抱歉让您不满意。请您详细描述遇到的问题，我将立即为您转接专门处理投诉的客服人员。',
                'en': 'I\'m very sorry to hear that you\'re unsatisfied. Please describe the problem in detail, and I will immediately transfer you to a specialized customer service representative for complaints.',
                'ja': 'ご不満をおかけして誠に申し訳ございません。詳細をお聞かせいただければ、速やかに専門の担当者にお繋ぎします。',
                'ko': '불편을 드려 죄송합니다. 겪으신 문제를 자세히 말씀해 주시면 즉시 전문 상담원에게 연결해 드리겠습니다.',
                'fr': 'Je suis très désolé d\'apprendre que vous n\'êtes pas satisfait. Veuillez décrire le problème en détail, et je vous transférerai immédiatement à un spécialiste.',
                'de': 'Es tut mir sehr leid, dass Sie unzufrieden sind. Bitte beschreiben Sie das Problem im Detail, und ich werde Sie sofort an einen spezialisierten Vertreter weiterleiten.',
                'es': 'Siento mucho escuchar que no está satisfecho. Por favor describa el problema detalladamente, y lo transferiré inmediatamente a un representante especializado.',
                'pt': 'Sinto muito ouvir que você não está satisfeito. Por favor, descreva o problema em detalhes, e eu o transferirei imediatamente para um representante especializado.',
                'ar': 'أنا آسف جداً لسماع أنك غير راضٍ. يرجى وصف المشكلة بالتفصيل، وسأقوم بتحويلك فوراً إلى ممثل متخصص.',
                'ru': 'Мне очень жаль слышать, что вы недовольны. Пожалуйста, опишите проблему подробно, и я немедленно переведу вас к специализированному представителю.'
            },
            'should_escalate': True
        },
        'payment': {
            'keywords': ['支付', 'payment', '付款', 'pay', '信用卡', 'credit card', '支付宝', 'alipay', '微信', 'wechat', 'paypal'],
            'responses': {
                'zh': '我们支持多种支付方式：信用卡、支付宝、微信支付、PayPal等。如果您遇到支付问题，请详细描述，我可以帮您解答或转接支付客服。',
                'en': 'We support multiple payment methods: credit card, Alipay, WeChat Pay, PayPal, etc. If you encounter payment issues, please describe in detail, and I can help or transfer you to payment support.',
                'ja': 'クレジットカード、Alipay、WeChat Pay、PayPalなど、複数の支払い方法に対応しています。お支払いで問題がある場合は、詳細をお聞かせください。',
                'ko': '신용카드, Alipay, WeChat Pay, PayPal 등 다양한 결제 방식을 지원합니다. 결제에 문제가 있으시면 자세히 말씀해 주세요.',
                'fr': 'Nous prenons en charge plusieurs méthodes de paiement: carte de crédit, Alipay, WeChat Pay, PayPal, etc. Si vous rencontrez des problèmes de paiement, veuillez décrire en détail.',
                'de': 'Wir unterstützen mehrere Zahlungsmethoden: Kreditkarte, Alipay, WeChat Pay, PayPal usw. Wenn Sie Probleme bei der Zahlung haben, beschreiben Sie dies bitte im Detail.',
                'es': 'Aceptamos múltiples métodos de pago: tarjeta de crédito, Alipay, WeChat Pay, PayPal, etc. Si encuentra problemas de pago, por favor describa en detalle.',
                'pt': 'Aceitamos vários métodos de pagamento: cartão de crédito, Alipay, WeChat Pay, PayPal, etc. Se encontrar problemas de pagamento, por favor descreva em detalhe.',
                'ar': 'ندعم عدة طرق دفع: بطاقة ائتمان، Alipay، WeChat Pay، PayPal، إلخ. إذا واجهت مشاكل في الدفع، يرجى الوصف بالتفصيل.',
                'ru': 'Мы поддерживаем несколько способов оплаты: кредитная карта, Alipay, WeChat Pay, PayPal и т.д. Если у вас возникли проблемы с оплатой, пожалуйста, опишите подробно.'
            }
        },
        'technical_support': {
            'keywords': ['技术', 'technical', 'bug', '错误', 'error', '无法', 'cannot', '打不开', 'can\'t', '故障', '技术支持', '网站', 'app'],
            'responses': {
                'zh': '了解您遇到了技术问题。请详细描述您的问题，包括设备类型、操作系统、浏览器等信息，我将为您转接技术支持专员。',
                'en': 'I understand you\'re experiencing technical issues. Please describe your problem in detail, including device type, operating system, browser, etc. I will transfer you to a technical support specialist.',
                'ja': '技術的な問題が発生していることを理解しました。デバイスの種類、OS、ブラウザなどを含め、詳細をお聞かせください。',
                'ko': '기술적인 문제가 발생하신 것을 이해했습니다. 기기 종류, 운영체제, 브라우저 등을 포함해 자세히 말씀해 주세요.',
                'fr': 'Je comprends que vous rencontrez des problèmes techniques. Veuillez décrire votre problème en détail, y compris le type d\'appareil, le système d\'exploitation, le navigateur, etc.',
                'de': 'Ich verstehe, dass Sie technische Probleme haben. Bitte beschreiben Sie Ihr Problem im Detail, einschließlich Gerätetyp, Betriebssystem, Browser usw.',
                'es': 'Entiendo que está experimentando problemas técnicos. Por favor describa su problema detalladamente, incluyendo tipo de dispositivo, sistema operativo, navegador, etc.',
                'pt': 'Entendo que você está enfrentando problemas técnicos. Por favor, descreva seu problema em detalhes, incluindo tipo de dispositivo, sistema operacional, navegador, etc.',
                'ar': 'أفهم أنك تواجه مشاكل تقنية. يرجى وصف مشكلتك بالتفصيل، بما في ذلك نوع الجهاز، نظام التشغيل، المتصفح، إلخ.',
                'ru': 'Я понимаю, что у вас возникли технические проблемы. Пожалуйста, опишите вашу проблему подробно, включая тип устройства, операционную систему, браузер и т.д.'
            },
            'should_escalate': True
        },
        'product_info': {
            'keywords': ['产品', 'product', '商品', 'item', '价格', 'price', '尺寸', 'size', '颜色', 'color', '规格', 'spec', '库存', 'stock', 'available'],
            'responses': {
                'zh': '您可以在商品详情页面查看所有产品信息，包括价格、规格、库存等。如果您有具体问题，请提供商品名称或链接，我可以帮您查看。',
                'en': 'You can view all product information on the product detail page, including price, specifications, stock, etc. If you have specific questions, please provide the product name or link and I can help you check.',
                'ja': '商品詳細ページで価格、仕様、在庫など、すべての商品情報を確認できます。具体的な質問がある場合は、商品名またはリンクをご提供ください。',
                'ko': '상품 상세 페이지에서 가격, 사양, 재고 등 모든 제품 정보를 확인할 수 있습니다. 구체적인 질문이 있으시면 상품명이나 링크를 알려주세요.',
                'fr': 'Vous pouvez consulter toutes les informations produit sur la page détaillée du produit, y compris le prix, les spécifications, le stock, etc.',
                'de': 'Sie können alle Produktinformationen auf der Produkt-Detailseite einsehen, einschließlich Preis, Spezifikationen, Lagerbestand usw.',
                'es': 'Puede consultar toda la información del producto en la página de detalles del producto, incluyendo precio, especificaciones, stock, etc.',
                'pt': 'Você pode ver todas as informações do produto na página de detalhes do produto, incluindo preço, especificações, estoque, etc.',
                'ar': 'يمكنك عرض جميع معلومات المنتج على صفحة تفاصيل المنتج، بما في ذلك السعر، المواصفات، المخزون، إلخ.',
                'ru': 'Вы можете просмотреть всю информацию о продукте на странице деталей продукта, включая цену, спецификации, наличие на складе и т.д.'
            }
        },
        'shipping_info': {
            'keywords': ['运费', 'shipping', '包邮', 'free shipping', '关税', 'customs', '关税', 'duty', '国际', 'international', '海外', 'overseas'],
            'responses': {
                'zh': '关于国际物流：我们提供多种配送方式，运费根据目的地和重量计算。部分国家可能需要支付关税，详细信息请查看配送政策页面。如需具体报价，请提供收货地址和商品信息。',
                'en': 'About international shipping: We offer multiple delivery methods, and shipping costs are calculated based on destination and weight. Some countries may require customs duties. For detailed information, please check the shipping policy page. For specific quotes, please provide the delivery address and product information.',
                'ja': '国際配送について：複数の配送方法を提供しており、送料は目的地と重量に基づいて計算されます。一部の国では関税が必要になる場合があります。',
                'ko': '국제 배송에 대해: 여러 배송 방식을 제공하며, 배송비는 목적지와 무게에 따라 계산됩니다. 일부 국가에서는 관세가 필요할 수 있습니다.',
                'fr': 'À propos de la livraison internationale: Nous proposons plusieurs méthodes de livraison. Les frais d\'expédition sont calculés en fonction de la destination et du poids.',
                'de': 'Über internationalen Versand: Wir bieten mehrere Versandmethoden an. Die Versandkosten werden basierend auf Zielort und Gewicht berechnet.',
                'es': 'Sobre el envío internacional: Ofrecemos múltiples métodos de entrega. Los costos de envío se calculan según el destino y el peso.',
                'pt': 'Sobre o envio internacional: Oferecemos múltiplos métodos de entrega. Os custos de envio são calculados com base no destino e no peso.',
                'ar': 'حول الشحن الدولي: نقدم طرق توصيل متعددة. تُحسب تكاليف الشحن بناءً على الوجهة والوزن.',
                'ru': 'О международной доставке: Мы предлагаем несколько способов доставки. Стоимость доставки рассчитывается на основе пункта назначения и веса.'
            }
        }
    }
}

def get_knowledge_base():
    return KNOWLEDGE_BASE

def get_intent_response(intent, language='en'):
    intents = KNOWLEDGE_BASE.get('intents', {})
    if intent in intents:
        responses = intents[intent].get('responses', {})
        return responses.get(language, responses.get('en', ''))
    return ''

def should_escalate_intent(intent):
    intents = KNOWLEDGE_BASE.get('intents', {})
    if intent in intents:
        return intents[intent].get('should_escalate', False)
    return False
