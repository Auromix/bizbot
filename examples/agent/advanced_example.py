"""高级用法示例 - Agent 高级特性

本示例展示 Agent 的高级用法，包括：
1. 消息解析（从非结构化文本提取结构化数据）
2. 自定义系统提示词
3. 控制迭代次数
4. 错误处理
5. 与数据库模块集成

运行方式：
    python examples/agent/advanced_example.py
"""
import sys
import os
import asyncio
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent import Agent, create_provider, FunctionRegistry
from agent.functions.discovery import agent_callable, register_instance_methods
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)


async def example_parse_message():
    """示例：消息解析（从非结构化文本提取结构化数据）"""
    logger.info("=" * 60)
    logger.info("示例 1: 消息解析")
    logger.info("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("未设置 OPENAI_API_KEY 环境变量，跳过此示例")
        return
    
    # 1.1 创建 Agent
    logger.info("\n1️⃣ 创建 Agent")
    logger.info("-" * 60)
    provider = create_provider("openai", api_key=api_key, model="gpt-4o-mini")
    agent = Agent(
        provider,
        system_prompt="你是一个数据提取助手，擅长从非结构化文本中提取结构化数据。"
    )
    logger.info("✅ Agent 已创建")
    
    # 1.2 解析消息
    logger.info("\n2️⃣ 解析非结构化消息")
    logger.info("-" * 60)
    messages = [
        ("前台", "2024-01-28 10:00:00", "张三 头疗 198元"),
        ("前台", "2024-01-28 11:00:00", "李四 剪发 50元"),
        ("前台", "2024-01-28 12:00:00", "王五 染发 300元"),
    ]
    
    for sender, timestamp, content in messages:
        logger.info(f"\n原始消息: {content}")
        records = await agent.parse_message(sender, timestamp, content)
        logger.info(f"解析结果: {records}")
        for record in records:
            logger.info(f"  - 类型: {record.get('type')}, "
                       f"顾客: {record.get('customer_name')}, "
                       f"服务: {record.get('service_or_product')}, "
                       f"金额: {record.get('amount')}")
    
    logger.info("")


async def example_custom_system_prompt():
    """示例：自定义系统提示词"""
    logger.info("=" * 60)
    logger.info("示例 2: 自定义系统提示词")
    logger.info("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("未设置 OPENAI_API_KEY 环境变量，跳过此示例")
        return
    
    # 2.1 创建不同角色的 Agent
    logger.info("\n1️⃣ 创建不同角色的 Agent")
    logger.info("-" * 60)
    provider = create_provider("openai", api_key=api_key, model="gpt-4o-mini")
    
    # 数学助手
    math_agent = Agent(
        provider,
        system_prompt="你是一个专业的数学助手，擅长解决数学问题。"
    )
    
    # 编程助手
    coding_agent = Agent(
        provider,
        system_prompt="你是一个经验丰富的编程助手，擅长解释代码和技术概念。"
    )
    
    # 客服助手
    service_agent = Agent(
        provider,
        system_prompt="你是一个友好的客服助手，擅长用简洁明了的方式回答客户问题。"
    )
    
    logger.info("✅ 已创建 3 个不同角色的 Agent")
    
    # 2.2 测试不同角色的回复
    logger.info("\n2️⃣ 测试不同角色的回复")
    logger.info("-" * 60)
    
    question = "什么是 Python？"
    logger.info(f"问题: {question}")
    
    logger.info("\n数学助手的回复:")
    response = await math_agent.chat(question)
    logger.info(f"  {response['content'][:150]}...")
    
    logger.info("\n编程助手的回复:")
    response = await coding_agent.chat(question)
    logger.info(f"  {response['content'][:150]}...")
    
    logger.info("\n客服助手的回复:")
    response = await service_agent.chat(question)
    logger.info(f"  {response['content'][:150]}...")
    
    logger.info("")


async def example_control_iterations():
    """示例：控制迭代次数"""
    logger.info("=" * 60)
    logger.info("示例 3: 控制迭代次数")
    logger.info("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("未设置 OPENAI_API_KEY 环境变量，跳过此示例")
        return
    
    # 3.1 创建带函数调用的 Agent
    logger.info("\n1️⃣ 创建带函数调用的 Agent")
    logger.info("-" * 60)
    provider = create_provider("openai", api_key=api_key, model="gpt-4o-mini")
    registry = FunctionRegistry()
    
    @agent_callable(description="获取数字")
    def get_number(n: int) -> Dict[str, Any]:
        return {"number": n}
    
    registry.register("get_number", "获取数字", get_number)
    
    agent = Agent(provider, registry, system_prompt="你是一个助手。")
    logger.info("✅ Agent 已创建")
    
    # 3.2 测试不同的迭代次数限制
    logger.info("\n2️⃣ 测试不同的迭代次数限制")
    logger.info("-" * 60)
    
    for max_iter in [1, 3, 5]:
        logger.info(f"\n最大迭代次数: {max_iter}")
        response = await agent.chat(
            "获取数字1，然后获取数字2，然后获取数字3",
            max_iterations=max_iter
        )
        logger.info(f"  实际迭代次数: {response['iterations']}")
        logger.info(f"  函数调用次数: {len(response['function_calls'])}")
        agent.clear_history()  # 清空历史以便下次测试
    
    logger.info("")


async def example_error_handling():
    """示例：错误处理"""
    logger.info("=" * 60)
    logger.info("示例 4: 错误处理")
    logger.info("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("未设置 OPENAI_API_KEY 环境变量，跳过此示例")
        return
    
    # 4.1 创建带错误函数的 Agent
    logger.info("\n1️⃣ 创建带错误函数的 Agent")
    logger.info("-" * 60)
    provider = create_provider("openai", api_key=api_key, model="gpt-4o-mini")
    registry = FunctionRegistry()
    
    @agent_callable(description="可能出错的函数")
    def risky_function(should_fail: bool = False) -> Dict[str, Any]:
        if should_fail:
            raise ValueError("模拟错误")
        return {"status": "success"}
    
    registry.register("risky_function", "可能出错的函数", risky_function)
    
    agent = Agent(
        provider,
        registry,
        system_prompt="你是一个助手，当函数出错时，请尝试其他方法或向用户说明。"
    )
    logger.info("✅ Agent 已创建")
    
    # 4.2 测试错误处理
    logger.info("\n2️⃣ 测试错误处理")
    logger.info("-" * 60)
    
    logger.info("用户: 调用可能出错的函数，参数 should_fail=True")
    response = await agent.chat("调用可能出错的函数，参数 should_fail=True")
    logger.info(f"助手: {response['content']}")
    logger.info(f"函数调用次数: {len(response['function_calls'])}")
    
    # 查看是否有错误消息
    tool_messages = [
        msg for msg in agent.conversation_history
        if msg.role == "tool" and "错误" in msg.content
    ]
    if tool_messages:
        logger.info(f"检测到错误消息: {tool_messages[0].content}")
    
    logger.info("")


async def example_database_integration():
    """示例：与数据库模块集成"""
    logger.info("=" * 60)
    logger.info("示例 5: 与数据库模块集成")
    logger.info("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("未设置 OPENAI_API_KEY 环境变量，跳过此示例")
        return
    
    try:
        from database import DatabaseManager
    except ImportError:
        logger.warning("数据库模块未安装，跳过此示例")
        return
    
    # 5.1 创建数据库管理器
    logger.info("\n1️⃣ 创建数据库管理器")
    logger.info("-" * 60)
    DATA_DIR = PROJECT_ROOT / "data"
    DATA_DIR.mkdir(exist_ok=True)
    DB_PATH = DATA_DIR / "advanced_example.db"
    
    db = DatabaseManager(f"sqlite:///{DB_PATH}")
    db.create_tables()
    logger.info("✅ 数据库管理器已创建")
    
    # 5.2 注册数据库方法到 Agent
    logger.info("\n2️⃣ 注册数据库方法到 Agent")
    logger.info("-" * 60)
    provider = create_provider("openai", api_key=api_key, model="gpt-4o-mini")
    registry = FunctionRegistry()
    
    # 注册数据库方法（使用前缀避免命名冲突）
    register_instance_methods(registry, db, prefix="db_")
    
    functions = registry.list_functions()
    logger.info(f"✅ 已注册 {len(functions)} 个数据库函数")
    logger.info("   示例函数:")
    for func in functions[:5]:  # 只显示前5个
        logger.info(f"     - {func['name']}")
    
    # 5.3 创建 Agent 并测试
    logger.info("\n3️⃣ 创建 Agent 并测试数据库查询")
    logger.info("-" * 60)
    agent = Agent(
        provider,
        registry,
        system_prompt="你是一个数据库查询助手，可以使用数据库函数查询信息。"
    )
    
    # 先创建一些测试数据
    msg_id = db.save_raw_message({
        "msg_id": "test-001",
        "sender_nickname": "测试",
        "content": "张三 头疗 198元",
        "timestamp": "2024-01-28 10:00:00",
        "is_business": True,
    })
    
    db.save_service_record({
        "customer_name": "张三",
        "service_or_product": "头疗",
        "date": "2024-01-28",
        "amount": 198
    }, msg_id)
    
    logger.info("用户: 查询2024-01-28的所有记录")
    response = await agent.chat("查询2024-01-28的所有记录")
    logger.info(f"助手: {response['content'][:200]}...")
    logger.info(f"函数调用次数: {len(response['function_calls'])}")
    
    logger.info("")


async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Agent 模块 - 高级用法示例")
    logger.info("=" * 60)
    logger.info("")
    logger.info("提示: 请确保设置了 OPENAI_API_KEY 环境变量")
    logger.info("")
    
    try:
        # 运行各个示例
        await example_parse_message()
        await example_custom_system_prompt()
        await example_control_iterations()
        await example_error_handling()
        await example_database_integration()
        
        logger.info("=" * 60)
        logger.info("✅ 高级用法示例完成！")
        logger.info("=" * 60)
        logger.info("")
        logger.info("💡 关键要点:")
        logger.info("   1. parse_message() 可以从非结构化文本提取结构化数据")
        logger.info("   2. 系统提示词可以控制 Agent 的行为和角色")
        logger.info("   3. max_iterations 可以控制函数调用的迭代次数")
        logger.info("   4. Agent 会自动处理函数执行错误")
        logger.info("   5. 可以与数据库模块集成，实现业务功能")
        
    except Exception as e:
        logger.error(f"运行示例时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

