#!/usr/bin/env python3
"""商业管理平台 - Web 应用入口

启动 Web 管理平台，提供：
1. AI 聊天助手（与 Agent 对话）
2. 数据库可视化仪表盘

使用方式：
    python app.py

    # 指定端口
    python app.py --port 8080

    # 指定数据库
    python app.py --db sqlite:///data/store.db

环境变量（在 .env 文件中配置，运行 python scripts/setup_env.py 生成）：
    MINIMAX_API_KEY   MiniMax API Key（必填）
    MINIMAX_MODEL     MiniMax 模型名称（默认 MiniMax-M2.5）
    DATABASE_URL      数据库连接地址
    WEB_PORT          Web 端口（默认 8080）
    WEB_USERNAME      登录用户名（默认 admin）
    WEB_PASSWORD      登录密码（默认 admin123）
    WEB_SECRET_KEY    JWT 密钥
"""
import argparse
import asyncio
import os
import signal
import sys

from loguru import logger


async def create_agent():
    """创建 Agent 实例"""
    from config.settings import settings
    from agent import Agent, create_provider, FunctionRegistry
    from config.prompts import get_system_prompt

    # 默认使用 MiniMax
    if not settings.minimax_api_key:
        logger.warning("未配置 MINIMAX_API_KEY，Agent 将不可用")
        return None

    try:
        provider = create_provider(
            "minimax",
            api_key=settings.minimax_api_key,
            model=settings.minimax_model,
            base_url=settings.minimax_base_url,
        )
        logger.info(f"LLM Provider 创建成功: minimax ({settings.minimax_model})")
    except Exception as e:
        logger.warning(f"创建 LLM Provider 失败: {e}，将使用无 Agent 模式")
        return None

    # 创建函数注册表
    registry = FunctionRegistry()

    # 获取系统提示词
    system_prompt = get_system_prompt()

    # 创建 Agent
    agent = Agent(provider, registry, system_prompt=system_prompt)
    return agent


async def _cleanup(web, db):
    """统一资源清理函数。

    确保 Web 服务器和数据库连接被正确关闭，释放端口和文件句柄。
    """
    logger.info("正在清理资源...")

    # 1. 停止 Web 服务器（释放端口）
    if web is not None:
        try:
            await web.shutdown()
        except Exception as e:
            logger.warning(f"停止 Web 服务器时出错: {e}")

    # 2. 关闭数据库连接（释放连接池）
    if db is not None:
        try:
            db.close()
        except Exception as e:
            logger.warning(f"关闭数据库连接时出错: {e}")

    logger.info("服务已停止")


async def main():
    parser = argparse.ArgumentParser(description="商业管理平台 Web 应用")
    parser.add_argument("--host", default=os.getenv("WEB_HOST", "0.0.0.0"),
                        help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.getenv("WEB_PORT", "8080")),
                        help="监听端口 (默认: 8080)")
    parser.add_argument("--db", default=os.getenv("DATABASE_URL", None),
                        help="数据库连接 URL")
    parser.add_argument("--username", default=os.getenv("WEB_USERNAME", "admin"),
                        help="登录用户名 (默认: admin)")
    parser.add_argument("--password", default=os.getenv("WEB_PASSWORD", "admin123"),
                        help="登录密码 (默认: admin123)")
    parser.add_argument("--no-agent", action="store_true",
                        help="不启动 Agent（仅数据库可视化）")
    args = parser.parse_args()

    # 用于 finally 清理的引用
    web = None
    db = None

    try:
        # 初始化数据库
        from database import DatabaseManager
        db = DatabaseManager(args.db)
        db.create_tables()
        logger.info(f"数据库已连接: {db.database_url}")

        # 创建 Agent
        agent = None
        if not args.no_agent:
            try:
                agent = await create_agent()
                if agent:
                    logger.info("Agent 已就绪")
            except Exception as e:
                logger.warning(f"Agent 初始化失败: {e}")

        # 消息处理回调
        from interface.base import Message, MessageType, Reply

        async def message_handler(message: Message):
            """处理用户消息"""
            if agent:
                try:
                    response = await agent.chat(message.content)
                    return Reply(
                        type=MessageType.TEXT,
                        content=response.get("content", "抱歉，我无法处理你的请求。"),
                    )
                except Exception as e:
                    logger.error(f"Agent 处理出错: {e}")
                    return Reply(
                        type=MessageType.TEXT,
                        content=f"处理出错: {str(e)}",
                    )
            else:
                return Reply(
                    type=MessageType.TEXT,
                    content="Agent 未配置。请在 .env 中设置 MINIMAX_API_KEY 后重启。\n\n运行 python scripts/setup_env.py 可快速生成配置。\n\n当前仅支持数据库可视化功能，请在左侧导航栏查看数据。",
                )

        # 创建 Web 通道
        from interface.web.channel import WebChannel
        from config.settings import settings

        web = WebChannel(
            message_handler=message_handler,
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            secret_key=settings.web_secret_key,
            db_manager=db,
        )

        # 启动
        await web.startup()

        print()
        print("=" * 60)
        print(f"  商业管理平台已启动!")
        print(f"  访问地址: http://localhost:{args.port}")
        print(f"  外网访问: http://YOUR_IP:{args.port}")
        print(f"  用户名: {args.username}")
        print(f"  密码: {args.password}")
        print(f"  数据库: {db.database_url}")
        print(f"  Agent: {'已启用' if agent else '未启用（请配置 MINIMAX_API_KEY）'}")
        print("=" * 60)
        print("  按 Ctrl+C 停止服务")
        print()

        # 设置信号处理 —— 使用 asyncio 的信号处理确保事件循环能正确响应
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()
        _shutdown_requested = False

        def signal_handler(signum):
            """处理退出信号"""
            nonlocal _shutdown_requested
            if _shutdown_requested:
                # 第二次收到信号，强制退出
                logger.warning("再次收到退出信号，强制退出...")
                # 取消所有待处理的任务以快速退出
                for task in asyncio.all_tasks(loop):
                    task.cancel()
                return
            _shutdown_requested = True
            logger.info(f"收到信号 {signum}，正在关闭服务...")
            shutdown_event.set()

        # 使用 loop.add_signal_handler（asyncio 原生方式，确保事件循环能正确唤醒）
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler, sig)

        # 保持运行，直到收到退出信号
        await shutdown_event.wait()

    except asyncio.CancelledError:
        logger.info("任务被取消，正在清理...")
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")
    finally:
        await _cleanup(web, db)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        print("\n已停止。")
