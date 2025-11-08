"""
Example demonstrating the Network Toolkit capabilities.

This example shows:
- HTTP requests with caching
- Guardian security policies
- Rate limiting
- DNS lookups and ping
"""

import asyncio
from app.network import (
    HTTPClientWithCaching,
    HTTPClientConfig,
    Guardian,
    NetworkPolicy,
    OperationType,
    NetworkDiagnostics,
)


async def http_example():
    """Demonstrate HTTP client with caching."""
    print("\n=== HTTP Client Example ===\n")
    
    # Configure HTTP client
    config = HTTPClientConfig(
        enable_cache=True,
        cache_default_ttl=300,
        enable_rate_limiting=True,
        rate_limit_per_second=5.0
    )
    
    async with HTTPClientWithCaching(config=config) as client:
        # First request - hits network
        print("Making first request to httpbin.org...")
        response = await client.get("https://httpbin.org/json")
        print(f"Status: {response.status_code}")
        print(f"From cache: {response.from_cache}")
        print(f"Request time: {response.request_time:.3f}s")
        
        # Second request - from cache
        print("\nMaking second request (should be cached)...")
        response = await client.get("https://httpbin.org/json")
        print(f"Status: {response.status_code}")
        print(f"From cache: {response.from_cache}")
        print(f"Request time: {response.request_time:.3f}s")
        
        # Get cache statistics
        stats = client.get_cache_stats()
        print(f"\nCache stats:")
        print(f"  Hit rate: {stats['hit_rate']}")
        print(f"  Entries: {stats['entry_count']}")


async def guardian_example():
    """Demonstrate Guardian security policies."""
    print("\n=== Guardian Security Example ===\n")
    
    # Create custom policy
    policy = NetworkPolicy(
        name="strict_policy",
        description="Strict security policy",
        allowed_operations={OperationType.HTTP_GET},
        blocked_hosts=[r".*\.onion"],  # Block Tor addresses
        allowed_ports=[80, 443],  # Only HTTP/HTTPS
        require_confirmation=[OperationType.HTTP_POST]
    )
    
    guardian = Guardian(policy)
    
    # Test allowed request
    print("Testing allowed request...")
    assessment = guardian.assess_risk(
        operation=OperationType.HTTP_GET,
        host="api.github.com",
        port=443
    )
    print(f"Risk level: {assessment.level.value}")
    print(f"Approved: {assessment.approved}")
    print(f"Reasons: {', '.join(assessment.reasons)}")
    
    # Test blocked request
    print("\nTesting blocked request...")
    assessment = guardian.assess_risk(
        operation=OperationType.HTTP_GET,
        host="localhost",
        port=8080
    )
    print(f"Risk level: {assessment.level.value}")
    print(f"Approved: {assessment.approved}")
    print(f"Reasons: {', '.join(assessment.reasons)}")


async def diagnostics_example():
    """Demonstrate network diagnostics."""
    print("\n=== Network Diagnostics Example ===\n")
    
    diagnostics = NetworkDiagnostics()
    
    # DNS lookup
    print("DNS lookup for google.com...")
    result = await diagnostics.dns_lookup("google.com", record_type="A")
    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"IP addresses: {', '.join(result.ip_addresses)}")
        print(f"Resolution time: {result.resolution_time:.3f}s")
    
    # Ping
    print("\nPinging google.com...")
    result = await diagnostics.ping("google.com", count=4)
    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Packets: {result.packets_received}/{result.packets_sent}")
        print(f"Packet loss: {result.packet_loss}%")
        if result.avg_rtt:
            print(f"Average RTT: {result.avg_rtt:.2f}ms")


async def main():
    """Run all examples."""
    print("Network Toolkit Examples")
    print("=" * 50)
    
    try:
        # HTTP client example
        await http_example()
    except Exception as e:
        print(f"HTTP example error: {e}")
    
    # Guardian example
    await guardian_example()
    
    try:
        # Diagnostics example
        await diagnostics_example()
    except Exception as e:
        print(f"Diagnostics example error: {e}")
    
    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
