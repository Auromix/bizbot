"""通道管理器 - 统一管理多个用户交互通道"""
import asyncio
from typing import Dict, List, Optional

from loguru import logger

from interface.base import Channel, MessageHandler


class ChannelManager:
    """通道管理器

    统一管理多个用户交互通道（Web、终端等），
    提供统一的启动、停止和消息处理接口。

    使用方式：
        ```python
        manager = ChannelManager(message_handler=agent_handler)
        manager.register(WebChannel(port=8080))
        await manager.start_all()
        ```
    """

    def __init__(self, message_handler: Optional[MessageHandler] = None):
        """
        Args:
            message_handler: 全局消息处理回调，会自动设置给所有注册的通道
        """
        self.channels: Dict[str, Channel] = {}
        self._message_handler = message_handler

    def register(self, channel: Channel):
        """注册通道

        如果提供了全局 message_handler 且通道未设置 handler，
        会自动将全局 handler 设置给该通道。

        Args:
            channel: 通道实例
        """
        name = channel.name
        if name in self.channels:
            logger.warning(f"通道 {name} 已注册，将被替换")
        self.channels[name] = channel

        # 自动设置全局 handler
        if self._message_handler and not channel._message_handler:
            channel.set_message_handler(self._message_handler)

        logger.info(f"通道已注册: {name}")

    def unregister(self, name: str):
        """注销通道

        如果通道正在运行，会先停止通道。

        Args:
            name: 通道名称
        """
        if name in self.channels:
            channel = self.channels[name]
            if channel.is_running:
                logger.info(f"通道 {name} 正在运行，先停止...")
                asyncio.ensure_future(channel.shutdown())
            del self.channels[name]
            logger.info(f"通道已注销: {name}")

    def get_channel(self, name: str) -> Optional[Channel]:
        """获取通道

        Args:
            name: 通道名称

        Returns:
            通道实例，如果不存在返回 None
        """
        return self.channels.get(name)

    async def start_all(self):
        """启动所有已注册的通道"""
        for name, channel in self.channels.items():
            try:
                await channel.startup()
                logger.info(f"通道已启动: {name}")
            except Exception as e:
                logger.error(f"通道启动失败 {name}: {e}")

    async def stop_all(self):
        """停止所有已注册的通道"""
        for name, channel in self.channels.items():
            try:
                if channel.is_running:
                    await channel.shutdown()
                    logger.info(f"通道已停止: {name}")
            except Exception as e:
                logger.error(f"通道停止失败 {name}: {e}")

    async def start(self, name: str):
        """启动指定通道

        Args:
            name: 通道名称
        """
        channel = self.get_channel(name)
        if channel:
            await channel.startup()
        else:
            logger.warning(f"通道不存在: {name}")

    async def stop(self, name: str):
        """停止指定通道

        Args:
            name: 通道名称
        """
        channel = self.get_channel(name)
        if channel:
            await channel.shutdown()
        else:
            logger.warning(f"通道不存在: {name}")

    def list_channels(self) -> List[str]:
        """列出所有已注册的通道名称"""
        return list(self.channels.keys())

    def get_running_channels(self) -> List[str]:
        """获取所有正在运行的通道名称"""
        return [name for name, ch in self.channels.items() if ch.is_running]
