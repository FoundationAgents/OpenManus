#!/usr/bin/env python3
"""
Demo script showing how to use the LLM API integration with OpenAI-compatible endpoints.

This demonstrates:
1. Basic API client usage with streaming
2. Fallback mechanism for handling failures
3. Context management with token tracking
4. Token usage monitoring
5. Health checking
"""

import asyncio
import sys

from app.config import config
from app.llm.api_client import OpenAICompatibleClient
from app.llm.api_fallback import APIFallbackManager
from app.llm.context_manager import ContextManager
from app.llm.token_counter import TokenCounter, TokenBudget
from app.llm.health_check import HealthChecker, HealthStatus
from app.logger import logger


async def demo_basic_client():
    """Demo: Basic API client usage."""
    print("\n=== Demo 1: Basic API Client ===")
    
    client = OpenAICompatibleClient(
        endpoint="https://gpt4free.pro/v1/vibingfox/chat/completions",
        model="claude-sonnet-4.5",
        timeout=120,
    )
    
    # Check if endpoint is available
    is_available = await client.health_check()
    print(f"Endpoint available: {is_available}")
    
    if is_available:
        # Prepare messages
        messages = [
            {"role": "user", "content": "What is 2+2? Answer briefly."}
        ]
        
        # Stream response
        print("\nStreaming response:")
        response_text = ""
        try:
            async for token in await client.create_completion(
                messages=messages,
                stream=True,
                max_tokens=100,
            ):
                print(token, end="", flush=True)
                response_text += token
            print("\n")
        except Exception as e:
            print(f"Error: {e}")
    
    # Show token usage
    usage = client.get_token_usage()
    print(f"Token usage: {usage}")
    
    await client.close()


async def demo_fallback_mechanism():
    """Demo: Fallback mechanism."""
    print("\n=== Demo 2: Fallback Mechanism ===")
    
    fallback_endpoints = [
        {
            "url": "https://gpt4free.pro/v1/vibingfox/chat/completions",
            "model": "claude-sonnet-4.5",
            "priority": 2,
        }
    ]
    
    manager = APIFallbackManager(
        primary_endpoint="https://gpt4free.pro/v1/vibingfox/chat/completions",
        primary_model="claude-sonnet-4.5",
        fallback_endpoints=fallback_endpoints,
    )
    
    # Show endpoint status
    status = manager.get_endpoint_status()
    print("Endpoint status:")
    for url, endpoint_status in status.items():
        print(f"  {url}: {endpoint_status}")
    
    # Try a query
    messages = [
        {"role": "user", "content": "Say 'Hello from fallback manager!'"}
    ]
    
    print("\nAttempting query with fallback mechanism:")
    try:
        response = await manager.query(
            messages=messages,
            stream=False,
            max_tokens=100,
        )
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")


async def demo_context_management():
    """Demo: Context management."""
    print("\n=== Demo 3: Context Management ===")
    
    manager = ContextManager(max_tokens=1000, compression_threshold=0.9)
    
    # Set system message
    manager.set_system_message("You are a helpful assistant specializing in Python.")
    print("Set system message")
    
    # Add messages
    manager.add_message("user", "What is Python?", importance=0.9)
    manager.add_message("assistant", "Python is a high-level programming language.")
    manager.add_message("user", "Can you give an example?")
    manager.add_message("assistant", "Sure! Here's a simple example: print('Hello, World!')")
    
    # Show context status
    status = manager.get_status()
    print(f"Context status: {status}")
    
    # Get formatted context
    context = manager.get_context()
    print(f"\nFormatted context ({len(context)} messages):")
    for msg in context:
        content_preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
        print(f"  {msg['role']}: {content_preview}")
    
    # Check if we can add more messages
    can_add = manager.can_add_message("This is a test message.")
    print(f"\nCan add more messages: {can_add}")
    print(f"Available tokens: {manager.get_available_tokens()}")


async def demo_token_tracking():
    """Demo: Token usage tracking."""
    print("\n=== Demo 4: Token Usage Tracking ===")
    
    counter = TokenCounter(request_limit=10, time_window=60)
    
    # Simulate API calls
    print("Recording token usage:")
    counter.record_usage(input_tokens=50, output_tokens=30, model="gpt-4")
    print("  Request 1: 50 input, 30 output tokens")
    
    counter.record_usage(input_tokens=100, output_tokens=50, model="gpt-4")
    print("  Request 2: 100 input, 50 output tokens")
    
    counter.record_usage(input_tokens=75, output_tokens=40, model="gpt-4")
    print("  Request 3: 75 input, 40 output tokens")
    
    # Show statistics
    stats = counter.get_usage_stats()
    print(f"\nUsage statistics:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Average tokens per request: {stats['average_tokens_per_request']}")
    
    # Show window statistics (last minute)
    window_stats = counter.get_window_stats(minutes=1)
    print(f"\nWindow statistics (last 1 minute):")
    print(f"  Requests in window: {window_stats['window_requests']}")
    print(f"  Tokens in window: {window_stats['window_tokens']}")
    
    # Check rate limits
    is_ok, msg = counter.check_rate_limit()
    print(f"\nRate limit check: {'OK' if is_ok else 'LIMITED'}")
    if not is_ok:
        print(f"  Message: {msg}")
    print(f"  Requests remaining: {counter.get_requests_remaining()}/10")
    
    # Show daily statistics
    daily_stats = counter.get_daily_stats()
    print(f"\nDaily statistics: {daily_stats}")


async def demo_token_budget():
    """Demo: Token budget management."""
    print("\n=== Demo 5: Token Budget ===")
    
    budget = TokenBudget(daily_budget=10000, warning_threshold=0.8)
    
    # Use tokens
    print("Using tokens from budget:")
    
    status = budget.use_tokens(3000)
    print(f"  Used 3000 tokens: {status}")
    
    status = budget.use_tokens(5000)
    print(f"  Used 5000 tokens: {status}")
    if "warning" in status:
        print(f"    ⚠️  {status['warning']}")
    
    # Show final budget
    final_status = budget.get_status()
    print(f"\nFinal budget status: {final_status}")


async def demo_health_checking():
    """Demo: Endpoint health checking."""
    print("\n=== Demo 6: Health Checking ===")
    
    checker = HealthChecker(check_interval=5, timeout=10)
    
    # Register endpoints
    checker.register_endpoint(
        "https://gpt4free.pro/v1/vibingfox/chat/completions",
        "claude-sonnet-4.5"
    )
    
    print("Registered endpoint for health monitoring")
    
    # Perform a single health check
    print("\nPerforming health check...")
    status = await checker.check_endpoint(
        "https://gpt4free.pro/v1/vibingfox/chat/completions"
    )
    print(f"  Status: {status.value}")
    emoji = checker.get_status_emoji(status)
    print(f"  Emoji: {emoji} {status.value.upper()}")
    
    # Get overall status
    overall = checker.get_overall_status()
    print(f"\nOverall system status: {checker.get_status_emoji(overall)} {overall.value}")
    
    # Show endpoint details
    endpoint_status = checker.get_status("https://gpt4free.pro/v1/vibingfox/chat/completions")
    print(f"Endpoint details: {endpoint_status}")


async def demo_full_workflow():
    """Demo: Complete workflow."""
    print("\n=== Demo 7: Full Workflow ===")
    
    # Initialize components
    print("Initializing components...")
    
    context_manager = ContextManager(max_tokens=2000)
    token_counter = TokenCounter()
    health_checker = HealthChecker()
    
    # Register endpoint
    health_checker.register_endpoint(
        "https://gpt4free.pro/v1/vibingfox/chat/completions",
        "claude-sonnet-4.5"
    )
    
    # Set system message
    context_manager.set_system_message(
        "You are a helpful assistant. Keep responses concise."
    )
    
    # Add user query to context
    user_query = "What is machine learning?"
    context_manager.add_message("user", user_query)
    
    print(f"Query: {user_query}")
    print(f"Context tokens: {context_manager.current_tokens}/{context_manager.max_tokens}")
    
    # Check endpoint health
    print("\nChecking endpoint health...")
    status = await health_checker.check_endpoint(
        "https://gpt4free.pro/v1/vibingfox/chat/completions"
    )
    print(f"Endpoint status: {health_checker.get_status_emoji(status)} {status.value}")
    
    if status == HealthStatus.CONNECTED:
        # Prepare to make request
        print("\nPreparing API request...")
        
        # Create API client
        client = OpenAICompatibleClient(
            endpoint="https://gpt4free.pro/v1/vibingfox/chat/completions",
            model="claude-sonnet-4.5",
        )
        
        # Get context
        messages = context_manager.get_context()
        print(f"Sending {len(messages)} messages to API")
        
        # Estimate tokens
        estimated_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        token_counter.record_usage(estimated_tokens, 0)
        
        print(f"Estimated input tokens: {estimated_tokens}")
        
        # Show token stats
        stats = token_counter.get_usage_stats()
        print(f"Token usage: {stats['total_requests']} requests, {stats['total_tokens']} total tokens")
        
        await client.close()
    else:
        print(f"Endpoint offline or degraded, using fallback...")


async def main():
    """Run all demos."""
    print("=" * 60)
    print("LLM API Integration Demos")
    print("=" * 60)
    
    try:
        await demo_basic_client()
        await demo_fallback_mechanism()
        await demo_context_management()
        await demo_token_tracking()
        await demo_token_budget()
        await demo_health_checking()
        await demo_full_workflow()
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
    
    print("\n" + "=" * 60)
    print("Demo completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
