# Agent 模块测试

本目录包含 Agent 模块的完整测试套件，覆盖了所有核心功能。

## 测试文件结构

- `conftest.py`: 共享的测试 fixtures 和配置
- `test_registry.py`: 测试 FunctionRegistry（函数注册表）
- `test_executor.py`: 测试 ToolExecutor（工具执行器）
- `test_discovery.py`: 测试函数自动发现和注册机制
- `test_agent.py`: 测试 Agent 核心类
- `test_providers.py`: 测试 LLM Provider 实现（支持 mock 和真实 API）

## 运行测试

### 基本测试（使用 Mock）

默认情况下，所有测试都使用 Mock 对象，不需要真实的 API Key：

```bash
# 运行所有 agent 测试
pytest tests/agent/

# 运行特定测试文件
pytest tests/agent/test_registry.py

# 运行特定测试类
pytest tests/agent/test_registry.py::TestFunctionRegistry

# 运行特定测试方法
pytest tests/agent/test_registry.py::TestFunctionRegistry::test_register_simple_function
```

### 真实 API 测试

如果需要使用真实的 API 进行测试，可以通过环境变量配置：

#### OpenAI Provider

```bash
export AGENT_TEST_USE_REAL_API=true
export AGENT_TEST_PROVIDER_TYPE=openai
export AGENT_TEST_API_KEY=sk-your-api-key-here
export AGENT_TEST_MODEL=gpt-4o-mini

pytest tests/agent/test_providers.py::TestOpenAIProvider::test_chat_real_api
```

#### Claude Provider

```bash
export AGENT_TEST_USE_REAL_API=true
export AGENT_TEST_PROVIDER_TYPE=claude
export AGENT_TEST_API_KEY=sk-ant-your-api-key-here
export AGENT_TEST_MODEL=claude-sonnet-4-20250514

pytest tests/agent/test_providers.py::TestClaudeProvider::test_chat_real_api
```

#### Open Source Provider

```bash
export AGENT_TEST_USE_REAL_API=true
export AGENT_TEST_PROVIDER_TYPE=open_source
export AGENT_TEST_BASE_URL=http://localhost:8000/v1
export AGENT_TEST_MODEL=qwen
# 可选：如果需要 API Key
export AGENT_TEST_API_KEY=your-api-key

pytest tests/agent/test_providers.py::TestOpenSourceProvider::test_chat_real_api
```

## 环境变量说明

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `AGENT_TEST_USE_REAL_API` | 是否使用真实 API | `false` | 否 |
| `AGENT_TEST_PROVIDER_TYPE` | Provider 类型（openai/claude/open_source） | `openai` | 是（真实 API 时） |
| `AGENT_TEST_API_KEY` | API Key | 空 | 是（真实 API 时） |
| `AGENT_TEST_MODEL` | 模型名称 | `gpt-4o-mini` | 否 |
| `AGENT_TEST_BASE_URL` | 基础 URL（开源模型需要） | 空 | 是（open_source 时） |

## 测试覆盖范围

### FunctionRegistry 测试
- ✅ 函数注册（基本、自定义参数、覆盖）
- ✅ 参数自动推断（基本类型、可选参数、Union 类型）
- ✅ 函数查询和列表生成
- ✅ 异步函数支持

### ToolExecutor 测试
- ✅ 执行同步函数
- ✅ 执行异步函数
- ✅ 错误处理
- ✅ 结果格式化（None、字符串、字典、列表、嵌套结构）

### Discovery 测试
- ✅ `@agent_callable` 装饰器
- ✅ `register_instance_methods`（实例方法注册）
- ✅ `register_module_functions`（模块函数注册）
- ✅ `register_class_methods`（类方法注册）
- ✅ `auto_discover_and_register`（自动发现）

### Agent 测试
- ✅ 初始化和配置
- ✅ 简单对话
- ✅ 函数调用和多轮迭代
- ✅ 最大迭代次数限制
- ✅ 错误处理
- ✅ 消息解析（JSON、Markdown code block）
- ✅ 历史记录管理

### Provider 测试
- ✅ OpenAI Provider（Mock 和真实 API）
- ✅ Claude Provider（Mock 和真实 API）
- ✅ Open Source Provider（Mock 和真实 API）
- ✅ 函数调用支持
- ✅ 错误处理

## 注意事项

1. **Mock 测试是默认的**：所有测试默认使用 Mock，不会产生 API 费用
2. **真实 API 测试是可选的**：只有明确设置环境变量时才会进行真实 API 调用
3. **真实 API 测试可能产生费用**：使用真实 API 时请注意费用
4. **网络要求**：真实 API 测试需要网络连接
5. **API Key 安全**：
   - ⚠️ **重要**：永远不要将真实的 API Key 硬编码在代码中
   - 所有 API Key 必须通过环境变量提供（使用 `export` 或 `.env` 文件）
   - 不要将包含真实密钥的 `.env` 文件提交到版本控制系统
   - 确保 `.gitignore` 中包含 `.env`
   - 如果密钥已泄露，请立即在服务提供商处撤销并重新生成

## 示例：运行完整测试套件

```bash
# 1. 运行所有 Mock 测试（推荐，快速且免费）
pytest tests/agent/ -v

# 2. 运行特定模块的测试
pytest tests/agent/test_registry.py -v

# 3. 运行真实 API 测试（需要配置环境变量）
export AGENT_TEST_USE_REAL_API=true
export AGENT_TEST_PROVIDER_TYPE=openai
export AGENT_TEST_API_KEY=sk-...
pytest tests/agent/test_providers.py::TestOpenAIProvider::test_chat_real_api -v

# 4. 生成测试覆盖率报告
pytest tests/agent/ --cov=agent --cov-report=html
```

## 故障排除

### 问题：真实 API 测试失败

1. 检查环境变量是否正确设置
2. 检查 API Key 是否有效
3. 检查网络连接
4. 检查模型名称是否正确

### 问题：Mock 测试失败

1. 检查测试代码是否正确
2. 检查 Mock 对象配置是否正确
3. 查看详细的错误信息

### 问题：导入错误

1. 确保在项目根目录运行测试
2. 确保所有依赖已安装：`pip install -r requirements.txt`
3. 检查 Python 路径配置

