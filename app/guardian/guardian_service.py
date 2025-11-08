"""
Guardian Security Monitoring Service
Monitors system activities and detects threats
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import aiosqlite

from app.logger import logger
from app.config import config
from app.database.database_service import database_service, audit_service
from .threat_detector import ThreatDetector
from .security_rules import SecurityRules


@dataclass
class SecurityEvent:
    """Represents a security event"""
    event_type: str
    severity: str  # low, medium, high, critical
    description: str
    source_ip: Optional[str] = None
    user_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class GuardianService:
    """Main Guardian security monitoring service"""
    
    def __init__(self):
        self.threat_detector = ThreatDetector()
        self.security_rules = SecurityRules()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._event_queue = asyncio.Queue()
        self._running = False
    
    async def start(self):
        """Start the Guardian service"""
        if not config.guardian.enable_guardian:
            logger.info("Guardian service disabled in configuration")
            return
        
        logger.info("Starting Guardian security monitoring service...")
        self._running = True
        
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Start event processing task
        asyncio.create_task(self._event_processing_loop())
        
        logger.info("Guardian service started successfully")
    
    async def stop(self):
        """Stop the Guardian service"""
        logger.info("Stopping Guardian service...")
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Guardian service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._perform_security_scan()
                await asyncio.sleep(config.guardian.scan_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in security monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _event_processing_loop(self):
        """Process security events from queue"""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._process_security_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing security event: {e}")
    
    async def _perform_security_scan(self):
        """Perform regular security scan"""
        try:
            # Check for suspicious login attempts
            await self._check_login_anomalies()
            
            # Check for unusual system activity
            await self._check_system_anomalies()
            
            # Check for security rule violations
            await self._check_security_rules()
            
            # Check for resource abuse
            await self._check_resource_abuse()
            
        except Exception as e:
            logger.error(f"Error during security scan: {e}")
    
    async def _check_login_anomalies(self):
        """Check for suspicious login patterns"""
        try:
            # Get recent failed login attempts
            recent_failures = await audit_service.get_audit_logs(
                action="login_failed",
                limit=100
            )
            
            # Group by IP and user
            ip_failures = {}
            user_failures = {}
            
            for log in recent_failures:
                ip = log.get('ip_address')
                user_id = log.get('user_id')
                
                if ip:
                    ip_failures[ip] = ip_failures.get(ip, 0) + 1
                if user_id:
                    user_failures[user_id] = user_failures.get(user_id, 0) + 1
            
            # Check for IP-based attacks
            for ip, count in ip_failures.items():
                if count >= config.acl.max_failed_attempts:
                    await self._create_security_event(
                        event_type="brute_force_ip",
                        severity="high",
                        description=f"Brute force attack detected from IP {ip}: {count} failed attempts",
                        source_ip=ip,
                        metadata={"failed_attempts": count}
                    )
            
            # Check for user-based attacks
            for user_id, count in user_failures.items():
                if count >= config.acl.max_failed_attempts:
                    await self._create_security_event(
                        event_type="brute_force_user",
                        severity="high",
                        description=f"Brute force attack detected for user {user_id}: {count} failed attempts",
                        user_id=user_id,
                        metadata={"failed_attempts": count}
                    )
                    
        except Exception as e:
            logger.error(f"Error checking login anomalies: {e}")
    
    async def _check_system_anomalies(self):
        """Check for unusual system activity patterns"""
        try:
            # Get recent system metrics
            async with await database_service.get_connection() as db:
                cursor = await db.execute("""
                    SELECT metric_name, AVG(metric_value) as avg_value, COUNT(*) as count
                    FROM system_metrics 
                    WHERE timestamp > datetime('now', '-1 hour')
                    GROUP BY metric_name
                """)
                metrics = await cursor.fetchall()
                
                for metric_name, avg_value, count in metrics:
                    # Check for anomalies using threat detector
                    is_anomaly, confidence = await self.threat_detector.detect_anomaly(
                        metric_name, avg_value
                    )
                    
                    if is_anomaly and confidence > config.guardian.anomaly_threshold:
                        await self._create_security_event(
                            event_type="system_anomaly",
                            severity="medium",
                            description=f"Anomaly detected in {metric_name}: {avg_value:.2f} (confidence: {confidence:.2f})",
                            metadata={
                                "metric_name": metric_name,
                                "value": avg_value,
                                "confidence": confidence
                            }
                        )
                        
        except Exception as e:
            logger.error(f"Error checking system anomalies: {e}")
    
    async def _check_security_rules(self):
        """Check for security rule violations"""
        try:
            violations = await self.security_rules.check_violations()
            
            for violation in violations:
                await self._create_security_event(
                    event_type=violation["rule_type"],
                    severity=violation["severity"],
                    description=violation["description"],
                    metadata=violation.get("metadata", {})
                )
                
        except Exception as e:
            logger.error(f"Error checking security rules: {e}")
    
    async def _check_resource_abuse(self):
        """Check for resource abuse patterns"""
        try:
            # Check for excessive API calls
            async with await database_service.get_connection() as db:
                cursor = await db.execute("""
                    SELECT user_id, COUNT(*) as call_count
                    FROM audit_logs 
                    WHERE action LIKE 'api_%' 
                    AND timestamp > datetime('now', '-1 hour')
                    GROUP BY user_id
                    HAVING call_count > 1000
                """)
                results = await cursor.fetchall()
                
                for user_id, call_count in results:
                    await self._create_security_event(
                        event_type="resource_abuse",
                        severity="medium",
                        description=f"Excessive API usage by user {user_id}: {call_count} calls in 1 hour",
                        user_id=user_id,
                        metadata={"call_count": call_count, "timeframe": "1 hour"}
                    )
                    
        except Exception as e:
            logger.error(f"Error checking resource abuse: {e}")
    
    async def _create_security_event(self, event_type: str, severity: str, 
                                  description: str, source_ip: Optional[str] = None,
                                  user_id: Optional[int] = None,
                                  metadata: Optional[Dict[str, Any]] = None):
        """Create and process a security event"""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            description=description,
            source_ip=source_ip,
            user_id=user_id,
            metadata=metadata
        )
        
        await self._event_queue.put(event)
    
    async def _process_security_event(self, event: SecurityEvent):
        """Process a security event"""
        try:
            # Log to database
            async with await database_service.get_connection() as db:
                await db.execute("""
                    INSERT INTO security_events 
                    (event_type, severity, description, source_ip, user_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event.event_type, event.severity, event.description,
                    event.source_ip, event.user_id, json.dumps(event.metadata)
                ))
                await db.commit()
            
            # Send alerts
            await self._send_alerts(event)
            
            # Take automated actions if configured
            if config.guardian.quarantine_suspicious:
                await self._take_automated_action(event)
            
            logger.warning(f"Security event: {event.severity.upper()} - {event.description}")
            
        except Exception as e:
            logger.error(f"Error processing security event: {e}")
    
    async def _send_alerts(self, event: SecurityEvent):
        """Send alerts for security events"""
        try:
            alert_channels = config.guardian.alert_channels
            
            # Log alert
            if "log" in alert_channels:
                logger.warning(f"GUARDIAN ALERT [{event.severity.upper()}] {event.event_type}: {event.description}")
            
            # UI alert (would integrate with UI system)
            if "ui" in alert_channels:
                # This would send to UI notification system
                pass
            
            # Email alert (would integrate with email system)
            if "email" in alert_channels:
                # This would send email notification
                pass
                
        except Exception as e:
            logger.error(f"Error sending alerts: {e}")
    
    async def _take_automated_action(self, event: SecurityEvent):
        """Take automated security actions"""
        try:
            if event.severity in ["high", "critical"]:
                # Implement automated quarantine/blocking logic
                if event.event_type == "brute_force_ip":
                    logger.info(f"Would block IP {event.source_ip} due to brute force attack")
                elif event.event_type == "brute_force_user":
                    logger.info(f"Would lock user {event.user_id} due to brute force attack")
                    
        except Exception as e:
            logger.error(f"Error taking automated action: {e}")
    
    async def get_security_events(self, severity: Optional[str] = None, 
                                limit: int = 100) -> List[Dict[str, Any]]:
        """Get security events"""
        async with await database_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM security_events WHERE 1=1"
            params = []
            
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                results.append(result)
            return results
    
    async def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary statistics"""
        async with await database_service.get_connection() as db:
            # Get counts by severity
            cursor = await db.execute("""
                SELECT severity, COUNT(*) as count
                FROM security_events 
                WHERE created_at > datetime('now', '-24 hours')
                GROUP BY severity
            """)
            severity_counts = dict(await cursor.fetchall())
            
            # Get recent event count
            cursor = await db.execute("""
                SELECT COUNT(*) as count
                FROM security_events 
                WHERE created_at > datetime('now', '-24 hours')
            """)
            total_recent = (await cursor.fetchone())[0]
            
            # Get unresolved critical events
            cursor = await db.execute("""
                SELECT COUNT(*) as count
                FROM security_events 
                WHERE severity = 'critical' AND resolved = FALSE
            """)
            unresolved_critical = (await cursor.fetchone())[0]
            
            return {
                "total_recent_24h": total_recent,
                "severity_counts_24h": severity_counts,
                "unresolved_critical": unresolved_critical,
                "last_scan": datetime.now().isoformat()
            }


# Global Guardian service instance
guardian_service = GuardianService()
