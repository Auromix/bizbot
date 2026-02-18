"""用户接口模块 - 统一的消息通道管理

提供多种用户交互通道，支持通过不同渠道与 Agent 对话：

通道类型：
- TerminalChannel: 终端命令行交互（开发调试用）
- WebChannel: Web 管理平台（聊天 + 数据库可视化）

核心组件：
- Channel: 通道抽象基类
- ChannelManager: 通道管理器（统一管理多个通道）
- Message / Reply: 统一消息格式

架构设计：
    用户 ──→ 通道 ──→ Message ──→ Agent ──→ Reply ──→ 通道 ──→ 用户
    (Web/终端)                   (处理逻辑)              (回复消息)

使用示例：
    ```python
    from interface import ChannelManager, WebChannel

    async def agent_handler(message):
        response = await agent.chat(message.content)
        return Reply(type=MessageType.TEXT, content=response["content"])

    manager = ChannelManager(message_handler=agent_handler)
    manager.register(WebChannel(port=8080))
    await manager.start_all()
    ```
"""
from interface.base import Channel, Message, MessageHandler, MessageType, Reply
from interface.manager import ChannelManager

# 终端通道
from interface.terminal.channel import TerminalChannel

# Web 通道
try:
    from interface.web.channel import WebChannel
    _has_web = True
except ImportError:
    _has_web = False
    WebChannel = None

__all__ = [
    # 核心
    "Channel",
    "ChannelManager",
    "Message",
    "MessageType",
    "Reply",
    "MessageHandler",
    # 通道
    "TerminalChannel",
]

if _has_web:
    __all__.append("WebChannel")
