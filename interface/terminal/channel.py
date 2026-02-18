"""终端通道 - 用于开发调试的命令行交互

提供基于终端的文本交互界面，方便开发和调试 Agent 对话。

使用方式：
    ```python
    channel = TerminalChannel(message_handler=agent_handler)
    await channel.startup()
    await channel.run_loop()  # 进入交互循环
    ```
"""
import asyncio
import sys
from datetime import datetime
from typing import Optional

from loguru import logger

from interface.base import Channel, Message, MessageHandler, MessageType, Reply


class TerminalChannel(Channel):
    """终端交互通道

    在命令行中与 Agent 进行文字对话，主要用于开发调试。

    特性：
    - 简单的 stdin/stdout 交互
    - 支持退出命令（quit/exit/q）
    - 支持清屏命令（clear/cls）
    - 自动会话管理
    """

    def __init__(
        self,
        message_handler: Optional[MessageHandler] = None,
        user_name: str = "用户",
        bot_name: str = "助手",
    ):
        """
        Args:
            message_handler: 消息处理回调
            user_name: 用户显示名称
            bot_name: 助手显示名称
        """
        super().__init__("terminal", message_handler)
        self.user_name = user_name
        self.bot_name = bot_name
        self.session_id = "terminal_session"

    async def startup(self):
        """启动终端通道"""
        self.running = True
        logger.info("终端通道已启动")

    async def shutdown(self):
        """关闭终端通道"""
        self.running = False
        logger.info("终端通道已关闭")

    async def send(self, session_id: str, reply: Reply):
        """发送回复到终端

        Args:
            session_id: 会话标识（终端通道忽略此参数）
            reply: 回复内容
        """
        if reply.type == MessageType.TEXT:
            print(f"\n🤖 {self.bot_name}: {reply.content}\n")
        else:
            print(f"\n🤖 {self.bot_name}: [{reply.type.value}] {reply.content}\n")

    async def run_loop(self):
        """运行交互循环

        进入终端交互模式，持续读取用户输入并处理。
        输入 quit/exit/q 退出。
        """
        if not self.running:
            await self.startup()

        print("=" * 60)
        print(f"  💬 商业管理助手 - 终端模式")
        print(f"  输入消息与助手对话，输入 quit 退出")
        print("=" * 60)
        print()

        loop = asyncio.get_event_loop()

        while self.running:
            try:
                # 在线程中读取输入（避免阻塞事件循环）
                user_input = await loop.run_in_executor(
                    None, lambda: input(f"👤 {self.user_name}: ")
                )
                user_input = user_input.strip()

                if not user_input:
                    continue

                # 检查退出命令
                if user_input.lower() in ("quit", "exit", "q", "退出"):
                    print("\n👋 再见！")
                    await self.shutdown()
                    break

                # 检查清屏命令
                if user_input.lower() in ("clear", "cls", "清屏"):
                    print("\033[2J\033[H")  # ANSI 清屏
                    continue

                # 构建消息
                message = Message(
                    type=MessageType.TEXT,
                    content=user_input,
                    sender_id="terminal_user",
                    sender_name=self.user_name,
                    session_id=self.session_id,
                    timestamp=datetime.now(),
                )

                # 处理消息
                print(f"\n⏳ 正在处理...")
                reply = await self.handle(message)

                if reply:
                    await self.send(self.session_id, reply)
                else:
                    print(f"\n🤖 {self.bot_name}: (无回复)\n")

            except EOFError:
                print("\n👋 再见！")
                await self.shutdown()
                break
            except KeyboardInterrupt:
                print("\n👋 再见！")
                await self.shutdown()
                break
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
                print(f"\n❌ 出错了: {e}\n")

