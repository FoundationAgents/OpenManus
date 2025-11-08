"""
Watchdog Service

External process monitoring and auto-restart capability.
Runs as a separate process to detect and recover from hangs.
"""

import asyncio
import os
import platform
import psutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.logger import logger


class WatchdogService:
    """External watchdog for process monitoring"""

    HEALTH_CHECK_PORT = 9999
    HEALTH_CHECK_INTERVAL = 30  # seconds
    HANG_DETECTION_TIMEOUT = 60  # seconds
    MAX_RESTART_ATTEMPTS = 3

    def __init__(self, main_process_pid: Optional[int] = None):
        self.main_process_pid = main_process_pid
        self._is_running = False
        self._restart_count = 0
        self._last_health_check = None
        self._health_check_failures = 0

    async def start(self):
        """Start watchdog service"""
        self._is_running = True
        logger.info(f"Watchdog service started (monitoring PID: {self.main_process_pid})")

        # Start monitoring loop
        await self._monitoring_loop()

    async def stop(self):
        """Stop watchdog service"""
        self._is_running = False
        logger.info("Watchdog service stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._is_running:
            try:
                await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)

                # Check process health
                if not await self._check_process_health():
                    self._health_check_failures += 1

                    if self._health_check_failures >= 2:
                        logger.warning(
                            f"Process health check failed {self._health_check_failures} times"
                        )

                        if self._restart_count < self.MAX_RESTART_ATTEMPTS:
                            await self._restart_main_process()
                            self._restart_count += 1
                        else:
                            logger.error(
                                f"Max restart attempts ({self.MAX_RESTART_ATTEMPTS}) reached"
                            )

                else:
                    self._health_check_failures = 0

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    async def _check_process_health(self) -> bool:
        """Check if main process is healthy"""
        try:
            if self.main_process_pid:
                # Check if process is still running
                try:
                    proc = psutil.Process(self.main_process_pid)
                    if proc.status() == psutil.STATUS_ZOMBIE:
                        logger.error("Main process is a zombie")
                        return False

                    # Check if process is responsive via health endpoint
                    if await self._check_health_endpoint():
                        self._last_health_check = datetime.now()
                        return True
                    else:
                        logger.warning("Health endpoint not responding")
                        return False

                except psutil.NoSuchProcess:
                    logger.error("Main process not found")
                    return False

            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def _check_health_endpoint(self) -> bool:
        """Check if process responds to health request"""
        try:
            # Try to connect to health check endpoint
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("localhost", self.HEALTH_CHECK_PORT),
                timeout=5.0,
            )

            writer.write(b"PING\n")
            await writer.drain()

            response = await asyncio.wait_for(reader.readline(), timeout=5.0)
            writer.close()
            await writer.wait_closed()

            return response.startswith(b"PONG")

        except Exception as e:
            logger.debug(f"Health endpoint check failed: {e}")
            return False

    async def _restart_main_process(self):
        """Restart the main process"""
        try:
            logger.warning(f"Restarting main process (attempt {self._restart_count + 1})")

            if self.main_process_pid:
                try:
                    proc = psutil.Process(self.main_process_pid)
                    proc.terminate()
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    logger.warning("Process did not terminate gracefully, killing...")
                    proc.kill()
                except Exception as e:
                    logger.error(f"Failed to terminate process: {e}")

            # Get the main script path and restart
            script_path = sys.argv[0]
            if platform.system() == "Windows":
                subprocess.Popen([sys.executable, script_path])
            else:
                subprocess.Popen([sys.executable, script_path])

            logger.info("Process restart command sent")
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Failed to restart process: {e}")

    def get_watchdog_status(self) -> Dict[str, Any]:
        """Get watchdog status"""
        return {
            "is_running": self._is_running,
            "monitored_pid": self.main_process_pid,
            "restart_count": self._restart_count,
            "last_health_check": (
                self._last_health_check.isoformat()
                if self._last_health_check
                else None
            ),
            "health_check_failures": self._health_check_failures,
            "timestamp": datetime.now().isoformat(),
        }


class HealthCheckServer:
    """Health check server for watchdog verification"""

    def __init__(self, port: int = WatchdogService.HEALTH_CHECK_PORT):
        self.port = port
        self._is_running = False

    async def start(self):
        """Start health check server"""
        self._is_running = True
        server = await asyncio.start_server(self._handle_health_check, "localhost", self.port)

        logger.info(f"Health check server started on port {self.port}")

        async with server:
            await server.serve_forever()

    async def _handle_health_check(self, reader, writer):
        """Handle health check request"""
        try:
            data = await reader.readline()

            if data.startswith(b"PING"):
                writer.write(b"PONG\n")
                await writer.drain()

        except Exception as e:
            logger.error(f"Health check handler error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()


async def start_watchdog(main_pid: int):
    """Start watchdog service for a given process"""
    watchdog = WatchdogService(main_process_pid=main_pid)
    health_server = HealthCheckServer()

    # Start both watchdog and health check server
    await asyncio.gather(
        watchdog.start(),
        health_server.start(),
    )
