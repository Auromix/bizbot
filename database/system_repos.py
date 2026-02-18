"""系统数据仓库 —— 系统级数据的数据访问层。

管理系统辅助数据（原始消息、修正记录、每日汇总、插件数据），
这些数据用于消息追溯、审计、统计报表和扩展插件。
"""
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
from sqlalchemy.orm import Session
from loguru import logger

from .base_crud import BaseCRUD
from .connection import DatabaseConnection
from .models import (
    RawMessage, Correction, DailySummary, PluginData
)


class MessageRepository(BaseCRUD):
    """原始消息与修正记录 仓库。

    管理接收到的原始消息，以及对业务记录的修正操作。
    支持消息去重和解析状态跟踪。
    """

    def __init__(self, conn: DatabaseConnection) -> None:
        super().__init__(conn)

    def save_raw_message(self, msg_data: Dict[str, Any]) -> int:
        """保存原始消息（自动去重）。

        Args:
            msg_data: 消息数据字典，支持以下键：
                - msg_id: 消息ID（用于去重，可选）
                - sender_nickname: 发送者昵称（必填）
                - content: 消息内容（必填）
                - msg_type: 消息类型（可选，默认"text"）
                - group_id: 群组ID（可选）
                - timestamp: 消息时间戳（必填）
                - is_at_bot: 是否@机器人（可选）
                - is_business: 是否为业务消息（可选）
                - parse_status: 解析状态（可选，默认"pending"）

        Returns:
            消息记录ID（新建或已存在的）。
        """
        with self._get_session() as session:
            # 去重检查（如果提供了msg_id）
            msg_id = msg_data.get("msg_id")
            existing = None
            if msg_id:
                existing = session.query(RawMessage).filter(
                    RawMessage.msg_id == msg_id
                ).first()
            if existing:
                return existing.id

            msg = RawMessage(
                msg_id=msg_id,
                sender_nickname=msg_data.get("sender_nickname"),
                content=msg_data.get("content"),
                msg_type=msg_data.get("msg_type", "text"),
                group_id=msg_data.get("group_id"),
                timestamp=msg_data.get("timestamp"),
                is_at_bot=msg_data.get("is_at_bot", False),
                is_business=msg_data.get("is_business"),
                parse_status=msg_data.get("parse_status", "pending")
            )
            session.add(msg)
            session.commit()
            session.refresh(msg)
            return msg.id

    def update_parse_status(self, msg_id: int, status: str,
                            result: Optional[Dict[str, Any]] = None,
                            error: Optional[str] = None) -> None:
        """更新消息解析状态。

        Args:
            msg_id: 消息记录ID。
            status: 新的解析状态（pending/parsed/failed/ignored）。
            result: 解析结果字典（可选）。
            error: 解析错误信息（可选）。
        """
        with self._get_session() as session:
            msg = session.query(RawMessage).filter(
                RawMessage.id == msg_id
            ).first()
            if msg:
                msg.parse_status = status
                if result is not None:
                    msg.parse_result = result
                if error is not None:
                    msg.parse_error = error
                session.commit()

    def save_correction(self, correction_data: Dict[str, Any]) -> int:
        """保存修正记录。

        Args:
            correction_data: 修正数据字典，支持以下键：
                - original_record_type: 原始记录类型
                - original_record_id: 原始记录ID
                - correction_type: 修正类型
                - old_value: 旧值（JSON）
                - new_value: 新值（JSON）
                - reason: 修正原因
                - raw_message_id: 关联的原始消息ID

        Returns:
            修正记录ID。
        """
        with self._get_session() as session:
            correction = Correction(
                original_record_type=correction_data.get(
                    "original_record_type"
                ),
                original_record_id=correction_data.get(
                    "original_record_id"
                ),
                correction_type=correction_data.get("correction_type"),
                old_value=correction_data.get("old_value"),
                new_value=correction_data.get("new_value"),
                reason=correction_data.get("reason"),
                raw_message_id=correction_data.get("raw_message_id")
            )
            session.add(correction)
            session.commit()
            session.refresh(correction)
            return correction.id


class SummaryRepository(BaseCRUD):
    """每日汇总 仓库。

    管理每日经营汇总数据，用于快速查询和报表生成。
    """

    def __init__(self, conn: DatabaseConnection) -> None:
        super().__init__(conn)

    def save(self, summary_date: date,
             summary_data: Dict[str, Any]) -> int:
        """保存或更新每日汇总。

        如果该日期的汇总已存在则更新，否则创建新记录（幂等）。

        Args:
            summary_date: 汇总日期。
            summary_data: 汇总数据字典，支持以下键：
                - total_service_revenue: 服务总收入
                - total_product_revenue: 商品总收入
                - total_commissions: 总提成支出
                - net_revenue: 净收入
                - service_count: 服务记录数
                - product_sale_count: 商品销售数
                - new_members: 新增会员数
                - membership_revenue: 会员卡收入
                - summary_text: 汇总文本
                - confirmed: 是否已确认

        Returns:
            汇总记录ID。
        """
        with self._get_session() as session:
            existing = session.query(DailySummary).filter(
                DailySummary.summary_date == summary_date
            ).first()

            if existing:
                for key, value in summary_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                session.commit()
                session.refresh(existing)
                return existing.id
            else:
                summary = DailySummary(
                    summary_date=summary_date, **summary_data
                )
                session.add(summary)
                session.commit()
                session.refresh(summary)
                return summary.id

    def get_by_date(self, summary_date: date,
                    session: Optional[Session] = None
                    ) -> Optional[DailySummary]:
        """获取指定日期的汇总。

        Args:
            summary_date: 目标日期。

        Returns:
            DailySummary 对象，不存在则返回 None。
        """
        def _query(sess):
            return sess.query(DailySummary).filter(
                DailySummary.summary_date == summary_date
            ).first()

        if session:
            return _query(session)

        with self._get_session() as sess:
            return _query(sess)


class PluginRepository(BaseCRUD):
    """插件数据 仓库。

    提供完全自定义的扩展数据存储，用于插件化的业务扩展。
    不同业态可以通过插件机制存储特有的数据，而无需修改核心模型。

    示例场景：
    - 健身房：存储体测数据、课程评价
    - 理发店：存储发型偏好、过敏信息
    - 餐厅：存储会员口味偏好、过敏原
    """

    def __init__(self, conn: DatabaseConnection) -> None:
        super().__init__(conn)

    def save(self, plugin_name: str, entity_type: str,
             entity_id: int, data_key: str,
             data_value: Any) -> int:
        """保存或更新插件数据。

        如果数据已存在则更新，否则创建新记录（幂等）。

        Args:
            plugin_name: 插件标识。
            entity_type: 实体类型（employee/customer/product等）。
            entity_id: 实体ID。
            data_key: 数据键。
            data_value: 数据值（任意JSON可序列化对象）。

        Returns:
            插件数据记录ID。
        """
        with self._get_session() as session:
            existing = session.query(PluginData).filter(
                PluginData.plugin_name == plugin_name,
                PluginData.entity_type == entity_type,
                PluginData.entity_id == entity_id,
                PluginData.data_key == data_key
            ).first()

            if existing:
                existing.data_value = data_value
                existing.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(existing)
                return existing.id
            else:
                plugin_data = PluginData(
                    plugin_name=plugin_name,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    data_key=data_key,
                    data_value=data_value
                )
                session.add(plugin_data)
                session.commit()
                session.refresh(plugin_data)
                return plugin_data.id

    def get(self, plugin_name: str, entity_type: str,
            entity_id: int,
            data_key: Optional[str] = None
            ) -> Union[Dict[str, Any], Any, None]:
        """获取插件数据。

        Args:
            plugin_name: 插件标识。
            entity_type: 实体类型。
            entity_id: 实体ID。
            data_key: 数据键（可选）。提供则返回单个值，否则返回全部。

        Returns:
            单个值或键值对字典。
        """
        with self._get_session() as session:
            query = session.query(PluginData).filter(
                PluginData.plugin_name == plugin_name,
                PluginData.entity_type == entity_type,
                PluginData.entity_id == entity_id
            )
            if data_key:
                query = query.filter(PluginData.data_key == data_key)

            results = query.all()
            if data_key:
                return results[0].data_value if results else None
            else:
                return {
                    item.data_key: item.data_value for item in results
                }

    def delete(self, plugin_name: str, entity_type: str,
               entity_id: int,
               data_key: Optional[str] = None) -> None:
        """删除插件数据。

        Args:
            plugin_name: 插件标识。
            entity_type: 实体类型。
            entity_id: 实体ID。
            data_key: 数据键（可选）。提供则只删除该键，否则删除全部。
        """
        with self._get_session() as session:
            query = session.query(PluginData).filter(
                PluginData.plugin_name == plugin_name,
                PluginData.entity_type == entity_type,
                PluginData.entity_id == entity_id
            )
            if data_key:
                query = query.filter(PluginData.data_key == data_key)

            query.delete()
            session.commit()

