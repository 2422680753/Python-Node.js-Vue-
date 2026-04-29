# 跨境电商多语言客服机器人

采用 Python + Node.js + Vue 全栈技术栈，打造智能客服系统。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue 3)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  用户聊天界面  │  │  客服管理面板  │  │  对话搜索功能  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Node.js 后端服务                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ WebSocket    │  │ API Gateway  │  │ Message Queue│      │
│  │ (实时通信)    │  │ (REST API)   │  │ (Bull + Redis)│     │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python NLP 服务                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 语言检测      │  │ 意图识别      │  │ 智能回复生成  │      │
│  │ 多语言翻译    │  │ 实体提取      │  │ 知识库匹配    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         数据存储                              │
│  ┌──────────────────┐  ┌─────────────────────────────────┐  │
│  │ MongoDB          │  │ Redis                           │  │
│  │ - 对话记录       │  │ - 消息队列 (Bull)              │  │
│  │ - 用户信息       │  │ - 会话缓存                      │  │
│  │ - 搜索索引       │  │ - 高并发处理                    │  │
│  └──────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 核心功能

### 🗣️ 10种语言支持
- 中文 (zh)
- 英文 (en)
- 日文 (ja)
- 韩文 (ko)
- 法文 (fr)
- 德文 (de)
- 西班牙文 (es)
- 葡萄牙文 (pt)
- 阿拉伯文 (ar)
- 俄文 (ru)

### ⚡ 秒级响应
- 基于关键词匹配和意图识别，快速定位用户需求
- 预定义知识库，智能生成回复
- WebSocket实时通信，无延迟

### 👥 复杂问题自动转人工
- 智能识别需要人工处理的场景：
  - 投诉问题
  - 退款退货申请
  - 技术支持需求
  - 低置信度意图
- 无缝转接，用户无感知

### 🔒 敏感信息自动打码
- 信用卡号: `****-****-****-****`
- 银行账号: `************`
- 电子邮箱: `***@***.***`
- 电话号码: `****-****`
- 身份证号: `******************`
- 护照号: `*********`

### 📝 对话记录全保存 + 搜索
- 所有对话自动存入 MongoDB
- 支持全文搜索
- 支持按时间范围、语言、发送者筛选
- 支持关键词高亮

### 🚀 高并发处理 (每秒1000条消息)
- Bull 消息队列 (Redis 后端)
- 并发处理 (可配置并发数)
- 消息持久化
- 失败重试机制
- 限流保护

## 快速开始

### 环境要求
- Node.js >= 16.0.0
- Python >= 3.9
- MongoDB >= 5.0
- Redis >= 6.0

### 安装步骤

#### 1. 启动 MongoDB 和 Redis
```bash
# MongoDB (默认端口 27017)
mongod

# Redis (默认端口 6379)
redis-server
```

#### 2. 安装 Node.js 后端依赖
```bash
cd backend
npm install
```

#### 3. 配置 Node.js 后端
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，根据实际情况修改配置
```

#### 4. 启动 Node.js 后端
```bash
cd backend
npm run dev
```

#### 5. 安装 Python 服务依赖
```bash
cd python-service

# 创建虚拟环境 (推荐)
python -m venv venv

# Windows 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 6. 启动 Python NLP 服务
```bash
cd python-service
python app.py
```

#### 7. 安装 Vue 前端依赖
```bash
cd frontend
npm install
```

#### 8. 启动 Vue 前端
```bash
cd frontend
npm run dev
```

### 访问应用

- **用户聊天界面**: http://localhost:5173
- **客服管理面板**: http://localhost:5173/admin (登录后)
- **Node.js 后端 API**: http://localhost:3001
- **Python NLP 服务**: http://localhost:5000

## 项目结构

```
Python-Node.js-Vue-/
├── backend/                    # Node.js 后端
│   ├── package.json
│   ├── .env.example
│   └── src/
│       ├── server.js          # 主入口文件
│       ├── config/            # 配置文件
│       │   ├── index.js
│       │   ├── database.js    # MongoDB 配置
│       │   └── redis.js       # Redis 配置
│       ├── models/            # 数据模型
│       │   ├── Message.js
│       │   └── Conversation.js
│       ├── services/          # 业务逻辑
│       │   ├── messageService.js
│       │   ├── conversationService.js
│       │   └── pythonService.js
│       ├── routes/            # API 路由
│       │   └── api.js
│       ├── utils/             # 工具函数
│       │   ├── sensitiveMask.js  # 敏感信息打码
│       │   └── helpers.js
│       └── websocket/         # WebSocket 处理
│           └── index.js
│
├── python-service/            # Python NLP 服务
│   ├── requirements.txt
│   ├── config.py              # 配置
│   ├── app.py                 # Flask 应用入口
│   ├── services/              # NLP 服务
│   │   ├── __init__.py
│   │   ├── language_detector.py   # 语言检测
│   │   ├── intent_classifier.py   # 意图识别
│   │   ├── response_generator.py  # 回复生成
│   │   └── knowledge_base.py      # 知识库
│   └── routes/                # API 路由
│       ├── __init__.py
│       └── api.py
│
├── frontend/                   # Vue 3 前端
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js            # 入口文件
│       ├── App.vue
│       ├── router/            # 路由配置
│       │   └── index.js
│       ├── stores/            # Pinia 状态管理
│       │   ├── auth.js
│       │   ├── settings.js
│       │   └── chat.js
│       ├── services/          # API 服务
│       │   └── api.js
│       ├── styles/            # 样式文件
│       │   └── main.scss
│       └── views/             # 视图组件
│           ├── Home.vue       # 首页
│           ├── Chat.vue       # 用户聊天界面
│           ├── Login.vue      # 登录页
│           ├── NotFound.vue
│           └── Admin/          # 客服管理面板
│               ├── Dashboard.vue
│               ├── Conversations.vue
│               ├── ConversationDetail.vue
│               ├── Search.vue
│               └── Escalated.vue
│
├── README.md
└── .gitignore
```

## API 文档

### Node.js 后端 API (端口 3001)

#### 对话管理
- `POST /api/v1/conversations` - 创建新对话
- `GET /api/v1/conversations/:id` - 获取对话详情
- `GET /api/v1/conversations/:id/messages` - 获取对话消息
- `POST /api/v1/conversations/:id/messages` - 发送消息
- `POST /api/v1/conversations/:id/close` - 关闭对话
- `POST /api/v1/conversations/:id/assign-agent` - 分配客服
- `GET /api/v1/conversations/status/active` - 获取活跃对话
- `GET /api/v1/conversations/status/escalated` - 获取已转接对话

#### 搜索
- `GET /api/v1/search/messages` - 搜索消息

#### 其他
- `GET /api/v1/languages` - 获取支持的语言列表
- `GET /health` - 健康检查

### Python NLP 服务 API (端口 5000)

- `POST /api/detect-language` - 检测语言
- `POST /api/translate` - 翻译文本
- `POST /api/intent` - 意图识别
- `POST /api/entities` - 实体提取
- `POST /api/generate-response` - 生成回复
- `POST /api/analyze` - 完整分析 (语言+意图+翻译+回复)
- `GET /api/intents` - 获取所有意图
- `GET /api/languages` - 获取支持的语言
- `GET /api/health` - 健康检查

## 高并发架构说明

### 消息队列 (Bull + Redis)
- 消息进入队列后立即返回，不阻塞请求
- 支持并发消费 (默认 50 并发)
- 失败自动重试 (最多 3 次)
- 延迟队列支持

### 限流保护
- 使用 `express-rate-limit`
- 默认每分钟 100 请求/IP
- 可配置调整

### WebSocket 优化
- 心跳检测 (25s ping, 60s timeout)
- 断线重连机制
- 房间管理 (按会话隔离)

## 敏感信息打码示例

**输入**:
```
我的信用卡号是 4111-1111-1111-1111，手机号是 13812345678，
邮箱是 test@example.com，身份证号是 110101199001011234。
```

**输出**:
```
我的信用卡号是 ****-****-****-****，手机号是 ****-****，
邮箱是 ***@***.***，身份证号是 ******************。
```

## 生产部署建议

### 1. 使用 PM2 管理 Node.js 进程
```bash
npm install -g pm2
cd backend
pm2 start src/server.js --name "customer-service-backend"
```

### 2. 使用 Gunicorn 部署 Python 服务
```bash
cd python-service
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 3. Nginx 反向代理
```nginx
upstream node_backend {
    server 127.0.0.1:3001;
}

upstream python_service {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://node_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /socket.io/ {
        proxy_pass http://node_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。
