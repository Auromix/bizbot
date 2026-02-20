<p align="center">
  <h1 align="center">🤖 BizBot</h1>
  <p align="center">
    <strong>AI-powered business management framework — manage your shop with natural language.</strong>
  </p>
  <p align="center">
    LLM Agent &nbsp;·&nbsp; Database ORM &nbsp;·&nbsp; Web Dashboard
  </p>
  <p align="center">
    <a href="https://github.com/Auromix/bizbot/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+"></a>
    <a href="https://github.com/Auromix/bizbot/issues"><img src="https://img.shields.io/github/issues/Auromix/bizbot.svg" alt="Issues"></a>
    <a href="https://github.com/Auromix/bizbot/stargazers"><img src="https://img.shields.io/github/stars/Auromix/bizbot.svg?style=social" alt="Stars"></a>
  </p>
</p>

---

BizBot is an open-source framework that lets small-business owners — salons, gyms, clinics, and more — run their entire shop through **natural-language conversations** with an AI agent. It combines a multi-provider LLM agent, a repository-pattern database layer, and a real-time web dashboard into one deployable package.

> **"帮我记一下，陈阿姨做了推拿按摩，张师傅做的，198 元"**
> → BizBot automatically creates a service record, assigns the technician, and updates daily revenue.

## ✨ Features

- 🗣️ **Natural Language Operations** — Talk to your business: record sales, manage members, check revenue, all through chat
- 🧠 **Multi-LLM Support** — OpenAI GPT, Anthropic Claude, MiniMax, and any OpenAI-compatible model
- 🔧 **30+ Tool Functions** — Full CRUD for services, products, staff, customers, memberships, channels, and analytics
- 📊 **Web Dashboard** — Real-time data visualization with JWT-secured login
- 🗄️ **Repository-Pattern ORM** — Clean SQLAlchemy layer supporting SQLite and PostgreSQL
- 🔌 **Pluggable Business Config** — Swap business types (clinic → salon → gym) by changing one config file
- 🚀 **One-Command Deploy** — `python app.py` and you're live

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Dashboard (FastAPI)                  │
│              Chat UI  ·  Data Tables  ·  Analytics           │
├──────────────────────────┬──────────────────────────────────┤
│       LLM Agent          │       Database Layer             │
│  ┌──────────────────┐    │  ┌────────────────────────────┐  │
│  │ OpenAI / Claude / │    │  │ Entity Repos (Staff,       │  │
│  │ MiniMax / Custom  │    │  │   Customer, Product, ...)  │  │
│  ├──────────────────┤    │  ├────────────────────────────┤  │
│  │ Function Registry │    │  │ Business Repos (Service    │  │
│  │ Tool Executor     │    │  │   Record, Sale, Member)    │  │
│  │ Auto-Discovery    │    │  ├────────────────────────────┤  │
│  └──────────────────┘    │  │ System Repos (Message,     │  │
│                          │  │   Summary, Plugin)         │  │
│                          │  └────────────────────────────┘  │
├──────────────────────────┴──────────────────────────────────┤
│                  Business Config (Pluggable)                 │
│          TherapyStore · HairSalon · Gym · Custom            │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Project Structure

```
bizbot/
├── agent/                 # LLM agent framework
│   ├── agent.py           #   Core agent with multi-turn tool calling
│   ├── providers/         #   LLM providers (OpenAI, Claude, MiniMax, ...)
│   └── functions/         #   Function registry, executor, auto-discovery
├── database/              # Repository-pattern ORM
│   ├── models.py          #   SQLAlchemy models
│   ├── entity_repos.py    #   Staff, Customer, ServiceType, Product, Channel
│   ├── business_repos.py  #   ServiceRecord, ProductSale, Membership
│   ├── system_repos.py    #   Message, Summary, Plugin
│   └── manager.py         #   DatabaseManager facade
├── interface/             # User interaction channels
│   ├── web/               #   FastAPI web dashboard + chat
│   └── terminal/          #   CLI channel for development
├── config/                # Pluggable business configuration
│   ├── business_config.py #   Abstract base + default TherapyStore config
│   ├── business_functions.py  # 30+ agent-callable functions
│   ├── register_functions.py  # Function registration
│   └── settings.py        #   Environment-based settings
├── scripts/               # Utility scripts
│   ├── setup_env.py       #   Interactive .env generator
│   └── init_db.py         #   Database initialization
├── examples/              # Usage examples
├── tests/                 # Comprehensive test suite
├── app.py                 # Application entry point
├── environment.yml        # Conda environment definition
├── pyproject.toml         # Python project & tool configuration
└── requirements.txt       # Pip dependencies reference
```

## 🚀 Quick Start

### Prerequisites

- **[Miniconda](https://docs.conda.io/en/latest/miniconda.html)** (推荐) 或 Python 3.10+
- An LLM API key (MiniMax by default, or OpenAI / Anthropic)

### 1. Clone the repository

```bash
git clone https://github.com/Auromix/bizbot.git
cd bizbot
```

### 2. Create conda environment

```bash
conda env create -f environment.yml
conda activate bizbot
```

### 3. Configure environment

Run the interactive setup wizard:

```bash
python scripts/setup_env.py
```

Or manually create a `.env` file:

```ini
# === LLM Configuration (MiniMax default) ===
MINIMAX_API_KEY=your-api-key-here
MINIMAX_MODEL=MiniMax-M2.5
MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic

# === Database ===
DATABASE_URL=sqlite:///data/store.db

# === Web Dashboard ===
WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_USERNAME=admin
WEB_PASSWORD=admin123
WEB_SECRET_KEY=change-me-to-a-random-secret-key
```

### 4. Launch

```bash
python app.py
```

Open **http://localhost:8080** in your browser, log in, and start chatting!

```
============================================================
  🤖 BizBot — 理疗馆 is running!
  URL:       http://localhost:8080
  Username:  admin
  Password:  admin123
  Agent:     ✅ enabled
  Functions: 30 registered
============================================================
```

## 💬 Usage Examples

### Natural Language → Business Operations

| You say | BizBot does |
|---------|------------|
| "帮我记一下，陈阿姨做了推拿按摩，张师傅做的，198元" | Creates service record with customer, technician, and amount |
| "王女士办年卡3000" | Opens a membership card (annual, ¥3000) |
| "赵先生买了两盒艾条" | Records product sale |
| "今天收入多少" | Returns daily revenue summary |
| "帮我加一个新技师小孙，提成30%" | Adds a new staff member |
| "查一下张师傅这个月的提成" | Calculates commission for date range |
| "哪些会员快到期了" | Lists expiring memberships |

### Python API

```python
from agent import Agent, create_provider, FunctionRegistry

# Create an LLM provider
provider = create_provider("openai", api_key="sk-...", model="gpt-4o-mini")

# Create agent with function calling
registry = FunctionRegistry()
agent = Agent(provider, registry, system_prompt="You are a helpful assistant.")

# Chat
response = await agent.chat("Show me today's revenue")
print(response["content"])
```

```python
from database import DatabaseManager

db = DatabaseManager("sqlite:///data/store.db")
db.create_tables()

# Repository-pattern access
staff = db.staff.get_or_create("Alice")
records = db.get_daily_records("2025-01-28")
```

## 🔌 Supported LLM Providers

| Provider | Models | Status |
|----------|--------|--------|
| **MiniMax** | MiniMax-M2.5 | ✅ Default |
| **OpenAI** | GPT-4o, GPT-4o-mini, etc. | ✅ Supported |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus, etc. | ✅ Supported |
| **Open Source** | Any OpenAI-compatible API (vLLM, Ollama, etc.) | ✅ Supported |

Switch providers by changing one line in your `.env`:

```ini
# Use OpenAI instead
OPENAI_API_KEY=sk-...
```

## 🏪 Custom Business Types

BizBot ships with a default **therapy clinic** (理疗馆) config. To adapt it for your business:

1. **Quick customization** — Edit `config/business_config.py` directly:

```python
class TherapyStoreConfig(BusinessConfig):
    STORE_NAME = "My Hair Salon"          # Change store name
    SERVICE_TYPES = [                      # Change services
        {"name": "Haircut", "default_price": 30.0, "category": "cut"},
        {"name": "Color", "default_price": 80.0, "category": "color"},
    ]
    # ... customize products, staff, channels, etc.
```

2. **Full customization** — Create a new config class:

```python
class GymConfig(BusinessConfig):
    """Gym / Fitness center configuration"""
    def get_business_name(self) -> str:
        return "FitZone Gym"
    # ... implement all abstract methods

# Swap the global config
business_config = GymConfig()
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific module tests
pytest tests/database/ -v
pytest tests/agent/ -v

# With coverage
pytest tests/ --cov=agent --cov=database --cov=interface --cov=config
```

## 🛠️ Development

```bash
# Install dev dependencies
pip install -e ".[all,dev]"

# Format code
black .
isort .

# Type checking
mypy agent/ database/

# Lint
flake8 agent/ database/ interface/ config/
```

## ☁️ Ubuntu 云服务器部署（阿里云）

本节说明如何在阿里云 ECS（Ubuntu 22.04）上部署 BizBot，并通过公网 IP 或域名从浏览器访问。

### 前置条件

- 阿里云 ECS，操作系统：Ubuntu 22.04 LTS（推荐）
- 安全组已放行入方向端口：**8080**（或自定义端口）
- 已获取 MiniMax API Key

---

### 第一步：安装 Miniconda

```bash
# 下载 Miniconda（Linux x86_64）
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh

# 静默安装到 ~/miniconda3
bash ~/miniconda.sh -b -p ~/miniconda3

# 初始化 conda（写入 .bashrc）
~/miniconda3/bin/conda init bash
source ~/.bashrc

# 验证
conda --version
```

---

### 第二步：克隆项目

```bash
git clone https://github.com/Auromix/bizbot.git
cd bizbot
```

---

### 第三步：创建并激活 conda 环境

```bash
conda env create -f environment.yml
conda activate bizbot
```

---

### 第四步：配置 `.env`

**方式 A：交互式向导（推荐）**

```bash
python scripts/setup_env.py
```

**方式 B：手动创建**

```bash
cp .env.example .env
nano .env
```

至少需要填写（**务必修改默认密码！**）：

```ini
MINIMAX_API_KEY=你的MiniMax_API_Key

WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_USERNAME=admin
WEB_PASSWORD=你的强密码
WEB_SECRET_KEY=随机生成一个长字符串
```

---

### 第五步：验证启动

```bash
conda activate bizbot
python app.py
```

看到以下输出说明启动成功：

```
============================================================
  🤖 BizBot — xxx is running!
  URL:       http://localhost:8080
  External:  http://YOUR_IP:8080
  ...
============================================================
```

此时即可通过 `http://服务器公网IP:8080` 从个人电脑访问。

---

### 第六步：阿里云安全组放行端口

在 **阿里云控制台 → ECS → 安全组 → 入方向规则** 中添加：

| 协议 | 端口范围 | 授权对象 |
|------|----------|----------|
| TCP  | 8080/8080 | 0.0.0.0/0 |

---

### 第七步（推荐）：配置 systemd 后台服务

避免 SSH 断开后服务停止，将 BizBot 注册为系统服务：

```bash
sudo nano /etc/systemd/system/bizbot.service
```

写入以下内容（将 `YOUR_USER` 替换为你的实际用户名）：

```ini
[Unit]
Description=BizBot AI Business Platform
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/bizbot
ExecStart=/home/YOUR_USER/miniconda3/envs/bizbot/bin/python app.py
Restart=on-failure
RestartSec=5
Environment=PATH=/home/YOUR_USER/miniconda3/envs/bizbot/bin

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable bizbot
sudo systemctl start bizbot

# 查看运行状态 / 实时日志
sudo systemctl status bizbot
sudo journalctl -u bizbot -f
```

---

### （可选）绑定域名 + Nginx 反向代理

如果已有域名，可通过 Nginx 将 80/443 端口代理到 8080，实现无端口号访问：

```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/bizbot
```

```nginx
server {
    listen 80;
    server_name 你的域名;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/bizbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

之后通过 `http://你的域名` 即可直接访问，无需输入端口号。

---

## 🗺️ Roadmap

- [ ] Multi-language UI (English / Chinese)
- [ ] PostgreSQL production deployment guide
- [ ] Docker & Docker Compose support
- [ ] WeChat / Telegram bot integration
- [ ] Scheduled reports & notifications
- [ ] Role-based access control (RBAC)
- [ ] Plugin marketplace

## 🤝 Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## ⭐ Star History

If you find BizBot useful, please consider giving it a star! It helps others discover the project.

---

<p align="center">
  Made with ❤️ for small business owners everywhere
</p>

