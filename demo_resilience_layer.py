#!/usr/bin/env python3
"""
Agent Resilience Layer Demo

Demonstrates health monitoring, failure detection, and automatic agent replacement.
"""

import asyncio
import time
import random
from typing import Dict, Any

from app.flow.multi_agent_environment import (
    AutonomousMultiAgentEnvironment,
    DevelopmentTask,
    AgentRole,
    TaskPriority
)
from app.agents.resilience import (
    AgentResilienceManager,
    ResilienceConfig,
    HealthStatus
)
from app.config import ResilienceSettings
from app.logger import logger


class FailingAgent:
    """Simulates a failing agent for demonstration"""
    
    def __init__(self, agent_id: str, resilience_manager: AgentResilienceManager):
        self.agent_id = agent_id
        self.resilience_manager = resilience_manager
        self.failure_rate = 0.3  # 30% failure rate
        self.consecutive_failures = 0
    
    async def simulate_work(self):
        """Simulate agent work with potential failures"""
        for i in range(20):  # Simulate 20 work items
            await asyncio.sleep(0.5)  # Simulate work duration
            
            if random.random() < self.failure_rate:
                # Simulate failure
                error_msg = f"Simulated error {i+1} in {self.agent_id}"
                self.resilience_manager.update_agent_error(self.agent_id, error_msg)
                self.consecutive_failures += 1
                logger.warning(f"Agent {self.agent_id} failed: {error_msg}")
            else:
                # Simulate success
                latency = random.uniform(0.1, 2.0)
                self.resilience_manager.update_agent_success(self.agent_id, latency)
                self.consecutive_failures = 0
                logger.info(f"Agent {self.agent_id} completed work in {latency:.2f}s")


async def demo_basic_health_monitoring():
    """Demonstrate basic health monitoring"""
    print("\n=== Basic Health Monitoring Demo ===")
    
    # Create environment with resilience
    resilience_config = ResilienceSettings(
        health_check_interval=2.0,
        max_consecutive_errors=3,
        min_health_score=0.4,
        enable_auto_replacement=False  # Disable for demo control
    )
    
    env = AutonomousMultiAgentEnvironment(resilience_config)
    resilience_manager = env.get_resilience_manager()
    
    # Get initial status
    status = resilience_manager.get_resilience_status()
    print(f"Initial agents: {status['health_summary']['total_agents']}")
    print(f"Initial health: {status['health_summary']['average_health_score']:.2f}")
    
    # Simulate some activity
    print("\nSimulating agent activity...")
    for i in range(10):
        # Randomly update some agents
        agents = list(resilience_manager.health_monitor.get_all_telemetry().keys())
        if agents:
            agent_id = random.choice(agents)
            
            if random.random() < 0.3:  # 30% chance of error
                resilience_manager.update_agent_error(agent_id, f"Demo error {i}")
            else:
                resilience_manager.update_agent_success(agent_id, random.uniform(0.1, 1.0))
        
        await asyncio.sleep(0.5)
    
    # Check updated status
    status = resilience_manager.get_resilience_status()
    print(f"Updated health: {status['health_summary']['average_health_score']:.2f}")
    print(f"Healthy agents: {status['health_summary']['healthy_agents']}")
    print(f"Unhealthy agents: {status['health_summary']['unhealthy_agents']}")
    
    # Show recent events
    events = status['recent_events'][:5]
    print("\nRecent events:")
    for event in events:
        print(f"  {event.type.value}: {event.description}")
    
    env.shutdown()


async def demo_failure_detection():
    """Demonstrate failure detection"""
    print("\n=== Failure Detection Demo ===")
    
    # Create environment with sensitive thresholds
    resilience_config = ResilienceSettings(
        health_check_interval=1.0,
        max_consecutive_errors=2,  # Very sensitive
        min_health_score=0.6,
        enable_auto_replacement=False
    )
    
    env = AutonomousMultiAgentEnvironment(resilience_config)
    resilience_manager = env.get_resilience_manager()
    
    # Get an agent to simulate failures
    agents = list(resilience_manager.health_monitor.get_all_telemetry().keys())
    if agents:
        test_agent = agents[0]
        print(f"Simulating failures for agent: {test_agent}")
        
        # Simulate consecutive failures
        for i in range(4):  # Exceed threshold of 2
            resilience_manager.update_agent_error(test_agent, f"Induced error {i+1}")
            await asyncio.sleep(0.5)
        
        # Check if failure was detected
        telemetry = resilience_manager.health_monitor.get_agent_telemetry(test_agent)
        print(f"Agent health score: {telemetry.get_health_score():.2f}")
        print(f"Agent status: {telemetry.get_status().value}")
        
        # Check events
        events = resilience_manager.health_monitor.get_recent_events()
        failure_events = [e for e in events if e.type.value == "failure_detected"]
        print(f"Failure detection events: {len(failure_events)}")
        
        for event in failure_events[-3:]:  # Show last 3
            print(f"  - {event.description}")
    
    env.shutdown()


async def demo_automatic_replacement():
    """Demonstrate automatic agent replacement"""
    print("\n=== Automatic Replacement Demo ===")
    
    # Create environment with auto-replacement enabled
    resilience_config = ResilienceSettings(
        health_check_interval=1.0,
        max_consecutive_errors=3,
        min_health_score=0.3,
        enable_auto_replacement=True,
        replacement_delay=2.0,
        max_replacements_per_hour=10
    )
    
    env = AutonomousMultiAgentEnvironment(resilience_config)
    resilience_manager = env.get_resilience_manager()
    
    # Get an agent to fail repeatedly
    agents = list(resilience_manager.health_monitor.get_all_telemetry().keys())
    if agents:
        test_agent = agents[0]
        print(f"Triggering replacement for agent: {test_agent}")
        
        # Simulate many consecutive failures to trigger replacement
        for i in range(5):
            resilience_manager.update_agent_error(test_agent, f"Critical error {i+1}")
            await asyncio.sleep(0.5)
        
        # Wait for replacement to potentially occur
        await asyncio.sleep(3.0)
        
        # Check replacement history
        history = resilience_manager.replacement_history
        if history:
            print(f"Replacements triggered: {len(history)}")
            for replacement in history[-3:]:  # Show last 3
                print(f"  - {replacement['original_agent']} -> {replacement['replacement_agent']}")
        else:
            print("No replacements occurred (this may be normal depending on timing)")
    
    env.shutdown()


async def demo_manual_intervention():
    """Demonstrate manual agent replacement"""
    print("\n=== Manual Intervention Demo ===")
    
    resilience_config = ResilienceSettings(
        enable_auto_replacement=False  # Disable auto for manual demo
    )
    
    env = AutonomousMultiAgentEnvironment(resilience_config)
    resilience_manager = env.get_resilience_manager()
    
    # Show initial agents
    status = resilience_manager.get_resilience_status()
    print(f"Initial agents: {len(status['active_agents'])}")
    
    # Manually replace an agent
    agents = list(resilience_manager.health_monitor.get_all_telemetry().keys())
    if agents:
        agent_to_replace = agents[0]
        print(f"Manually replacing agent: {agent_to_replace}")
        
        success = resilience_manager.manually_replace_agent(
            agent_to_replace, 
            "Demo manual replacement"
        )
        
        if success:
            print("Manual replacement successful")
        else:
            print("Manual replacement failed")
        
        # Check updated status
        await asyncio.sleep(1.0)
        status = resilience_manager.get_resilience_status()
        print(f"Updated agents: {len(status['active_agents'])}")
    
    env.shutdown()


async def demo_configuration_changes():
    """Demonstrate dynamic configuration changes"""
    print("\n=== Configuration Changes Demo ===")
    
    # Start with default config
    resilience_config = ResilienceSettings()
    env = AutonomousMultiAgentEnvironment(resilience_config)
    resilience_manager = env.get_resilience_manager()
    
    print("Initial configuration:")
    print(f"  Max consecutive errors: {resilience_manager.config.max_consecutive_errors}")
    print(f"  Min health score: {resilience_manager.config.min_health_score}")
    print(f"  Health check interval: {resilience_manager.config.health_check_interval}s")
    
    # Change configuration
    print("\nUpdating configuration...")
    resilience_manager.config.max_consecutive_errors = 5
    resilience_manager.config.min_health_score = 0.2
    resilience_manager.config.health_check_interval = 5.0
    
    print("Updated configuration:")
    print(f"  Max consecutive errors: {resilience_manager.config.max_consecutive_errors}")
    print(f"  Min health score: {resilience_manager.config.min_health_score}")
    print(f"  Health check interval: {resilience_manager.config.health_check_interval}s")
    
    env.shutdown()


async def demo_comprehensive_monitoring():
    """Comprehensive demo showing all features"""
    print("\n=== Comprehensive Resilience Demo ===")
    
    # Create environment with full monitoring
    resilience_config = ResilienceSettings(
        health_check_interval=1.0,
        max_consecutive_errors=3,
        min_health_score=0.4,
        enable_auto_replacement=True,
        context_retention_tasks=5,
        context_retention_messages=20
    )
    
    env = AutonomousMultiAgentEnvironment(resilience_config)
    resilience_manager = env.get_resilience_manager()
    
    print("Starting comprehensive monitoring demo...")
    
    # Simulate mixed activity across multiple agents
    agents = list(resilience_manager.health_monitor.get_all_telemetry().keys())
    
    for round_num in range(3):
        print(f"\n--- Round {round_num + 1} ---")
        
        # Simulate activity for each agent
        for agent_id in agents[:3]:  # Limit to 3 agents for demo
            for i in range(random.randint(2, 5)):
                if random.random() < 0.4:  # 40% failure rate
                    resilience_manager.update_agent_error(agent_id, f"Round {round_num+1} error {i+1}")
                else:
                    resilience_manager.update_agent_success(agent_id, random.uniform(0.1, 2.0))
                await asyncio.sleep(0.2)
        
        # Show status
        status = resilience_manager.get_resilience_status()
        health_summary = status['health_summary']
        
        print(f"Health Summary:")
        print(f"  Total agents: {health_summary['total_agents']}")
        print(f"  Average health: {health_summary['average_health_score']:.2f}")
        print(f"  Healthy: {health_summary['healthy_agents']}")
        print(f"  Unhealthy: {health_summary['unhealthy_agents']}")
        print(f"  Recent replacements: {health_summary['recent_replacements']}")
        
        # Show agent details
        telemetry_data = resilience_manager.health_monitor.get_all_telemetry()
        for agent_id, telemetry in list(telemetry_data.items())[:3]:
            print(f"  Agent {agent_id}: {telemetry.get_status().value} "
                  f"(score: {telemetry.get_health_score():.2f}, "
                  f"errors: {telemetry.consecutive_errors})")
        
        await asyncio.sleep(1.0)
    
    # Show final summary
    print("\n=== Final Summary ===")
    final_status = resilience_manager.get_resilience_status()
    
    print(f"Total events generated: {len(final_status['recent_events'])}")
    print(f"Total replacements: {len(final_status['replacement_history'])}")
    
    if final_status['replacement_history']:
        print("Replacement history:")
        for replacement in final_status['replacement_history']:
            print(f"  - {replacement['original_agent']} -> {replacement['replacement_agent']} "
                  f"({replacement['type']})")
    
    env.shutdown()


async def main():
    """Run all demos"""
    print("Agent Resilience Layer Demonstration")
    print("==================================")
    
    try:
        await demo_basic_health_monitoring()
        await demo_failure_detection()
        await demo_automatic_replacement()
        await demo_manual_intervention()
        await demo_configuration_changes()
        await demo_comprehensive_monitoring()
        
        print("\n=== Demo Complete ===")
        print("The Agent Resilience Layer provides:")
        print("✓ Real-time health monitoring")
        print("✓ Automatic failure detection")
        print("✓ Configurable thresholds")
        print("✓ Automatic agent replacement")
        print("✓ Context preservation")
        print("✓ Manual intervention support")
        print("✓ Comprehensive event logging")
        print("✓ Dynamic configuration")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
