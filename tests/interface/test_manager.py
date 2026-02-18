"""测试通道管理器"""
import pytest
from typing import Optional

from interface.base import Channel, Message, MessageType, Reply
from interface.manager import ChannelManager


class MockChannel(Channel):
    """Mock 通道实现"""

    def __init__(self, name: str, message_handler=None):
        super().__init__(name, message_handler)
        self.startup_called = False
        self.shutdown_called = False

    async def startup(self):
        self.startup_called = True
        self.running = True

    async def shutdown(self):
        self.shutdown_called = True
        self.running = False

    async def send(self, session_id: str, reply: Reply):
        pass


class TestChannelManager:
    """通道管理器测试"""

    def test_init(self):
        manager = ChannelManager()
        assert manager.channels == {}

    def test_register(self):
        manager = ChannelManager()
        channel = MockChannel("test")

        manager.register(channel)

        assert "test" in manager.channels
        assert manager.channels["test"] == channel

    def test_register_duplicate(self):
        manager = ChannelManager()
        channel1 = MockChannel("test")
        channel2 = MockChannel("test")

        manager.register(channel1)
        manager.register(channel2)

        assert manager.channels["test"] == channel2

    def test_register_with_global_handler(self):
        async def handler(msg):
            return None

        manager = ChannelManager(message_handler=handler)
        channel = MockChannel("test")

        manager.register(channel)

        assert channel._message_handler == handler

    def test_get_channel(self):
        manager = ChannelManager()
        channel = MockChannel("test")

        manager.register(channel)
        result = manager.get_channel("test")

        assert result == channel

    def test_get_channel_not_found(self):
        manager = ChannelManager()
        result = manager.get_channel("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_start_all(self):
        manager = ChannelManager()
        channel1 = MockChannel("test1")
        channel2 = MockChannel("test2")

        manager.register(channel1)
        manager.register(channel2)
        await manager.start_all()

        assert channel1.startup_called
        assert channel2.startup_called
        assert channel1.is_running
        assert channel2.is_running

    @pytest.mark.asyncio
    async def test_start_all_with_exception(self):
        manager = ChannelManager()
        channel1 = MockChannel("test1")
        channel2 = MockChannel("test2")

        async def failing_startup():
            raise Exception("Startup failed")

        channel2.startup = failing_startup

        manager.register(channel1)
        manager.register(channel2)
        await manager.start_all()

        # channel1 应该成功启动
        assert channel1.startup_called
        assert channel1.is_running

    @pytest.mark.asyncio
    async def test_stop_all(self):
        manager = ChannelManager()
        channel1 = MockChannel("test1")
        channel2 = MockChannel("test2")

        channel1.running = True
        channel2.running = True

        manager.register(channel1)
        manager.register(channel2)
        await manager.stop_all()

        assert channel1.shutdown_called
        assert channel2.shutdown_called
        assert not channel1.is_running
        assert not channel2.is_running

    @pytest.mark.asyncio
    async def test_stop_all_not_running(self):
        manager = ChannelManager()
        channel1 = MockChannel("test1")
        channel2 = MockChannel("test2")

        channel1.running = False
        channel2.running = True

        manager.register(channel1)
        manager.register(channel2)
        await manager.stop_all()

        assert not channel1.shutdown_called
        assert channel2.shutdown_called

    @pytest.mark.asyncio
    async def test_start_specific(self):
        manager = ChannelManager()
        channel = MockChannel("test")

        manager.register(channel)
        await manager.start("test")

        assert channel.startup_called
        assert channel.is_running

    @pytest.mark.asyncio
    async def test_start_not_found(self):
        manager = ChannelManager()
        # 不应该抛出异常
        await manager.start("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_specific(self):
        manager = ChannelManager()
        channel = MockChannel("test")
        channel.running = True

        manager.register(channel)
        await manager.stop("test")

        assert channel.shutdown_called
        assert not channel.is_running

    @pytest.mark.asyncio
    async def test_stop_not_found(self):
        manager = ChannelManager()
        # 不应该抛出异常
        await manager.stop("nonexistent")

    def test_list_channels(self):
        manager = ChannelManager()
        channel1 = MockChannel("test1")
        channel2 = MockChannel("test2")

        manager.register(channel1)
        manager.register(channel2)

        channels = manager.list_channels()
        assert set(channels) == {"test1", "test2"}

    def test_get_running_channels(self):
        manager = ChannelManager()
        channel1 = MockChannel("test1")
        channel2 = MockChannel("test2")
        channel3 = MockChannel("test3")

        channel1.running = True
        channel2.running = False
        channel3.running = True

        manager.register(channel1)
        manager.register(channel2)
        manager.register(channel3)

        running = manager.get_running_channels()
        assert set(running) == {"test1", "test3"}
