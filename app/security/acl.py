"""Access Control Layer (ACL) manager.

This module provides hierarchical, per-agent access control with SQLite backed
persistence. Permissions can be assigned at the agent, pool, role, or global
level and may inherit from configuration defined templates. The manager
supports wildcard and environment variable expansion for path scopes and
exposes a high-level API for permission checks and updating rules.
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import aiosqlite

from app.config import ACLRoleTemplate, config
from app.database.database_service import DatabaseService, audit_service, database_service
from app.logger import logger

ALLOWED_OPERATIONS: Set[str] = {"read", "write", "execute", "delete"}
DEFAULT_PRIORITY = 100
DEFAULT_ROLE = "unassigned"
DEFAULT_GLOBAL_SUBJECT = "*"


@dataclass(frozen=True)
class ACLAgentRecord:
    """Snapshot of an agent registered with the ACL system."""

    agent_id: str
    role: str
    pools: Tuple[str, ...]
    inherits_from: Optional[str]
    metadata: Dict[str, str]


@dataclass(frozen=True)
class ACLRuleRecord:
    """Snapshot of an ACL rule as evaluated by the manager."""

    id: Optional[int]
    subject_type: str
    subject_id: str
    path: str
    operations: Tuple[str, ...]
    effect: str
    priority: int
    inherits_from: Optional[str]
    description: Optional[str]
    created_by: Optional[str]
    template: bool = False
    source: str = "db"


@dataclass
class PermissionDecision:
    """Result of a permission check."""

    allowed: bool
    reason: str
    rule: Optional[ACLRuleRecord] = None


SubjectKey = Tuple[str, str]
PermissionCacheEntry = Tuple[bool, float, str, Optional[ACLRuleRecord]]


class ACLManager:
    """Coordinates ACL persistence and evaluation."""

    def __init__(self, db_service: DatabaseService = database_service):
        self._db_service = db_service
        self._lock = asyncio.Lock()
        self._initialized = False

        self._agents: Dict[str, ACLAgentRecord] = {}
        self._rules: Dict[SubjectKey, Tuple[ACLRuleRecord, ...]] = {}

        self._template_rules: Dict[str, Tuple[ACLRuleRecord, ...]] = {}
        self._template_inherits: Dict[str, Tuple[str, ...]] = {}
        self._template_counter = 0

        self._config_signature: str = ""
        self._default_allowed_ops: Set[str] = self._parse_default_permission(
            config.acl.default_permission
        )

        # Cache keyed by (agent_id, operation, normalized_path)
        self._decision_cache: Dict[Tuple[str, str, str], PermissionCacheEntry] = {}
        self._cache_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Load agents, rules, and templates into memory."""

        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            await self._load_agents()
            await self._load_rules()
            self._load_templates_from_config()
            self._config_signature = self._compute_config_signature()
            self._initialized = True
            logger.info("ACL manager initialized (%s agents, %s rule subjects)",
                        len(self._agents), len(self._rules))

    async def refresh_from_config(self) -> None:
        """Reload templates and defaults from configuration."""

        await self._ensure_initialized()
        async with self._lock:
            self._load_templates_from_config()
            self._config_signature = self._compute_config_signature()
            await self._clear_permission_cache()
            logger.info("ACL templates refreshed from configuration")

    async def register_agent(
        self,
        agent_id: str,
        role: Optional[str] = None,
        pools: Optional[Iterable[str]] = None,
        inherits_from: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> ACLAgentRecord:
        """Register or update an agent in the ACL system."""

        await self._ensure_initialized()
        normalized_role = (role or DEFAULT_ROLE).lower()
        pool_set: Set[str] = set(pools or [])

        async with self._lock:
            existing = self._agents.get(agent_id)
            if existing:
                normalized_role = role.lower() if role else existing.role
                pool_set.update(existing.pools)
                inherits_from = inherits_from if inherits_from is not None else existing.inherits_from
                existing_meta = existing.metadata
            else:
                existing_meta = {}

            if not pool_set:
                pool_set.update(config.acl.default_agent_pools.get(normalized_role, []))

            metadata_payload = metadata or existing_meta

            async with await self._db_service.get_connection() as db:
                await db.execute(
                    """
                    INSERT INTO acl_agents (agent_id, role, pools, inherits_from, metadata, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(agent_id) DO UPDATE SET
                        role=excluded.role,
                        pools=excluded.pools,
                        inherits_from=excluded.inherits_from,
                        metadata=excluded.metadata,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        agent_id,
                        normalized_role,
                        json.dumps(sorted(pool_set)),
                        inherits_from,
                        json.dumps(metadata_payload or {}),
                    ),
                )
                await db.commit()

            record = ACLAgentRecord(
                agent_id=agent_id,
                role=normalized_role,
                pools=tuple(sorted(pool_set)),
                inherits_from=inherits_from,
                metadata=metadata_payload or {},
            )
            self._agents[agent_id] = record
            await self._clear_permission_cache()
            logger.debug("Registered agent %s role=%s pools=%s", agent_id, normalized_role, record.pools)
            return record

    async def assign_rule(
        self,
        subject_type: str,
        subject_id: str,
        path: str,
        operations: Iterable[str],
        effect: str = "allow",
        priority: int = DEFAULT_PRIORITY,
        created_by: Optional[str] = None,
        inherits_from: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ACLRuleRecord:
        """Create a new ACL rule."""

        await self._ensure_initialized()
        normalized_subject = self._normalize_subject_type(subject_type)
        normalized_id = subject_id or DEFAULT_GLOBAL_SUBJECT
        normalized_ops = self._normalize_operations(operations)
        normalized_effect = self._normalize_effect(effect)
        normalized_priority = priority if priority is not None else DEFAULT_PRIORITY

        async with await self._db_service.get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO acl_rules (
                    subject_type,
                    subject_id,
                    path,
                    operations,
                    effect,
                    priority,
                    inherits_from,
                    description,
                    created_by,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    normalized_subject,
                    normalized_id,
                    path,
                    json.dumps(sorted(normalized_ops)),
                    normalized_effect,
                    normalized_priority,
                    inherits_from,
                    description,
                    created_by,
                ),
            )
            await db.commit()
            rule_id = cursor.lastrowid

        rule = ACLRuleRecord(
            id=rule_id,
            subject_type=normalized_subject,
            subject_id=normalized_id,
            path=path,
            operations=tuple(sorted(normalized_ops)),
            effect=normalized_effect,
            priority=normalized_priority,
            inherits_from=inherits_from,
            description=description,
            created_by=created_by,
            template=False,
            source="db",
        )

        async with self._lock:
            self._append_rule_to_cache(rule)
            await self._clear_permission_cache()
            logger.debug("Assigned ACL rule %s to %s:%s", rule_id, normalized_subject, normalized_id)

        return rule

    async def remove_rule(self, rule_id: int) -> bool:
        """Remove a rule by ID."""

        await self._ensure_initialized()
        subject_key: Optional[SubjectKey] = None
        async with await self._db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT subject_type, subject_id FROM acl_rules WHERE id = ?",
                (rule_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return False
            subject_key = (row["subject_type"], row["subject_id"])
            await db.execute("DELETE FROM acl_rules WHERE id = ?", (rule_id,))
            await db.commit()

        async with self._lock:
            await self._reload_rules_for_subject(subject_key)
            await self._clear_permission_cache()
            logger.debug("Removed ACL rule %s", rule_id)
        return True

    async def list_agents(self) -> List[ACLAgentRecord]:
        await self._ensure_initialized()
        return list(self._agents.values())

    async def list_rules(
        self,
        subject_type: Optional[str] = None,
        subject_id: Optional[str] = None,
    ) -> List[ACLRuleRecord]:
        await self._ensure_initialized()
        if subject_type:
            key = (self._normalize_subject_type(subject_type), subject_id or DEFAULT_GLOBAL_SUBJECT)
            return list(self._rules.get(key, ()))
        rules: List[ACLRuleRecord] = []
        for subject_rules in self._rules.values():
            rules.extend(subject_rules)
        return rules

    async def get_effective_rules(self, agent_id: str) -> List[ACLRuleRecord]:
        """Return all rules that would apply to an agent."""

        await self._ensure_initialized()
        agent = await self._ensure_agent_record(agent_id, {})
        context = {"agent_id": agent.agent_id, "agent_role": agent.role, "agent_pools": list(agent.pools)}
        return self._gather_rules(agent, context)

    async def check_permission(
        self,
        agent_id: str,
        requested_path: str,
        operation: str,
        context: Optional[Dict[str, object]] = None,
    ) -> PermissionDecision:
        """Evaluate whether an agent may perform an operation on a path."""

        if not config.acl.enable_acl:
            return PermissionDecision(True, "ACL disabled")

        await self._ensure_initialized()
        await self._ensure_config_sync()

        prepared_context = self._prepare_context(agent_id, context)
        normalized_operation = operation.lower().strip()
        if normalized_operation not in ALLOWED_OPERATIONS:
            raise ValueError(f"Unsupported operation '{operation}'")

        normalized_path = self._normalize_path(requested_path, prepared_context)

        cached = await self._get_cached_decision(agent_id, normalized_operation, normalized_path)
        if cached:
            allowed, _, reason, rule = cached
            return PermissionDecision(allowed, reason, rule)

        agent = await self._ensure_agent_record(agent_id, prepared_context)
        candidate_rules = self._gather_rules(agent, prepared_context)
        matching_rules = self._match_rules(candidate_rules, normalized_path, normalized_operation, prepared_context)

        decision = self._evaluate_rules(
            agent,
            normalized_path,
            normalized_operation,
            matching_rules,
            prepared_context,
        )

        await self._record_audit(agent.agent_id, normalized_operation, normalized_path, decision)
        await self._store_cached_decision(agent.agent_id, normalized_operation, normalized_path, decision)
        return decision

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_initialized(self) -> None:
        if not self._initialized:
            await self.initialize()

    async def _ensure_config_sync(self) -> None:
        signature = self._compute_config_signature()
        if signature != self._config_signature:
            async with self._lock:
                if signature != self._config_signature:
                    self._load_templates_from_config()
                    self._config_signature = signature
                    await self._clear_permission_cache()
                    logger.info("ACL templates reloaded after config change")

    async def _clear_permission_cache(self) -> None:
        async with self._cache_lock:
            self._decision_cache.clear()

    async def _get_cached_decision(
        self,
        agent_id: str,
        operation: str,
        normalized_path: str,
    ) -> Optional[PermissionCacheEntry]:
        ttl = config.acl.permission_cache_ttl
        if ttl <= 0:
            return None
        now = asyncio.get_running_loop().time()
        async with self._cache_lock:
            entry = self._decision_cache.get((agent_id, operation, normalized_path))
            if not entry:
                return None
            allowed, expiry, reason, rule = entry
            if expiry < now:
                self._decision_cache.pop((agent_id, operation, normalized_path), None)
                return None
            return entry

    async def _store_cached_decision(
        self,
        agent_id: str,
        operation: str,
        normalized_path: str,
        decision: PermissionDecision,
    ) -> None:
        ttl = config.acl.permission_cache_ttl
        if ttl <= 0:
            return
        expiry = asyncio.get_running_loop().time() + ttl
        async with self._cache_lock:
            self._decision_cache[(agent_id, operation, normalized_path)] = (
                decision.allowed,
                expiry,
                decision.reason,
                decision.rule,
            )

    async def _ensure_agent_record(
        self,
        agent_id: str,
        context: Dict[str, object],
    ) -> ACLAgentRecord:
        if agent_id in self._agents:
            return self._agents[agent_id]
        role = context.get("agent_role")
        pools = context.get("agent_pools") or []
        inherits_from = context.get("inherits_from")
        metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else None
        return await self.register_agent(
            agent_id,
            role=role if isinstance(role, str) else None,
            pools=pools if isinstance(pools, (list, tuple, set)) else None,
            inherits_from=inherits_from if isinstance(inherits_from, str) else None,
            metadata=metadata,
        )

    def _gather_rules(
        self,
        agent: ACLAgentRecord,
        context: Dict[str, object],
    ) -> List[ACLRuleRecord]:
        pools: Set[str] = set(context.get("agent_pools") or [])
        pools.update(agent.pools)
        role = agent.role

        rules: List[ACLRuleRecord] = []
        rules.extend(self._rules.get(("agent", agent.agent_id), ()))
        for pool in sorted(pools):
            rules.extend(self._rules.get(("pool", pool), ()))
        rules.extend(self._rules.get(("role", role), ()))
        rules.extend(self._gather_template_rules(role))
        # Global rules apply last
        rules.extend(self._rules.get(("global", DEFAULT_GLOBAL_SUBJECT), ()))

        # Sort rules by priority while maintaining stable order
        return sorted(rules, key=lambda r: (r.priority, r.id or 0))

    def _gather_template_rules(self, role: str, visited: Optional[Set[str]] = None) -> List[ACLRuleRecord]:
        visited = visited or set()
        if role in visited:
            return []
        visited.add(role)
        collected = list(self._template_rules.get(role, ()))
        for parent in self._template_inherits.get(role, ()):  # type: ignore[arg-type]
            collected.extend(self._gather_template_rules(parent, visited))
        return collected

    def _match_rules(
        self,
        rules: Iterable[ACLRuleRecord],
        normalized_path: str,
        operation: str,
        context: Dict[str, object],
    ) -> List[ACLRuleRecord]:
        matched: List[ACLRuleRecord] = []
        for rule in rules:
            if not self._operation_matches(rule, operation):
                continue
            if self._path_matches(rule.path, normalized_path, context):
                matched.append(rule)
        return matched

    def _evaluate_rules(
        self,
        agent: ACLAgentRecord,
        normalized_path: str,
        operation: str,
        rules: List[ACLRuleRecord],
        context: Dict[str, object],
    ) -> PermissionDecision:
        # Deny rules take precedence regardless of priority ordering
        for rule in rules:
            if rule.effect == "deny":
                reason = rule.description or (
                    f"Access denied by ACL rule ({rule.subject_type}:{rule.subject_id})"
                )
                return PermissionDecision(False, reason, rule)

        for rule in rules:
            if rule.effect == "allow":
                reason = rule.description or (
                    f"Access granted by ACL rule ({rule.subject_type}:{rule.subject_id})"
                )
                return PermissionDecision(True, reason, rule)

        # No rule matched; fall back to default permissions
        if operation in self._default_allowed_ops or "all" in self._default_allowed_ops:
            return PermissionDecision(True, "Allowed by default ACL policy")

        reason = (
            f"Access denied: no ACL rule allows {operation} on {normalized_path} for agent {agent.agent_id}"
        )
        return PermissionDecision(False, reason, None)

    def _normalize_subject_type(self, subject_type: str) -> str:
        normalized = subject_type.lower().strip()
        if normalized not in {"agent", "pool", "role", "global"}:
            raise ValueError(f"Unsupported subject type '{subject_type}'")
        return normalized

    def _normalize_operations(self, operations: Iterable[str]) -> Set[str]:
        normalized: Set[str] = set()
        for op in operations:
            if not op:
                continue
            candidate = op.lower().strip()
            if candidate == "all":
                normalized.add("all")
            elif candidate in ALLOWED_OPERATIONS:
                normalized.add(candidate)
            else:
                raise ValueError(f"Unsupported operation '{op}'")
        if not normalized:
            raise ValueError("At least one operation must be specified")
        return normalized

    def _normalize_effect(self, effect: str) -> str:
        candidate = effect.lower().strip()
        if candidate not in {"allow", "deny"}:
            raise ValueError(f"Invalid effect '{effect}'")
        return candidate

    def _prepare_context(
        self,
        agent_id: str,
        context: Optional[Dict[str, object]],
    ) -> Dict[str, object]:
        prepared = dict(context or {})
        prepared.setdefault("agent_id", agent_id)
        if "workspace_root" not in prepared:
            prepared["workspace_root"] = str(config.workspace_root)
        return prepared

    def _normalize_path(self, path: str, context: Dict[str, object]) -> str:
        substituted = self._apply_placeholders(path, context)
        expanded = os.path.expandvars(os.path.expanduser(substituted))
        workspace_root = context.get("workspace_root")
        try:
            if os.path.isabs(expanded):
                norm = Path(expanded).resolve(strict=False)
            elif isinstance(workspace_root, str) and workspace_root:
                norm = Path(workspace_root).joinpath(expanded).resolve(strict=False)
            else:
                norm = Path(expanded).resolve(strict=False)
        except RuntimeError:
            # Fallback if resolution fails due to permissions
            norm = Path(expanded).absolute()
        return os.path.normcase(str(norm))

    def _apply_placeholders(self, value: str, context: Dict[str, object]) -> str:
        workspace = context.get("workspace_root")
        if isinstance(workspace, str) and workspace:
            replacements = {
                "${WORKSPACE}": workspace,
                "$WORKSPACE": workspace,
                "{{WORKSPACE}}": workspace,
                "{WORKSPACE}": workspace,
            }
            for placeholder, replacement in replacements.items():
                value = value.replace(placeholder, replacement)
        return value

    def _contains_glob(self, value: str) -> bool:
        return any(ch in value for ch in ("*", "?", "["))

    def _path_matches(self, rule_path: str, normalized_path: str, context: Dict[str, object]) -> bool:
        normalized_rule_path = os.path.normcase(
            self._normalize_path(rule_path, context)
        )
        if self._contains_glob(normalized_rule_path):
            return fnmatch.fnmatch(normalized_path, normalized_rule_path)
        if normalized_path == normalized_rule_path:
            return True
        prefix = normalized_rule_path.rstrip(os.sep) + os.sep
        return normalized_path.startswith(prefix)

    def _operation_matches(self, rule: ACLRuleRecord, operation: str) -> bool:
        return "all" in rule.operations or operation in rule.operations

    async def _record_audit(
        self,
        agent_id: str,
        operation: str,
        normalized_path: str,
        decision: PermissionDecision,
    ) -> None:
        if not config.acl.audit_access:
            return
        try:
            details = {
                "operation": operation,
                "path": normalized_path,
                "allowed": decision.allowed,
                "reason": decision.reason,
            }
            if decision.rule:
                details.update(
                    {
                        "rule_id": decision.rule.id,
                        "subject_type": decision.rule.subject_type,
                        "subject_id": decision.rule.subject_id,
                        "effect": decision.rule.effect,
                    }
                )
            await audit_service.log_action(
                user_id=None,
                action="acl_allow" if decision.allowed else "acl_deny",
                resource=normalized_path,
                details=json.dumps(details),
            )
        except Exception as exc:  # pragma: no cover - audit failures should not break ACLs
            logger.warning("Failed to record ACL audit event: %s", exc)

    async def _load_agents(self) -> None:
        async with await self._db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT agent_id, role, pools, inherits_from, metadata FROM acl_agents"
            )
            rows = await cursor.fetchall()
        for row in rows:
            pools = []
            try:
                pools = json.loads(row["pools"] or "[]")
            except json.JSONDecodeError:
                pools = []
            metadata = {}
            try:
                metadata = json.loads(row["metadata"] or "{}")
            except json.JSONDecodeError:
                metadata = {}
            record = ACLAgentRecord(
                agent_id=row["agent_id"],
                role=row["role"],
                pools=tuple(pools),
                inherits_from=row["inherits_from"],
                metadata=metadata,
            )
            self._agents[record.agent_id] = record

    async def _load_rules(self) -> None:
        async with await self._db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, subject_type, subject_id, path, operations, effect, priority,
                       inherits_from, description, created_by
                FROM acl_rules
                """
            )
            rows = await cursor.fetchall()
        self._rules.clear()
        for row in rows:
            operations = []
            try:
                operations = json.loads(row["operations"] or "[]")
            except json.JSONDecodeError:
                operations = []
            rule = ACLRuleRecord(
                id=row["id"],
                subject_type=row["subject_type"],
                subject_id=row["subject_id"],
                path=row["path"],
                operations=tuple(sorted(self._normalize_operations(operations))),
                effect=row["effect"],
                priority=row["priority"] or DEFAULT_PRIORITY,
                inherits_from=row["inherits_from"],
                description=row["description"],
                created_by=row["created_by"],
                template=False,
                source="db",
            )
            key = (rule.subject_type, rule.subject_id)
            self._append_rule_to_cache(rule, key)

    def _append_rule_to_cache(self, rule: ACLRuleRecord, key: Optional[SubjectKey] = None) -> None:
        cache_key = key or (rule.subject_type, rule.subject_id)
        current = list(self._rules.get(cache_key, ()))
        current.append(rule)
        self._rules[cache_key] = tuple(sorted(current, key=lambda r: (r.priority, r.id or 0)))

    async def _reload_rules_for_subject(self, subject_key: SubjectKey) -> None:
        subject_type, subject_id = subject_key
        async with await self._db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, path, operations, effect, priority, inherits_from, description, created_by
                FROM acl_rules
                WHERE subject_type = ? AND subject_id = ?
                """,
                (subject_type, subject_id),
            )
            rows = await cursor.fetchall()

        refreshed: List[ACLRuleRecord] = []
        for row in rows:
            try:
                operations = json.loads(row["operations"] or "[]")
            except json.JSONDecodeError:
                operations = []
            refreshed.append(
                ACLRuleRecord(
                    id=row["id"],
                    subject_type=subject_type,
                    subject_id=subject_id,
                    path=row["path"],
                    operations=tuple(sorted(self._normalize_operations(operations))),
                    effect=row["effect"],
                    priority=row["priority"] or DEFAULT_PRIORITY,
                    inherits_from=row["inherits_from"],
                    description=row["description"],
                    created_by=row["created_by"],
                    template=False,
                    source="db",
                )
            )

        if refreshed:
            self._rules[subject_key] = tuple(sorted(refreshed, key=lambda r: (r.priority, r.id or 0)))
        else:
            self._rules.pop(subject_key, None)

    def _load_templates_from_config(self) -> None:
        self._template_rules.clear()
        self._template_inherits.clear()
        self._template_counter = 0

        role_templates: Dict[str, ACLRoleTemplate] = config.acl.default_role_templates
        for role, template in role_templates.items():
            inherits = tuple((template.inherits or []))
            self._template_inherits[role] = inherits
            role_rules: List[ACLRuleRecord] = []
            for rule_def in template.rules:
                operations = self._normalize_operations(rule_def.operations)
                self._template_counter -= 1
                rule = ACLRuleRecord(
                    id=self._template_counter,
                    subject_type="role",
                    subject_id=role,
                    path=rule_def.path,
                    operations=tuple(sorted(operations)),
                    effect=self._normalize_effect(rule_def.effect),
                    priority=rule_def.priority or DEFAULT_PRIORITY,
                    inherits_from=None,
                    description=rule_def.description,
                    created_by="template",
                    template=True,
                    source="template",
                )
                role_rules.append(rule)
            self._template_rules[role] = tuple(sorted(role_rules, key=lambda r: (r.priority, r.id or 0)))

    def _compute_config_signature(self) -> str:
        templates = {
            role: template.model_dump()
            for role, template in config.acl.default_role_templates.items()
        }
        payload = {
            "default_permission": config.acl.default_permission,
            "default_agent_pools": config.acl.default_agent_pools,
            "templates": templates,
        }
        return json.dumps(payload, sort_keys=True, default=list)

    def _parse_default_permission(self, value: str) -> Set[str]:
        if not value:
            return set()
        parts = [part.strip().lower() for part in value.split(",") if part.strip()]
        normalized: Set[str] = set()
        for part in parts:
            if part == "all":
                normalized.add("all")
            elif part in ALLOWED_OPERATIONS:
                normalized.add(part)
        return normalized


acl_manager = ACLManager()
