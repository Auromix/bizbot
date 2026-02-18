"""接口通道抽象层 - 统一的消息通道协议

定义 Channel（通道）基类和消息数据结构。
每个 Channel 代表一个用户交互通道（Web 聊天、终端等）。

核心概念：
- Message: 统一的入站消息格式（用户 → 系统）
- Reply: 统一的出站回复格式（系统 → 用户）
- Channel: 通道抽象基类，负责消息收发和格式转换
- MessageHandler: 消息处理回调类型（通常由 Agent 实现）

设计原则：
- 通道只负责消息的收发和格式转换
- 业务逻辑完全由 MessageHandler（Agent）处理
- 通道之间互相独立，可以同时运行多个通道
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"       # 文本消息
    IMAGE = "image"     # 图片消息（content 为图片文件路径或 URL）
    FILE = "file"       # 文件消息（content 为文件路径或 URL）


@dataclass
class Message:
    """统一入站消息格式

    所有通道收到的消息都转换为此格式后交给 MessageHandler 处理。

    Attributes:
        type: 消息类型
        content: 消息内容（文本内容，或图片/文件的本地路径/URL）
        sender_id: 发送者唯一标识
        sender_name: 发送者显示名称
        session_id: 会话标识（用于关联多轮对话上下文）
        channel_name: 来源通道名称（由 Channel 自动填充）
        timestamp: 消息时间戳
        extra: 通道特定的附加数据
    """
    type: MessageType
    content: str
    sender_id: str
    sender_name: str
    session_id: str
    channel_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Reply:
    """统一出站回复格式

    MessageHandler 处理完消息后返回此格式，由 Channel 转换为通道特定格式发送。

    Attributes:
        type: 回复类型
        content: 回复内容（文本内容或媒体文件路径）
    """
    type: MessageType
    content: str


# 消息处理回调类型：接收 Message，返回 Optional[Reply]
MessageHandler = Callable[[Message], Awaitable[Optional[Reply]]]


class Channel(ABC):
    """通道抽象基类

    所有用户交互通道（Web 聊天、终端等）都应实现此接口。

    Channel 的职责：
    1. 接收来自用户的原始消息，转换为统一的 Message 格式
    2. 调用 message_handler 处理消息，获取 Reply
    3. 将 Reply 转换为通道特定格式并发送回给用户

    使用方式：
        ```python
        async def my_handler(message: Message) -> Optional[Reply]:
            # 通常由 Agent 实现
            response = await agent.chat(message.content)
            return Reply(type=MessageType.TEXT, content=response["content"])

        channel = WebChannel(message_handler=my_handler, port=8080)
        await channel.startup()
        ```
    """

    def __init__(self, name: str, message_handler: Optional[MessageHandler] = None):
        """
        Args:
            name: 通道名称标识（如 'web', 'terminal'）
            message_handler: 消息处理回调，通常由 Agent 提供
        """
        self.name = name
        self.running = False
        self._message_handler = message_handler

    def set_message_handler(self, handler: MessageHandler):
        """设置消息处理回调

        Args:
            handler: 异步回调函数，接收 Message 返回 Optional[Reply]
        """
        self._message_handler = handler

    @abstractmethod
    async def startup(self):
        """启动通道

        子类实现具体的启动逻辑（如启动 HTTP 服务器、连接 WebSocket 等）。
        启动成功后应设置 self.running = True。
        """
        pass

    @abstractmethod
    async def shutdown(self):
        """关闭通道

        子类实现具体的关闭逻辑（如停止服务器、断开连接等）。
        关闭后应设置 self.running = False。
        """
        pass

    @abstractmethod
    async def send(self, session_id: str, reply: Reply):
        """发送回复到指定会话

        Args:
            session_id: 目标会话标识
            reply: 回复内容
        """
        pass

    async def handle(self, message: Message) -> Optional[Reply]:
        """处理收到的消息

        统一的消息处理入口。将消息交给 message_handler 处理并返回回复。
        子类通常不需要重写此方法，除非需要添加通道特定的预/后处理逻辑。

        Args:
            message: 统一格式的消息

        Returns:
            处理后的回复，如果无需回复则返回 None
        """
        if not self._message_handler:
            return None

        # 自动填充通道名称
        message.channel_name = self.name
        return await self._message_handler(message)

    @property
    def is_running(self) -> bool:
        """检查通道是否正在运行"""
        return self.running
