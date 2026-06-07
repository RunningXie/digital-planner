# Dear Diary - 英文日记本

一个温馨的英文日记Web应用，帮助您用英文记录生活，并通过AI逐句批改提升英文写作水平。

## 功能特性

- 🔐 **账号系统** - 安全的用户注册与登录
- ✍️ **日记撰写** - 简洁优雅的写作界面
- 🤖 **AI批改** - 逐句分析英文表达，提供优化建议
- 🔍 **短语搜索** - 写作时随时搜索地道英文表达
- 📚 **日记管理** - 查看历史日记和批改记录

## 技术栈

- **后端**: Python + FastAPI
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **前端**: HTML + CSS + JavaScript
- **AI**: 智谱GLM-4.5-Air
- **部署**: Docker + Docker Compose

## 快速开始

### 本地开发

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 配置环境变量:
```bash
cp .env.example .env
# 编辑 .env 文件，设置您的API密钥
```

3. 运行应用:
```bash
python main.py
```

应用将在 http://localhost:8000 启动

### Docker部署

1. 构建并运行:
```bash
docker-compose up -d
```

2. 查看日志:
```bash
docker-compose logs -f
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_URL | 数据库连接URL | sqlite:///./diary.db |
| AI_BASE_URL | AI API地址 | https://open.bigmodel.cn/api/paas/v4 |
| AI_API_KEY | AI API密钥 | - |
| AI_MODEL | AI模型名称 | glm-4.5-air |
| SECRET_KEY | JWT密钥 | - |
| DEBUG | 调试模式 | True |

## 项目结构

```
diary-app/
├── main.py              # 主应用入口
├── config.py            # 配置管理
├── database.py          # 数据库配置
├── models.py            # 数据模型
├── schemas.py           # Pydantic模型
├── auth.py              # 认证逻辑
├── ai_service.py        # AI服务
├── requirements.txt     # Python依赖
├── Dockerfile           # Docker镜像
├── docker-compose.yml   # Docker编排
├── static/              # 静态文件
│   ├── css/
│   └── js/
└── templates/           # HTML模板
```

## 腾讯云部署指南

1. 在腾讯云服务器上安装Docker和Docker Compose

2. 复制项目文件到服务器:
```bash
scp -r digital-planner/ root@your-server-ip:/opt/
```

3. 在服务器上启动:
```bash
cd /opt/digital-planner
docker-compose up -d
```

4. 配置Nginx反向代理（可选）:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 使用说明

1. 访问首页，注册账号
2. 登录后进入写日记页面
3. 用英文撰写日记，点击"保存并批改"
4. 查看AI批改结果和优化版本
5. 在写作过程中可以使用短语搜索功能查找表达

## 注意事项

- 请妥善保管您的AI API密钥
- 生产环境请修改SECRET_KEY
- 建议在生产环境使用PostgreSQL替代SQLite
- 定期备份数据库文件

## License

MIT License
