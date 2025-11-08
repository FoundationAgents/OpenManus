"""
Security Rules Engine
Defines and evaluates security rules
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from app.logger import logger
from app.config import config
from app.database.database_service import database_service, audit_service


class SecurityRule:
    """Represents a security rule"""
    
    def __init__(self, rule_id: str, name: str, description: str, 
                 severity: str, rule_type: str, conditions: Dict[str, Any],
                 action: str = "alert"):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.severity = severity
        self.rule_type = rule_type
        self.conditions = conditions
        self.action = action
    
    async def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the rule against context"""
        try:
            if self.rule_type == "file_access":
                return await self._evaluate_file_access(context)
            elif self.rule_type == "api_access":
                return await self._evaluate_api_access(context)
            elif self.rule_type == "user_behavior":
                return await self._evaluate_user_behavior(context)
            elif self.rule_type == "system_resource":
                return await self._evaluate_system_resource(context)
            elif self.rule_type == "time_based":
                return await self._evaluate_time_based(context)
            else:
                logger.warning(f"Unknown rule type: {self.rule_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating rule {self.rule_id}: {e}")
            return False
    
    async def _evaluate_file_access(self, context: Dict[str, Any]) -> bool:
        """Evaluate file access rules"""
        file_path = context.get("file_path", "")
        action = context.get("action", "")
        user_role = context.get("user_role", "")
        
        # Check file pattern restrictions
        if "file_patterns" in self.conditions:
            patterns = self.conditions["file_patterns"]
            for pattern in patterns:
                if re.match(pattern, file_path):
                    # Check if action is restricted
                    restricted_actions = self.conditions.get("restricted_actions", [])
                    if action in restricted_actions:
                        return True
        
        # Check role-based restrictions
        if "role_restrictions" in self.conditions:
            role_restriction = self.conditions["role_restrictions"]
            if user_role in role_restriction.get("roles", []):
                restricted_files = role_restriction.get("file_patterns", [])
                for pattern in restricted_files:
                    if re.match(pattern, file_path):
                        return True
        
        return False
    
    async def _evaluate_api_access(self, context: Dict[str, Any]) -> bool:
        """Evaluate API access rules"""
        endpoint = context.get("endpoint", "")
        method = context.get("method", "")
        user_id = context.get("user_id")
        ip_address = context.get("ip_address", "")
        
        # Check rate limiting
        if "rate_limit" in self.conditions:
            rate_limit = self.conditions["rate_limit"]
            time_window = rate_limit.get("time_window", 3600)  # 1 hour default
            max_requests = rate_limit.get("max_requests", 1000)
            
            # Count recent requests
            cutoff_time = datetime.now() - timedelta(seconds=time_window)
            async with await database_service.get_connection() as db:
                cursor = await db.execute("""
                    SELECT COUNT(*) as count
                    FROM audit_logs
                    WHERE action = ? AND user_id = ? AND timestamp > ?
                """, (f"api_{method}_{endpoint}", user_id, cutoff_time.isoformat()))
                
                count = (await cursor.fetchone())[0]
                if count > max_requests:
                    return True
        
        # Check IP restrictions
        if "ip_restrictions" in self.conditions:
            ip_restrictions = self.conditions["ip_restrictions"]
            blocked_ips = ip_restrictions.get("blocked_ips", [])
            allowed_ips = ip_restrictions.get("allowed_ips", [])
            
            if blocked_ips and ip_address in blocked_ips:
                return True
            
            if allowed_ips and ip_address not in allowed_ips:
                return True
        
        return False
    
    async def _evaluate_user_behavior(self, context: Dict[str, Any]) -> bool:
        """Evaluate user behavior rules"""
        user_id = context.get("user_id")
        action = context.get("action", "")
        
        # Check for unusual login times
        if "login_time_restrictions" in self.conditions:
            time_restrictions = self.conditions["login_time_restrictions"]
            current_hour = datetime.now().hour
            
            allowed_hours = time_restrictions.get("allowed_hours", list(range(24)))
            if current_hour not in allowed_hours and action == "login":
                # Check if this is unusual for this user
                async with await database_service.get_connection() as db:
                    cursor = await db.execute("""
                        SELECT COUNT(*) as count, COUNT(DISTINCT strftime('%H', timestamp)) as unique_hours
                        FROM audit_logs
                        WHERE user_id = ? AND action = 'login'
                        AND timestamp > datetime('now', '-30 days')
                    """, (user_id,))
                    
                    result = await cursor.fetchone()
                    total_logins, unique_hours = result
                    
                    # If user has logged in during this hour before, allow it
                    if unique_hours > 10:  # User has diverse login pattern
                        return False
                
                return True
        
        # Check for privilege escalation patterns
        if "privilege_escalation" in self.conditions:
            escalation_rules = self.conditions["privilege_escalation"]
            if action in escalation_rules.get("restricted_actions", []):
                # Check if user has recently performed similar actions
                time_window = escalation_rules.get("time_window", 86400)  # 24 hours
                max_actions = escalation_rules.get("max_actions", 1)
                
                cutoff_time = datetime.now() - timedelta(seconds=time_window)
                async with await database_service.get_connection() as db:
                    cursor = await db.execute("""
                        SELECT COUNT(*) as count
                        FROM audit_logs
                        WHERE user_id = ? AND action = ? AND timestamp > ?
                    """, (user_id, action, cutoff_time.isoformat()))
                    
                    count = (await cursor.fetchone())[0]
                    if count > max_actions:
                        return True
        
        return False
    
    async def _evaluate_system_resource(self, context: Dict[str, Any]) -> bool:
        """Evaluate system resource rules"""
        metric_name = context.get("metric_name", "")
        metric_value = context.get("metric_value", 0)
        
        # Check threshold violations
        if "thresholds" in self.conditions:
            thresholds = self.conditions["thresholds"]
            
            if metric_name in thresholds:
                threshold_config = thresholds[metric_name]
                
                # Check max threshold
                if "max" in threshold_config and metric_value > threshold_config["max"]:
                    return True
                
                # Check min threshold
                if "min" in threshold_config and metric_value < threshold_config["min"]:
                    return True
        
        # Check sustained violations
        if "sained_violations" in self.conditions:
            sustained_config = self.conditions["sustained_violations"]
            duration = sustained_config.get("duration", 300)  # 5 minutes
            threshold = sustained_config.get("threshold", 0.8)
            
            # Check if metric has been above threshold for duration
            cutoff_time = datetime.now() - timedelta(seconds=duration)
            async with await database_service.get_connection() as db:
                cursor = await db.execute("""
                    SELECT COUNT(*) as count, AVG(metric_value) as avg_value
                    FROM system_metrics
                    WHERE metric_name = ? AND timestamp > ?
                """, (metric_name, cutoff_time.isoformat()))
                
                result = await cursor.fetchone()
                count, avg_value = result
                
                if count > 0 and avg_value > threshold:
                    return True
        
        return False
    
    async def _evaluate_time_based(self, context: Dict[str, Any]) -> bool:
        """Evaluate time-based rules"""
        current_time = datetime.now()
        
        # Check maintenance windows
        if "maintenance_windows" in self.conditions:
            windows = self.conditions["maintenance_windows"]
            
            for window in windows:
                start_hour = window.get("start_hour", 0)
                end_hour = window.get("end_hour", 23)
                days = window.get("days", list(range(7)))  # 0=Monday, 6=Sunday
                
                if (current_time.hour >= start_hour and current_time.hour <= end_hour and
                    current_time.weekday() in days):
                    return True
        
        # Check business hours restrictions
        if "business_hours_only" in self.conditions:
            business_config = self.conditions["business_hours_only"]
            start_hour = business_config.get("start_hour", 9)
            end_hour = business_config.get("end_hour", 17)
            days = business_config.get("days", [0, 1, 2, 3, 4])  # Monday-Friday
            
            if (current_time.hour < start_hour or current_time.hour > end_hour or
                current_time.weekday() not in days):
                return True
        
        return False


class SecurityRules:
    """Security rules engine"""
    
    def __init__(self):
        self.rules: Dict[str, SecurityRule] = {}
        self._load_default_rules()
        self._load_custom_rules()
    
    def _load_default_rules(self):
        """Load default security rules"""
        default_rules = [
            SecurityRule(
                rule_id="critical_file_access",
                name="Critical File Access",
                description="Detect access to critical system files",
                severity="high",
                rule_type="file_access",
                conditions={
                    "file_patterns": [
                        r"/etc/passwd",
                        r"/etc/shadow",
                        r"/etc/sudoers",
                        r"/root/.*",
                        r"\.ssh/.*",
                        r"\.env$",
                        r"config/.*\.conf$"
                    ],
                    "restricted_actions": ["write", "delete", "execute"]
                }
            ),
            
            SecurityRule(
                rule_id="api_rate_limit",
                name="API Rate Limiting",
                description="Detect excessive API usage",
                severity="medium",
                rule_type="api_access",
                conditions={
                    "rate_limit": {
                        "time_window": 3600,  # 1 hour
                        "max_requests": 1000
                    }
                }
            ),
            
            SecurityRule(
                rule_id="unusual_login_time",
                name="Unusual Login Time",
                description="Detect logins outside normal hours",
                severity="low",
                rule_type="user_behavior",
                conditions={
                    "login_time_restrictions": {
                        "allowed_hours": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
                    }
                }
            ),
            
            SecurityRule(
                rule_id="system_resource_abuse",
                name="System Resource Abuse",
                description="Detect system resource threshold violations",
                severity="high",
                rule_type="system_resource",
                conditions={
                    "thresholds": {
                        "cpu_usage": {"max": 95.0},
                        "memory_usage": {"max": 90.0},
                        "disk_usage": {"max": 85.0},
                        "error_rate": {"max": 0.1}
                    },
                    "sustained_violations": {
                        "duration": 300,  # 5 minutes
                        "threshold": 0.8
                    }
                }
            ),
            
            SecurityRule(
                rule_id="maintenance_window",
                name="Maintenance Window Restriction",
                description="Restrict operations during maintenance windows",
                severity="medium",
                rule_type="time_based",
                conditions={
                    "maintenance_windows": [
                        {
                            "start_hour": 2,
                            "end_hour": 4,
                            "days": [6]  # Sunday
                        }
                    ]
                }
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
            logger.info(f"Loaded default security rule: {rule.name}")
    
    def _load_custom_rules(self):
        """Load custom security rules from file"""
        try:
            rules_file = Path(config.guardian.security_rules_file)
            if not rules_file.exists():
                logger.info(f"Custom rules file not found: {rules_file}")
                return
            
            with open(rules_file, 'r') as f:
                rules_data = json.load(f)
            
            for rule_data in rules_data.get("rules", []):
                rule = SecurityRule(
                    rule_id=rule_data["rule_id"],
                    name=rule_data["name"],
                    description=rule_data["description"],
                    severity=rule_data["severity"],
                    rule_type=rule_data["rule_type"],
                    conditions=rule_data["conditions"],
                    action=rule_data.get("action", "alert")
                )
                
                self.rules[rule.rule_id] = rule
                logger.info(f"Loaded custom security rule: {rule.name}")
                
        except Exception as e:
            logger.error(f"Error loading custom security rules: {e}")
    
    async def check_violations(self, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Check all rules for violations"""
        violations = []
        
        for rule in self.rules.values():
            try:
                if await rule.evaluate(context or {}):
                    violations.append({
                        "rule_id": rule.rule_id,
                        "rule_type": rule.rule_type,
                        "severity": rule.severity,
                        "description": rule.description,
                        "action": rule.action,
                        "metadata": {
                            "rule_name": rule.name,
                            "conditions": rule.conditions
                        }
                    })
                    
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
        
        return violations
    
    def add_rule(self, rule: SecurityRule):
        """Add a new security rule"""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added security rule: {rule.name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a security rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed security rule: {rule_id}")
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[SecurityRule]:
        """Get a security rule by ID"""
        return self.rules.get(rule_id)
    
    def list_rules(self) -> List[SecurityRule]:
        """List all security rules"""
        return list(self.rules.values())
