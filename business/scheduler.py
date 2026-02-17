"""定时任务调度器 - 通用的任务调度框架

具体的业务任务逻辑在 business/scheduler_tasks.py 中
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Optional, List
from loguru import logger
from config.settings import settings
import asyncio


class Scheduler:
    """定时任务调度器
    
    通用的任务调度框架，不包含具体的业务逻辑
    业务逻辑通过回调函数注入，保持 core 层的独立性
    """
    
    def __init__(self):
        """初始化调度器"""
        # 使用默认事件循环或创建新的事件循环
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        self.scheduler = AsyncIOScheduler(event_loop=loop)
    
    def add_daily_task(
        self,
        task_func: Callable,
        hour: int = 21,
        minute: int = 0,
        task_id: str = 'daily_task',
        task_name: str = '每日任务'
    ):
        """添加每日定时任务
        
        Args:
            task_func: 任务函数（async 函数）
            hour: 小时 (0-23)
            minute: 分钟 (0-59)
            task_id: 任务ID
            task_name: 任务名称
        """
        self.scheduler.add_job(
            task_func,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=task_id,
            name=task_name,
            replace_existing=True
        )
        logger.info(f"Added daily task '{task_name}' at {hour:02d}:{minute:02d}")
    
    def start(self):
        """启动调度器"""
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    def remove_job(self, job_id: str):
        """移除任务
        
        Args:
            job_id: 任务ID
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job {job_id} removed")
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")

