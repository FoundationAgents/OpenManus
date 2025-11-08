"""
WebSocket client with heartbeat detection and Guardian integration.

Provides async WebSocket connections with automatic reconnection,
heartbeat monitoring, message queuing, and security validation.
"""

import asyncio
import json
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

import websockets
from pydantic import BaseModel, Field
try:
    from websockets.asyncio.client import ClientConnection as WebSocketClientProtocol
except ImportError:
    from websockets.client import WebSocketClientProtocol

from app.network.guardian import Guardian, OperationType, get_guardian
from app.utils.logger import logger


class ConnectionState(str, Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSED = "closed"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    """WebSocket message wrapper."""
    
    data: Any
    timestamp: datetime = Field(default_factory=datetime.now)
    message_type: str = "text"
    
    class Config:
        arbitrary_types_allowed = True


class WebSocketConfig(BaseModel):
    """Configuration for WebSocket client."""
    
    heartbeat_interval: float = 30.0
    heartbeat_timeout: float = 10.0
    ping_interval: float = 20.0
    ping_timeout: float = 20.0
    max_reconnect_attempts: int = 5
    reconnect_delay: float = 2.0
    message_queue_size: int = 1000
    close_timeout: float = 10.0


class WebSocketHandler:
    """
    Advanced WebSocket client with heartbeat and Guardian integration.
    
    Features:
    - Automatic heartbeat detection
    - Reconnection with exponential backoff
    - Message queuing
    - Guardian security validation
    - Event callbacks
    - Connection monitoring
    """
    
    def __init__(
        self,
        url: str,
        config: Optional[WebSocketConfig] = None,
        guardian: Optional[Guardian] = None
    ):
        """
        Initialize WebSocket handler.
        
        Args:
            url: WebSocket URL (ws:// or wss://)
            config: WebSocket configuration
            guardian: Guardian instance for security validation
        """
        self.url = url
        self.config = config or WebSocketConfig()
        self.guardian = guardian or get_guardian()
        
        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.websocket: Optional[WebSocketClientProtocol] = None
        
        # Message handling
        self.message_queue: asyncio.Queue = asyncio.Queue(
            maxsize=self.config.message_queue_size
        )
        self.outgoing_queue: asyncio.Queue = asyncio.Queue()
        
        # Event callbacks
        self.on_message_callback: Optional[Callable] = None
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        
        # Tasks
        self._receiver_task: Optional[asyncio.Task] = None
        self._sender_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # Heartbeat tracking
        self._last_heartbeat = datetime.now()
        self._heartbeat_active = False
        
        # Stats
        self._messages_sent = 0
        self._messages_received = 0
        self._reconnect_count = 0
        
        logger.info(f"WebSocketHandler initialized for {url}")
    
    def _parse_url(self) -> tuple:
        """Parse WebSocket URL into host and port."""
        parsed = urlparse(self.url)
        host = parsed.hostname or parsed.netloc
        port = parsed.port
        
        if port is None:
            port = 443 if parsed.scheme == 'wss' else 80
        
        return host, port
    
    async def _check_guardian(self) -> bool:
        """
        Check Guardian approval for WebSocket connection.
        
        Returns:
            True if approved
            
        Raises:
            PermissionError: If connection is blocked
        """
        host, port = self._parse_url()
        
        # Assess risk
        assessment = self.guardian.assess_risk(
            operation=OperationType.WEBSOCKET,
            host=host,
            port=port,
            url=self.url
        )
        
        if not assessment.approved:
            error_msg = (
                f"WebSocket connection blocked by Guardian: {self.url}\n"
                f"Risk Level: {assessment.level.value}\n"
                f"Reasons: {', '.join(assessment.reasons)}"
            )
            logger.warning(error_msg)
            raise PermissionError(error_msg)
        
        if assessment.requires_confirmation:
            logger.warning(
                f"WebSocket requires confirmation: {self.url} "
                f"(Risk: {assessment.level.value})"
            )
            # Check if pre-approved
            if not self.guardian.is_approved(OperationType.WEBSOCKET, host, port):
                raise PermissionError(
                    f"WebSocket requires manual approval: {self.url}"
                )
        
        return True
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection.
        
        Returns:
            True if connected successfully
            
        Raises:
            PermissionError: If blocked by Guardian
            ConnectionError: On connection failure
        """
        if self.state == ConnectionState.CONNECTED:
            logger.warning("Already connected")
            return True
        
        # Check Guardian approval
        await self._check_guardian()
        
        try:
            self.state = ConnectionState.CONNECTING
            logger.info(f"Connecting to WebSocket: {self.url}")
            
            # Connect with ping/pong settings
            self.websocket = await websockets.connect(
                self.url,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout,
                close_timeout=self.config.close_timeout
            )
            
            self.state = ConnectionState.CONNECTED
            self._last_heartbeat = datetime.now()
            
            # Start background tasks
            self._receiver_task = asyncio.create_task(self._receive_loop())
            self._sender_task = asyncio.create_task(self._send_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info(f"WebSocket connected: {self.url}")
            
            # Trigger callback
            if self.on_connect_callback:
                await self._safe_callback(self.on_connect_callback)
            
            return True
            
        except Exception as e:
            self.state = ConnectionState.ERROR
            logger.error(f"Failed to connect WebSocket: {e}")
            
            if self.on_error_callback:
                await self._safe_callback(self.on_error_callback, e)
            
            raise ConnectionError(f"WebSocket connection failed: {e}")
    
    async def disconnect(self):
        """Disconnect WebSocket."""
        if self.state == ConnectionState.DISCONNECTED:
            return
        
        logger.info("Disconnecting WebSocket")
        self.state = ConnectionState.CLOSED
        
        # Cancel background tasks
        for task in [self._receiver_task, self._sender_task, self._heartbeat_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.state = ConnectionState.DISCONNECTED
        logger.info("WebSocket disconnected")
        
        # Trigger callback
        if self.on_disconnect_callback:
            await self._safe_callback(self.on_disconnect_callback)
    
    async def send(self, data: Any, message_type: str = "text"):
        """
        Send message over WebSocket.
        
        Args:
            data: Message data
            message_type: Message type (text or binary)
        """
        if self.state != ConnectionState.CONNECTED:
            raise ConnectionError("WebSocket not connected")
        
        message = WebSocketMessage(data=data, message_type=message_type)
        await self.outgoing_queue.put(message)
    
    async def send_json(self, data: Dict):
        """Send JSON message."""
        await self.send(json.dumps(data), "text")
    
    async def receive(self, timeout: Optional[float] = None) -> Optional[WebSocketMessage]:
        """
        Receive message from WebSocket.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            WebSocketMessage or None if timeout
        """
        try:
            if timeout:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=timeout
                )
            else:
                message = await self.message_queue.get()
            return message
        except asyncio.TimeoutError:
            return None
    
    async def _receive_loop(self):
        """Background task to receive messages."""
        try:
            while self.state == ConnectionState.CONNECTED:
                if not self.websocket:
                    break
                
                try:
                    message = await self.websocket.recv()
                    
                    # Update heartbeat
                    self._last_heartbeat = datetime.now()
                    
                    # Create message object
                    ws_message = WebSocketMessage(
                        data=message,
                        message_type="text" if isinstance(message, str) else "binary"
                    )
                    
                    # Add to queue
                    try:
                        self.message_queue.put_nowait(ws_message)
                        self._messages_received += 1
                    except asyncio.QueueFull:
                        logger.warning("Message queue full, dropping message")
                    
                    # Trigger callback
                    if self.on_message_callback:
                        await self._safe_callback(self.on_message_callback, ws_message)
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    if self.on_error_callback:
                        await self._safe_callback(self.on_error_callback, e)
        
        finally:
            # Trigger reconnection if needed
            if self.state == ConnectionState.CONNECTED:
                await self._reconnect()
    
    async def _send_loop(self):
        """Background task to send messages."""
        try:
            while self.state == ConnectionState.CONNECTED:
                if not self.websocket:
                    break
                
                try:
                    message = await self.outgoing_queue.get()
                    
                    if message.message_type == "text":
                        await self.websocket.send(message.data)
                    else:
                        await self.websocket.send(message.data)
                    
                    self._messages_sent += 1
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed while sending")
                    break
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    if self.on_error_callback:
                        await self._safe_callback(self.on_error_callback, e)
        
        except asyncio.CancelledError:
            pass
    
    async def _heartbeat_loop(self):
        """Background task to monitor heartbeat."""
        try:
            while self.state == ConnectionState.CONNECTED:
                await asyncio.sleep(self.config.heartbeat_interval)
                
                # Check if heartbeat timeout exceeded
                elapsed = (datetime.now() - self._last_heartbeat).total_seconds()
                
                if elapsed > self.config.heartbeat_timeout:
                    logger.warning(
                        f"Heartbeat timeout: no messages for {elapsed:.1f}s"
                    )
                    # Trigger reconnection
                    await self._reconnect()
                    break
        
        except asyncio.CancelledError:
            pass
    
    async def _reconnect(self):
        """Attempt to reconnect WebSocket."""
        if self.state == ConnectionState.RECONNECTING:
            return
        
        self.state = ConnectionState.RECONNECTING
        logger.info("Attempting to reconnect WebSocket")
        
        for attempt in range(self.config.max_reconnect_attempts):
            try:
                # Close existing connection
                if self.websocket:
                    await self.websocket.close()
                
                # Wait before reconnecting (exponential backoff)
                delay = self.config.reconnect_delay * (2 ** attempt)
                await asyncio.sleep(delay)
                
                # Attempt connection
                await self.connect()
                
                self._reconnect_count += 1
                logger.info(f"Reconnected successfully (attempt {attempt + 1})")
                return
                
            except Exception as e:
                logger.warning(
                    f"Reconnection attempt {attempt + 1} failed: {e}"
                )
        
        # Max attempts reached
        logger.error("Max reconnection attempts reached")
        self.state = ConnectionState.ERROR
        
        if self.on_error_callback:
            await self._safe_callback(
                self.on_error_callback,
                Exception("Max reconnection attempts reached")
            )
    
    async def _safe_callback(self, callback: Callable, *args):
        """Execute callback safely."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Error in callback: {e}")
    
    def on_message(self, callback: Callable):
        """Register message callback."""
        self.on_message_callback = callback
    
    def on_connect(self, callback: Callable):
        """Register connect callback."""
        self.on_connect_callback = callback
    
    def on_disconnect(self, callback: Callable):
        """Register disconnect callback."""
        self.on_disconnect_callback = callback
    
    def on_error(self, callback: Callable):
        """Register error callback."""
        self.on_error_callback = callback
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics."""
        return {
            "state": self.state.value,
            "url": self.url,
            "messages_sent": self._messages_sent,
            "messages_received": self._messages_received,
            "reconnect_count": self._reconnect_count,
            "queue_size": self.message_queue.qsize(),
            "last_heartbeat": self._last_heartbeat.isoformat(),
            "connected": self.state == ConnectionState.CONNECTED,
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
