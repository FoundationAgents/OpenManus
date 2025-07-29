from app.logger import logger

__all__ = ["initialize_event_handlers"]


def initialize_event_handlers():
    """
    显式初始化所有事件处理器

    这个函数确保所有事件处理器都被正确注册到事件系统中。
    """

    # 显式注册所有事件处理器
    _register_frontend_handlers()

    logger.info("事件处理器初始化完成")

    # 可选：验证注册状态
    try:
        from app.event.infrastructure import get_global_registry

        registry = get_global_registry()
        handlers = registry.list_handlers()
        logger.info(f"已注册 {len(handlers)} 个事件处理器")
    except Exception as e:
        logger.warning(f"无法验证事件处理器注册状态: {e}")


def _register_frontend_handlers():
    """注册前端事件处理器"""
    from app.event import BaseEvent, bus, event_handler

    @event_handler(["user.interrupt"])
    async def handle_user_interrupt(event: BaseEvent):
        """处理用户中断事件"""
        conversation_id = event.data.get("conversation_id")
        reason = event.data.get("reason", "user_interrupt")

        logger.info(
            f"收到用户中断事件: conversation_id={conversation_id}, reason={reason}"
        )

        # 发送响应事件到前端
        response_event = BaseEvent(
            event_type="system.interrupt_acknowledged",
            data={
                "conversation_id": conversation_id,
                "status": "acknowledged",
                "message": f"用户中断请求已处理: {reason}",
            },
            source="backend",
        )

        await bus.publish(response_event)
        return True

    @event_handler(["user.input"])
    async def handle_user_input(event: BaseEvent):
        """处理用户输入事件"""
        conversation_id = event.data.get("conversation_id")
        message = event.data.get("message")

        logger.info(
            f"收到用户输入事件: conversation_id={conversation_id}, message={message}"
        )

        # 发送响应事件到前端
        response_event = BaseEvent(
            event_type="system.input_received",
            data={
                "conversation_id": conversation_id,
                "status": "received",
                "message": f"已收到用户输入: {message}",
                "original_input": message,
            },
            source="backend",
        )

        await bus.publish(response_event)
        return True

    @event_handler(["ui.interaction"])
    async def handle_ui_interaction(event: BaseEvent):
        """处理UI交互事件"""
        conversation_id = event.data.get("conversation_id")
        action = event.data.get("action")
        target = event.data.get("target")

        logger.info(
            f"收到UI交互事件: conversation_id={conversation_id}, action={action}, target={target}"
        )

        # 发送响应事件到前端
        response_event = BaseEvent(
            event_type="system.ui_interaction_processed",
            data={
                "conversation_id": conversation_id,
                "status": "processed",
                "action": action,
                "target": target,
                "message": f"UI交互已处理: {action} on {target}",
            },
            source="backend",
        )

        await bus.publish(response_event)
        return True

    @event_handler(["frontend.*"])
    async def handle_generic_frontend_events(event: BaseEvent):
        """处理通用前端事件"""
        logger.info(f"收到前端事件: {event.event_type}, data: {event.data}")
        return True
