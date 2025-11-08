#!/usr/bin/env python3
"""
Example demonstrating the Dynamic Permission & Capability System

Shows how agents request capabilities, Guardian evaluates risk,
and users manage grants and revocations.
"""

import asyncio
from app.security.permissions import (
    CapabilityRequest,
    DynamicPermissionManager,
    DecisionType,
    RiskLevel,
    ResourceLimits,
    get_permission_manager,
)


async def example_safe_compile_request():
    """Example 1: Safe compile request (should AUTO_GRANT)"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Safe Compile Request")
    print("="*60)
    
    manager = get_permission_manager()
    
    request = CapabilityRequest(
        agent_id="dev_agent_1",
        agent_type="SWEAgent",
        tools=["compiler", "debugger"],
        env_vars={"PATH": "/usr/bin", "CC": "gcc"},
        paths=["/home/user/project/src", "/tmp"],
        network=False,
        command="gcc -c src/main.c -o build/main.o",
        task_description="Compile C source code with GCC",
        resource_limits=ResourceLimits(
            max_memory_mb=512,
            max_cpu_percent=50,
            timeout_seconds=300,
        ),
    )
    
    decision = await manager.request_capability(request)
    
    print(f"Decision: {decision.decision_type.value}")
    if decision.decision_type == DecisionType.AUTO_GRANT:
        grant = decision.grant
        print(f"✓ GRANTED")
        print(f"  - Tools: {', '.join(grant.granted_tools)}")
        print(f"  - Network: {grant.network_allowed}")
        print(f"  - Memory Limit: {grant.resource_limits.max_memory_mb} MB")
        print(f"  - TTL: {grant.ttl_seconds} seconds")
        print(f"  - Grant ID: {grant.grant_id}")
        print(f"  - Revocation Token: {grant.revocation_token}")


async def example_medium_risk_network_request():
    """Example 2: Medium-risk network request (should REQUIRE_CONFIRMATION)"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Medium-Risk Network Request")
    print("="*60)
    
    manager = get_permission_manager()
    
    request = CapabilityRequest(
        agent_id="network_agent_1",
        agent_type="NetworkAgent",
        tools=["http_client", "dns"],
        env_vars={"PROXY": "http://proxy.example.com:8080"},
        paths=["/tmp/network_cache"],
        network=True,
        command="curl -X POST http://api.example.com/data",
        task_description="Query external API and process response",
        resource_limits=ResourceLimits(
            max_network_bandwidth_mbps=50,
            timeout_seconds=60,
        ),
    )
    
    decision = await manager.request_capability(request)
    
    print(f"Decision: {decision.decision_type.value}")
    if decision.decision_type == DecisionType.REQUIRE_CONFIRMATION:
        print("⚠ REQUIRES USER CONFIRMATION")
        details = decision.confirmation_required
        print(f"  Agent: {details['agent_id']} ({details['agent_type']})")
        print(f"  Requested Tools: {', '.join(details['requested_tools'])}")
        print(f"  Network Access: {details['network_access']}")
        print(f"  File Paths: {', '.join(details['file_paths'])}")
        print(f"  Risk Reasons:")
        for reason in details['risk_reasons']:
            print(f"    - {reason}")
        print(f"  Agent Trust Score: {details['trust_score']:.2f}")


async def example_high_risk_request_denied():
    """Example 3: High-risk request (should AUTO_DENY)"""
    print("\n" + "="*60)
    print("EXAMPLE 3: High-Risk Request (System Deletion Pattern)")
    print("="*60)
    
    manager = get_permission_manager()
    
    request = CapabilityRequest(
        agent_id="suspicious_agent",
        agent_type="GenericAgent",
        tools=["delete", "system32_access", "powershell"],
        env_vars={"ADMIN": "true"},
        paths=["/etc/shadow", "C:\\Windows\\System32"],
        network=True,
        command="rm -rf /",
        task_description="Cleanup system files",
        resource_limits=ResourceLimits(
            max_memory_mb=16000,
            timeout_seconds=600,
        ),
    )
    
    decision = await manager.request_capability(request)
    
    print(f"Decision: {decision.decision_type.value}")
    if decision.decision_type == DecisionType.AUTO_DENY:
        deny = decision.deny
        print(f"✗ DENIED")
        print(f"  Risk Level: {deny.risk_level.value.upper()}")
        print(f"  Reason: {deny.denied_reason}")
        print(f"  Denied Capabilities: {', '.join(deny.denied_capabilities)}")
        print(f"  Audit ID: {deny.audit_id}")


async def example_incompatible_tool_request():
    """Example 4: Incompatible tool for agent type"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Incompatible Tool Request")
    print("="*60)
    
    manager = get_permission_manager()
    
    # NetworkAgent trying to use CUDA (game development tool)
    request = CapabilityRequest(
        agent_id="network_agent_2",
        agent_type="NetworkAgent",
        tools=["cuda", "http_client"],  # CUDA not compatible with NetworkAgent
        env_vars={"CUDA_PATH": "/usr/local/cuda"},
        paths=["/usr/local/cuda"],
        network=True,
        task_description="Network processing with CUDA",
    )
    
    decision = await manager.request_capability(request)
    
    print(f"Decision: {decision.decision_type.value}")
    if decision.decision_type == DecisionType.AUTO_DENY:
        deny = decision.deny
        print(f"✗ DENIED")
        print(f"  Risk Level: {deny.risk_level.value.upper()}")
        print(f"  Reason: {deny.denied_reason}")
    elif decision.decision_type == DecisionType.REQUIRE_CONFIRMATION:
        print("⚠ REQUIRES CONFIRMATION due to incompatible tools")
        details = decision.confirmation_required
        print(f"  Risk Reasons:")
        for reason in details['risk_reasons']:
            print(f"    - {reason}")


async def example_caching_behavior():
    """Example 5: Demonstrate caching behavior"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Caching Behavior")
    print("="*60)
    
    manager = get_permission_manager()
    
    request = CapabilityRequest(
        agent_id="cache_test_agent",
        agent_type="SWEAgent",
        tools=["compiler"],
        paths=["/home/user/project"],
        network=False,
    )
    
    print("First request (should be evaluated):")
    decision1 = await manager.request_capability(request)
    grant_id_1 = decision1.grant.grant_id if decision1.grant else None
    print(f"  Decision: {decision1.decision_type.value}")
    if grant_id_1:
        print(f"  Grant ID: {grant_id_1}")
    
    print("\nSecond request (should hit cache):")
    decision2 = await manager.request_capability(request)
    grant_id_2 = decision2.grant.grant_id if decision2.grant else None
    print(f"  Decision: {decision2.decision_type.value}")
    if grant_id_2:
        print(f"  Grant ID: {grant_id_2}")
    
    if grant_id_1 == grant_id_2:
        print("\n✓ Cache hit confirmed - same grant returned")
    else:
        print("\n✗ Different grants returned")


async def example_revocation():
    """Example 6: Grant revocation"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Grant Revocation")
    print("="*60)
    
    manager = get_permission_manager()
    
    # First, get a grant
    request = CapabilityRequest(
        agent_id="revocation_test_agent",
        agent_type="SWEAgent",
        tools=["debugger"],
        paths=["/home/user/project"],
        network=False,
    )
    
    decision = await manager.request_capability(request)
    
    if decision.decision_type == DecisionType.AUTO_GRANT:
        grant = decision.grant
        print(f"Grant created:")
        print(f"  Grant ID: {grant.grant_id}")
        print(f"  Tools: {', '.join(grant.granted_tools)}")
        print(f"  Expires: {grant.expires_at}")
        
        # Now revoke it
        print(f"\nRevoking grant...")
        success = await manager.revoke_grant(
            grant.grant_id,
            grant.revocation_token,
            "Debugger session completed"
        )
        
        if success:
            print("✓ Grant successfully revoked")
        else:
            print("✗ Revocation failed")


async def example_active_grants():
    """Example 7: Query active grants for an agent"""
    print("\n" + "="*60)
    print("EXAMPLE 7: Active Grants Query")
    print("="*60)
    
    manager = get_permission_manager()
    
    agent_id = "query_test_agent"
    
    # Create a few grants
    for i in range(2):
        request = CapabilityRequest(
            agent_id=agent_id,
            agent_type="SWEAgent",
            tools=["compiler"] if i == 0 else ["debugger"],
            paths=["/home/user/project"],
            network=False,
        )
        await manager.request_capability(request)
    
    # Query active grants
    active_grants = await manager.get_active_grants(agent_id)
    
    print(f"Active grants for agent '{agent_id}':")
    if active_grants:
        for grant in active_grants:
            print(f"  - Grant ID: {grant.grant_id}")
            print(f"    Tools: {', '.join(grant.granted_tools)}")
            print(f"    Created: {grant.timestamp}")
            print(f"    Expires: {grant.expires_at}")
    else:
        print("  (No active grants)")


async def example_audit_trail():
    """Example 8: Audit trail"""
    print("\n" + "="*60)
    print("EXAMPLE 8: Audit Trail")
    print("="*60)
    
    manager = get_permission_manager()
    
    # Create some activity
    request = CapabilityRequest(
        agent_id="audit_test_agent",
        agent_type="SWEAgent",
        tools=["compiler"],
        paths=["/home/user/project"],
        network=False,
    )
    
    await manager.request_capability(request)
    
    # Get audit log
    audit_logs = await manager.get_audit_log(
        agent_id="audit_test_agent",
        limit=10
    )
    
    print(f"Audit log entries for 'audit_test_agent':")
    for entry in audit_logs:
        print(f"  - Action: {entry['action']}")
        print(f"    Timestamp: {entry['created_at']}")
        print(f"    Request ID: {entry['request_id']}")
        print(f"    Metadata: {entry['metadata']}")


async def main():
    """Run all examples"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  Dynamic Permission & Capability System Examples".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    try:
        await example_safe_compile_request()
        await example_medium_risk_network_request()
        await example_high_risk_request_denied()
        await example_incompatible_tool_request()
        await example_caching_behavior()
        await example_revocation()
        await example_active_grants()
        await example_audit_trail()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
