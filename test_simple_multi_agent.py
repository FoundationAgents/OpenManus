#!/usr/bin/env python3
"""
Simple test script for multi-agent system core functionality
Tests the basic components without all dependencies
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_configuration():
    """Test configuration loading"""
    try:
        from app.config import config
        print('✅ Configuration loaded successfully')
        print(f'LLM Model: {config.llm["default"].model}')
        print(f'API URL: {config.llm["default"].base_url}')
        print(f'Multi-agent enabled: {config.run_flow_config.enable_multi_agent}')
        print(f'Agent pools: {config.agent_pools.developer} developers')
        return True
    except Exception as e:
        print(f'❌ Configuration test failed: {e}')
        return False

def test_multi_agent_classes():
    """Test multi-agent core classes"""
    try:
        from app.flow.multi_agent_environment import (
            AgentRole, 
            TaskPriority, 
            DevelopmentTask,
            Blackboard,
            BlackboardMessage,
            MessageType
        )
        print('✅ Multi-agent core classes imported successfully')
        
        # Test enums
        assert AgentRole.DEVELOPER == "developer"
        assert TaskPriority.HIGH.value == 3
        assert MessageType.TASK == "task"
        print('✅ Enums working correctly')
        
        # Test task creation
        task = DevelopmentTask(
            id='test_task',
            title='Test Task',
            description='Test task creation',
            role=AgentRole.DEVELOPER,
            priority=TaskPriority.MEDIUM
        )
        assert task.title == 'Test Task'
        assert task.role == AgentRole.DEVELOPER
        
        # Test task serialization
        task_dict = task.to_dict()
        assert 'id' in task_dict
        assert 'title' in task_dict
        assert 'role' in task_dict
        print('✅ Task creation and serialization working')
        
        # Test blackboard
        blackboard = Blackboard()
        message = BlackboardMessage(
            id="test_msg",
            type=MessageType.INFO,
            sender="test_agent",
            content="Test message",
            priority=TaskPriority.MEDIUM
        )
        blackboard.post_message(message)
        assert len(blackboard.message_history) == 1
        print('✅ Blackboard functionality working')
        
        return True
    except Exception as e:
        print(f'❌ Multi-agent classes test failed: {e}')
        return False

def test_enhanced_flow():
    """Test enhanced async flow"""
    try:
        from app.flow.enhanced_async_flow import EnhancedAsyncFlow, FlowState, UserInteractionType
        print('✅ Enhanced async flow classes imported successfully')
        
        # Test flow state enum
        assert FlowState.INITIALIZING == "initializing"
        assert UserInteractionType.GUIDANCE == "guidance"
        print('✅ Flow enums working correctly')
        
        # Test flow creation with mock agents
        from unittest.mock import Mock
        agents = {'test': Mock()}
        flow = EnhancedAsyncFlow(agents=agents)
        assert flow.flow_state == FlowState.INITIALIZING
        print('✅ Enhanced flow creation working')
        
        # Test user guidance
        flow.provide_user_guidance("Test guidance", UserInteractionType.GUIDANCE)
        assert len(flow.user_interactions) == 1
        print('✅ User guidance functionality working')
        
        # Test execution status
        status = flow.get_execution_status()
        assert 'flow_state' in status
        assert 'agent_thoughts' in status
        print('✅ Execution status reporting working')
        
        return True
    except Exception as e:
        print(f'❌ Enhanced flow test failed: {e}')
        return False

def test_specialized_agents():
    """Test specialized agent classes"""
    try:
        from app.flow.specialized_agents import (
            ArchitectAgent,
            DeveloperAgent,
            TesterAgent,
            DevOpsAgent,
            SecurityAgent
        )
        print('✅ Specialized agent classes imported successfully')
        
        # Test agent roles
        assert ArchitectAgent.__name__ == "ArchitectAgent"
        assert DeveloperAgent.__name__ == "DeveloperAgent"
        assert TesterAgent.__name__ == "TesterAgent"
        print('✅ Specialized agent classes working')
        
        return True
    except Exception as e:
        print(f'❌ Specialized agents test failed: {e}')
        return False

def test_integration():
    """Test basic integration"""
    try:
        # Test that all major components can be imported together
        from app.config import config
        from app.flow.multi_agent_environment import AutonomousMultiAgentEnvironment
        from app.flow.enhanced_async_flow import EnhancedAsyncFlow
        
        print('✅ All major components imported successfully')
        
        # Test configuration values
        assert config.run_flow_config.enable_multi_agent == True
        assert config.agent_pools.developer > 0
        print('✅ Configuration values correct')
        
        return True
    except Exception as e:
        print(f'❌ Integration test failed: {e}')
        return False

def main():
    """Run all tests"""
    print("🧪 Running Simple Multi-Agent System Tests")
    print("=" * 60)
    
    tests = [
        ("Configuration Loading", test_configuration),
        ("Multi-Agent Core Classes", test_multi_agent_classes),
        ("Enhanced Async Flow", test_enhanced_flow),
        ("Specialized Agents", test_specialized_agents),
        ("Integration Test", test_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   Tests Run: {total}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {total - passed}")
    print(f"   Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! The multi-agent environment core is working.")
        print("📝 Note: Some advanced features may require additional dependencies.")
    else:
        print("\n❌ Some tests failed. Please review the output above.")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)