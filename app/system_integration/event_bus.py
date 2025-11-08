"""
Event Bus
Provides publish-subscribe messaging for system components
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional

from app.logger import logger


class EventBus:
    """Asynchronous event bus for system-wide communication"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the event bus"""
        if self._running:
            return
        
        logger.info("Starting event bus...")
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event bus"""
        if not self._running:
            return
        
        logger.info("Stopping event bus...")
        self._running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event bus stopped")
    
    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to an event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type}: {handler.__name__}")
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Unsubscribed from {event_type}: {handler.__name__}")
            except ValueError:
                pass  # Handler not found
    
    async def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """Emit an event"""
        if not self._running:
            logger.warning(f"Event bus not running, dropping event: {event_type}")
            return
        
        event = {
            "type": event_type,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await self._event_queue.put(event)
            logger.debug(f"Emitted event: {event_type}")
        except Exception as e:
            logger.error(f"Error emitting event {event_type}: {e}")
    
    async def _process_events(self):
        """Process events from the queue"""
        while self._running:
            try:
                # Wait for events with timeout to allow graceful shutdown
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._handle_event(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def _handle_event(self, event: Dict[str, Any]):
        """Handle a single event"""
        event_type = event["type"]
        
        if event_type not in self._subscribers:
            logger.debug(f"No subscribers for event type: {event_type}")
            return
        
        handlers = self._subscribers[event_type]
        if not handlers:
            return
        
        # Call all handlers concurrently
        tasks = []
        for handler in handlers:
            try:
                task = asyncio.create_task(handler(event))
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating task for handler {handler.__name__}: {e}")
        
        if tasks:
            # Wait for all handlers to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any handler errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Handler {handlers[i].__name__} failed: {result}")
    
    def get_subscriber_count(self, event_type: str) -> int:
        """Get the number of subscribers for an event type"""
        return len(self._subscribers.get(event_type, []))
    
    def list_event_types(self) -> List[str]:
        """List all registered event types"""
        return list(self._subscribers.keys())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            "running": self._running,
            "event_types": len(self._subscribers),
            "total_subscribers": sum(len(handlers) for handlers in self._subscribers.values()),
            "queue_size": self._event_queue.qsize(),
            "event_types_list": list(self._subscribers.keys())
        }
