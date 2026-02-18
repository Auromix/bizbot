"""测试通道抽象基类"""
import pytest
from datetime import datetime
from typing import Any, Dict, Optional

from interface.base import Channel, Message, MessageHandler, MessageType, Reply


class ConcreteChannel(Channel):
    """具体通道实现用于测试"""

    def __init__(self, name: str, message_handler=None):
        super().__init__(name, message_handler)
        self.startup_called = False
        self.shutdown_called = False
        self.sent_messages = []

    async def startup(self):
        self.startup_called = True
        self.running = True

    async def shutdown(self):
        self.shutdown_called = True
        self.running = False

    async def send(self, session_id: str, reply: Reply):
        self.sent_messages.append((session_id, reply))


class TestMessageType:
    """消息类型测试"""

    def test_message_types(self):
        assert MessageType.TEXT.value == "text"
        assert MessageType.IMAGE.value == "image"
        assert MessageType.FILE.value == "file"


class TestMessage:
    """消息数据类测试"""

    def test_create_message(self):
        msg = Message(
            type=MessageType.TEXT,
            content="你好",
            sender_id="user1",
            sender_name="张三",
            session_id="session1",
        )
        assert msg.type == MessageType.TEXT
        assert msg.content == "你好"
        assert msg.sender_id == "user1"
        assert msg.sender_name == "张三"
        assert msg.session_id == "session1"
        assert msg.channel_name == ""
        assert isinstance(msg.timestamp, datetime)
        assert msg.extra == {}

    def test_message_with_extra(self):
        msg = Message(
            type=MessageType.TEXT,
            content="测试消息",
            sender_id="user1",
            sender_name="张三",
            session_id="session1",
            extra={"msg_id": "12345", "is_group": True},
        )
        assert msg.extra["msg_id"] == "12345"
        assert msg.extra["is_group"] is True


class TestReply:
    """回复数据类测试"""

    def test_create_reply(self):
        reply = Reply(type=MessageType.TEXT, content="收到")
        assert reply.type == MessageType.TEXT
        assert reply.content == "收到"


class TestChannel:
    """通道抽象基类测试"""

    def test_init(self):
        channel = ConcreteChannel("test")
        assert channel.name == "test"
        assert not channel.running

    def test_is_running(self):
        channel = ConcreteChannel("test")
        assert not channel.is_running

        channel.running = True
        assert channel.is_running

    @pytest.mark.asyncio
    async def test_startup(self):
        channel = ConcreteChannel("test")
        await channel.startup()
        assert channel.startup_called
        assert channel.is_running

    @pytest.mark.asyncio
    async def test_shutdown(self):
        channel = ConcreteChannel("test")
        channel.running = True
        await channel.shutdown()
        assert channel.shutdown_called
        assert not channel.is_running

    @pytest.mark.asyncio
    async def test_send(self):
        channel = ConcreteChannel("test")
        reply = Reply(type=MessageType.TEXT, content="回复内容")
        await channel.send("session1", reply)
        assert len(channel.sent_messages) == 1
        assert channel.sent_messages[0][0] == "session1"
        assert channel.sent_messages[0][1].content == "回复内容"

    @pytest.mark.asyncio
    async def test_handle_without_handler(self):
        channel = ConcreteChannel("test")
        msg = Message(
            type=MessageType.TEXT,
            content="测试",
            sender_id="user1",
            sender_name="张三",
            session_id="session1",
        )
        result = await channel.handle(msg)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_with_handler(self):
        async def handler(message: Message) -> Optional[Reply]:
            return Reply(type=MessageType.TEXT, content=f"收到: {message.content}")

        channel = ConcreteChannel("test", message_handler=handler)
        msg = Message(
            type=MessageType.TEXT,
            content="你好",
            sender_id="user1",
            sender_name="张三",
            session_id="session1",
        )
        result = await channel.handle(msg)

        assert result is not None
        assert result.content == "收到: 你好"
        assert msg.channel_name == "test"  # 自动填充通道名

    @pytest.mark.asyncio
    async def test_set_message_handler(self):
        channel = ConcreteChannel("test")

        async def handler(message: Message) -> Optional[Reply]:
            return Reply(type=MessageType.TEXT, content="ok")

        channel.set_message_handler(handler)

        msg = Message(
            type=MessageType.TEXT,
            content="测试",
            sender_id="user1",
            sender_name="张三",
            session_id="session1",
        )
        result = await channel.handle(msg)
        assert result is not None
        assert result.content == "ok"
