#!/usr/bin/env python3
"""
Modern Web Search Demonstration

This script demonstrates the new modern web search capabilities including:
- HTTP/2-enabled backends
- LLM-based semantic refinement
- Structured results parsing
- Guardian integration
"""

import asyncio
import json
import time
from typing import Dict, Any

from app.tool.modern_web_search import ModernWebSearch
from app.tool.web_search import WebSearch
from app.config import config


async def demo_modern_search():
    """Demonstrate modern web search features."""
    print("🚀 Modern Web Search Demonstration")
    print("=" * 50)
    
    # Initialize modern search
    search = ModernWebSearch()
    
    # Test queries
    test_queries = [
        {
            "query": "Python async programming best practices",
            "enable_rag": True,
            "backend": "serpapi",
            "description": "Semantic refinement with RAG"
        },
        {
            "query": "machine learning frameworks comparison",
            "enable_rag": False,
            "backend": "brave",
            "description": "Direct search without RAG"
        },
        {
            "query": "HTTP/2 vs HTTP/1.1 performance",
            "enable_rag": True,
            "backend": "duckduckgo",
            "description": "Privacy-focused search with RAG"
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📋 Test Case {i}: {test_case['description']}")
        print(f"Query: {test_case['query']}")
        print(f"Backend: {test_case['backend']}")
        print(f"RAG Enabled: {test_case['enable_rag']}")
        print("-" * 40)
        
        try:
            start_time = time.time()
            
            response = await search.execute(
                query=test_case["query"],
                num_results=5,
                backend=test_case["backend"],
                enable_rag=test_case["enable_rag"],
                fetch_content=False
            )
            
            elapsed = time.time() - start_time
            
            if response.error:
                print(f"❌ Error: {response.error}")
            else:
                print(f"✅ Success! Found {len(response.results)} results in {elapsed:.2f}s")
                
                # Show metadata
                if response.metadata:
                    print(f"\n📊 Metadata:")
                    print(f"  Backend: {response.metadata.backend_used}")
                    print(f"  Query Reformulations: {response.metadata.query_reformulations}")
                    print(f"  RAG Iterations: {response.metadata.rag_iterations}")
                    print(f"  Cache Hits: {response.metadata.cache_hits}")
                    print(f"  HTTP/2: {response.metadata.http2_enabled}")
                    print(f"  Structured Results: {response.metadata.structured_results_enabled}")
                
                # Show top results
                print(f"\n🔍 Top Results:")
                for j, result in enumerate(response.results[:3], 1):
                    print(f"\n{j}. {result.title}")
                    print(f"   URL: {result.url}")
                    if result.description:
                        print(f"   Description: {result.description[:100]}...")
                    if result.rag_reasoning:
                        print(f"   RAG Reasoning: {result.rag_reasoning[:80]}...")
                    if result.result_type:
                        print(f"   Type: {result.result_type}")
                
                # Show reasoning trace (if enabled)
                if response.reasoning_trace and len(response.reasoning_trace) > 0:
                    print(f"\n🧠 Reasoning Trace (last 3 steps):")
                    for step in response.reasoning_trace[-3:]:
                        print(f"   • {step}")
            
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print("\n" + "=" * 50)
    
    # Cleanup
    await search.close()


async def demo_backward_compatibility():
    """Demonstrate backward compatibility with legacy WebSearch."""
    print("\n🔄 Backward Compatibility Demonstration")
    print("=" * 50)
    
    # Use legacy interface
    legacy_search = WebSearch()
    
    try:
        response = await legacy_search.execute(
            query="legacy web search test",
            num_results=3,
            lang="en",
            country="us",
            fetch_content=False
        )
        
        if response.error:
            print(f"❌ Error: {response.error}")
        else:
            print(f"✅ Legacy search successful!")
            print(f"Results: {len(response.results)}")
            
            # Show legacy format output
            print("\n📄 Legacy Output Format:")
            print(response.output)
            
            # Show that it's using modern backend under the hood
            if hasattr(response, 'metadata') and response.metadata:
                if hasattr(response.metadata, 'backend_used'):
                    print(f"\n🔧 Using modern backend: {response.metadata.backend_used}")
                if hasattr(response.metadata, 'rag_iterations'):
                    print(f"🧠 RAG iterations: {response.metadata.rag_iterations}")
    
    except Exception as e:
        print(f"❌ Exception: {e}")


async def demo_performance_comparison():
    """Compare performance with and without RAG."""
    print("\n⚡ Performance Comparison")
    print("=" * 50)
    
    search = ModernWebSearch()
    query = "microservices architecture patterns"
    
    # Test without RAG
    print("🏃‍♂️ Testing without RAG...")
    start = time.time()
    response_no_rag = await search.execute(
        query=query,
        enable_rag=False,
        num_results=5
    )
    time_no_rag = time.time() - start
    
    # Test with RAG
    print("🧠 Testing with RAG...")
    start = time.time()
    response_with_rag = await search.execute(
        query=query,
        enable_rag=True,
        num_results=5
    )
    time_with_rag = time.time() - start
    
    # Compare results
    print(f"\n📊 Performance Comparison:")
    print(f"Without RAG: {time_no_rag:.2f}s, {len(response_no_rag.results)} results")
    print(f"With RAG: {time_with_rag:.2f}s, {len(response_with_rag.results)} results")
    print(f"RAG overhead: {time_with_rag - time_no_rag:.2f}s")
    
    if response_with_rag.metadata:
        print(f"\n🧠 RAG Analysis:")
        print(f"  Query reformulations: {response_with_rag.metadata.query_reformulations}")
        print(f"  RAG iterations: {response_with_rag.metadata.rag_iterations}")
        print(f"  Cache hits: {response_with_rag.metadata.cache_hits}")
    
    await search.close()


def show_configuration():
    """Display current configuration."""
    print("\n⚙️ Current Configuration")
    print("=" * 50)
    
    if config.search_config:
        print(f"Search Backend: {getattr(config.search_config, 'search_backend', 'not set')}")
        print(f"RAG Enabled: {getattr(config.search_config, 'search_rag_enabled', 'not set')}")
        print(f"HTTP/2 Enabled: {getattr(config.search_config, 'enable_http2', 'not set')}")
        print(f"Structured Results: {getattr(config.search_config, 'enable_structured_results', 'not set')}")
        print(f"Max RAG Iterations: {getattr(config.search_config, 'rag_max_iterations', 'not set')}")
        print(f"Cache TTL: {getattr(config.search_config, 'search_cache_ttl', 'not set')}s")
        
        # Check API keys (without revealing them)
        api_keys = {
            'SerpAPI': getattr(config.search_config, 'serpapi_key', None),
            'Brave': getattr(config.search_config, 'brave_api_key', None),
            'Google': getattr(config.search_config, 'google_api_key', None),
        }
        
        print(f"\n🔑 API Keys Status:")
        for name, key in api_keys.items():
            status = "✅ Set" if key else "❌ Not set"
            print(f"  {name}: {status}")
    else:
        print("❌ Search configuration not found")


async def main():
    """Run demonstration."""
    try:
        # Show configuration
        show_configuration()
        
        # Run demonstrations
        await demo_modern_search()
        await demo_backward_compatibility()
        await demo_performance_comparison()
        
        print("\n🎉 Demonstration complete!")
        print("\n💡 To use in your code:")
        print("   from app.tool.modern_web_search import ModernWebSearch")
        print("   search = ModernWebSearch()")
        print("   response = await search.execute('your query')")
        print("\n📚 For more info, see MODERN_WEB_SEARCH_README.md")
        
    except KeyboardInterrupt:
        print("\n👋 Demonstration interrupted")
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())