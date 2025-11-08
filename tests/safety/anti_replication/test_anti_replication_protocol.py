import datetime
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.config import config
from app.safety import (
    AgentProcess,
    AuditEntry,
    CodeIntegrityViolation,
    CodeSignature,
    CodeSigner,
    ExternalAuditLog,
    FilePermissionMatrix,
    FileSystemPermissionManager,
    HardwareLevelEnforcer,
    HardwareSecurityModule,
    ImmutabilityError,
    ImmutableCore,
    MultiLayerVerification,
    MultiLayerVerificationError,
    Operation,
    PermissionDeniedError,
    PermissionMatrix,
    Platform,
    VerificationLayer,
    ReadOnlyCodeReference,
    ReplicationBlocker,
    ReplicationAttemptDetected,
    ReplicationMonitor,
    ReplicationVector,
    SignatureRegistry,
    SignatureVerifier,
)
from app.safety.crypto_verification import compute_hash_from_bytes, safe_file_read
from app.safety.hw_level_enforcement import Constraint


def test_immutable_core_detects_tampering(tmp_path: Path) -> None:
    code_dir = tmp_path / "agent"
    code_dir.mkdir()
    target_file = code_dir / "main.py"
    target_file.write_text("print('safe')\n", encoding="utf-8")

    core = ImmutableCore([code_dir])
    core.initialize()

    target_file.write_text("print('tampered')\n", encoding="utf-8")

    with pytest.raises(CodeIntegrityViolation):
        core.verify_integrity()


def test_replication_blocker_triggers_on_forbidden_action() -> None:
    blocker = ReplicationBlocker()

    with pytest.raises(ReplicationAttemptDetected):
        blocker.enforce(ReplicationVector.FILE_SYSTEM, "Creating new agent instances/processes")


def test_permission_matrix_enforces_no_self_modification() -> None:
    matrix = PermissionMatrix()

    matrix.enforce("read", "own_code")

    with pytest.raises(PermissionDeniedError):
        matrix.enforce("write", "own_code")


def test_filesystem_permission_manager_blocks_writes(tmp_path: Path) -> None:
    ro_root = tmp_path / "app"
    rw_root = tmp_path / "data"
    ro_root.mkdir()
    rw_root.mkdir()

    manager = FileSystemPermissionManager(
        FilePermissionMatrix(
            read_only_paths=[ro_root],
            writable_paths=[rw_root],
            forbidden_paths=[tmp_path / "system"],
        )
    )

    with pytest.raises(PermissionDeniedError):
        manager.assert_write_allowed(ro_root / "agent.py")

    manager.assert_write_allowed(rw_root / "output.log")


def test_external_audit_log_chain_is_tamper_evident() -> None:
    audit = ExternalAuditLog()
    entry_one = audit.record("decision", {"action": "test"}, "HASH1")
    entry_two = audit.record("decision", {"action": "test-2"}, "HASH2")

    assert audit.verify_chain()
    assert entry_one.chain_hash != entry_two.chain_hash

    audit._entries.append(
        AuditEntry(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            action="tamper",
            details={},
            code_hash="HASH2",
            chain_hash="invalid",
        )
    )

    assert not audit.verify_chain()


def test_crypto_safe_read_detects_tampering(tmp_path: Path) -> None:
    source = tmp_path / "core.py"
    source.write_text("print('secure')\n", encoding="utf-8")

    code_hash = compute_hash_from_bytes(source.read_bytes())
    signer = CodeSigner("unit-test-key")
    signature = signer.sign(code_hash)

    registry = SignatureRegistry()
    registry.register(source, CodeSignature(code_hash=code_hash, signature=signature))
    verifier = SignatureVerifier(public_key="unit-test-key")

    assert "secure" in safe_file_read(source, registry, verifier)

    source.write_text("print('modified')\n", encoding="utf-8")

    with pytest.raises(CodeIntegrityViolation):
        safe_file_read(source, registry, verifier)


def test_replication_monitor_blocks_blocked_category() -> None:
    monitor = ReplicationMonitor()

    with pytest.raises(ReplicationAttemptDetected):
        monitor.record_event("file_creation", "/tmp/agent.py")

    allowed_event = monitor.record_event(
        "audit", "/tmp/log", allowed=True, details={"note": "safe"}
    )

    assert allowed_event.allowed is True
    assert monitor.status()["events_recorded"] == "2"


def test_multi_layer_verification_reports_violation(tmp_path: Path) -> None:
    code_dir = tmp_path / "agent"
    code_dir.mkdir()
    file_path = code_dir / "main.py"
    file_path.write_text("print('ok')\n", encoding="utf-8")

    core = ImmutableCore([code_dir])
    core.initialize()

    verifier = MultiLayerVerification()
    verifier.register_layer(
        VerificationLayer(
            name="immutable_core",
            description="Validates immutable code hash",
            check=lambda: core.verify_integrity(),
        )
    )

    verifier.verify_all_layers()

    file_path.write_text("print('tampered')\n", encoding="utf-8")

    with pytest.raises(MultiLayerVerificationError):
        verifier.verify_all_layers()


def test_agent_process_cannot_modify_code() -> None:
    code_reference = ReadOnlyCodeReference("print('safety')")
    agent = AgentProcess(code_reference)

    assert "safety" in agent.run()

    with pytest.raises(ImmutabilityError):
        code_reference.write("print('mod')")

    with pytest.raises(ImmutabilityError):
        agent.attempt_self_modification("print('mod')")


def test_hardware_enforcer_blocks_child_process(tmp_path: Path) -> None:
    allowed_dir = tmp_path / "data"
    allowed_dir.mkdir()

    enforcer = HardwareLevelEnforcer(
        {
            Platform.LINUX: Constraint(
                allowed_file_roots=[allowed_dir],
                read_only_roots=[tmp_path / "app"],
                allowed_network_endpoints=["monitor.openmanus.local"],
            )
        }
    )

    decision = enforcer.enforce(
        Platform.LINUX, Operation.FILE_WRITE, target=str(allowed_dir / "log.txt")
    )
    assert decision.allowed

    with pytest.raises(PermissionDeniedError):
        enforcer.ensure_allowed(Platform.LINUX, Operation.NETWORK_IO, target="untrusted")


def test_hsm_signatures_integrate_with_verifier() -> None:
    hsm = HardwareSecurityModule(endpoint="https://hsm.example.com", device_id="openmanus_001")
    hsm.configure_signer("shared-test-key")

    code_hash = "abc123"
    signature = hsm.sign(code_hash)

    verifier = SignatureVerifier(public_key="shared-test-key")
    assert verifier.verify(code_hash, signature)


def test_config_safety_section_loaded() -> None:
    safety_settings = config.safety
    assert safety_settings.anti_replication.enabled is True
    assert safety_settings.integrity.check_interval_seconds == 60
