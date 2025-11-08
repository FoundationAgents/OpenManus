#!/usr/bin/env python3
"""
Hybrid QA System - Usage Examples

Demonstrates how to use the new Hybrid QA System with AI specialists
and post-check validation.
"""

import asyncio
from typing import List, Tuple
from app.qa import HybridQASystem
from app.workflows.qa_integration import HybridQAGate, HybridQAWorkflowIntegration


async def example_1_basic_code_review():
    """Example 1: Basic code review with hybrid QA"""
    print("\n" + "="*70)
    print("Example 1: Basic Code Review with Hybrid QA")
    print("="*70)
    
    # Initialize hybrid QA system
    hybrid_qa = HybridQASystem(qa_level="standard", auto_fix=True)
    
    # Code files to review
    code_files = [
        ("calculator.py", """
def add(a, b):
    return a + b

def divide(a, b):
    # TODO: add error handling
    return a / b

def process_data(data):
    result = []
    for item in data:
        if item:
            if item > 0:
                if item < 100:
                    result.append(item * 2)
    return result
"""),
        ("utils.py", """
import os
import json

password = "super_secret_123"

def load_config():
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    return query

def cleanup():
    pass
""")
    ]
    
    # Run complete QA workflow
    print("\nRunning complete hybrid QA workflow...")
    result = await hybrid_qa.run_complete_qa_workflow(code_files)
    
    # Display results
    print(f"\n✓ Workflow Status: {result['workflow_status']}")
    print(f"✓ QA Level: {result['qa_level']}")
    print(f"\nApproval Decision:")
    print(f"  Status: {result['approval']['status']}")
    print(f"  Recommendation: {result['approval']['recommendation']}")
    print(f"  AI Consensus: {result['approval']['ai_consensus']:.2%}")
    print(f"  Total Issues: {result['approval']['total_issues']}")
    print(f"  Issues Fixed: {result['approval']['issues_fixed']}")
    print(f"  Post-check Passed: {result['approval']['post_check_passed']}")


async def example_2_ai_specialist_analysis():
    """Example 2: Detailed AI specialist analysis"""
    print("\n" + "="*70)
    print("Example 2: AI Specialist Team Analysis")
    print("="*70)
    
    from app.qa import AIQAAgent
    
    # Initialize AI agent
    ai_agent = AIQAAgent(agent_id="qa_specialist_1")
    
    # Code to analyze
    code_files = [
        ("service.py", """
import database
import logging

class UserService:
    def __init__(self):
        self.db = database.connect()
    
    async def get_user(self, user_id):
        '''Fetch user from database'''
        try:
            query = f"SELECT * FROM users WHERE id = {user_id}"
            return self.db.execute(query)
        except Exception as e:
            logging.error(f"Error: {e}")
            return None
    
    async def create_user(self, name, email):
        # TODO: validate email
        # HACK: bypass password requirement for now
        query = f"INSERT INTO users VALUES ('{name}', '{email}')"
        self.db.execute(query)
        return True
""")
    ]
    
    print("\nRunning AI specialist analysis...")
    result = await ai_agent.analyze_code_changes(code_files)
    
    print(f"\n✓ Files Analyzed: {result['files_analyzed']}")
    print(f"✓ Specialists Involved: {len(result['specialists_involved'])}")
    print(f"✓ Total Decisions: {result['total_decisions']}")
    
    print(f"\nSpecialist Analysis Summary:")
    summary = result["summary"]
    print(f"  Average Confidence: {summary['avg_confidence']:.2%}")
    print(f"  Critical Priority: {summary['critical_priority_count']}")
    print(f"  High Priority: {summary['high_priority_count']}")
    print(f"  Recommendations: {summary['recommendations_count']}")
    
    print(f"\nSpecialist Findings:")
    for i, decision in enumerate(result["all_decisions"], 1):
        print(f"\n  Specialist #{i}: {decision.specialist_type.value}")
        print(f"    Decision Type: {decision.decision_type}")
        print(f"    Priority: {decision.priority}")
        print(f"    Confidence: {decision.confidence:.2%}")
        if decision.recommendations:
            print(f"    Recommendations:")
            for rec in decision.recommendations[:2]:  # First 2
                print(f"      - {rec}")


async def example_3_post_check_validation():
    """Example 3: Post-check validation system"""
    print("\n" + "="*70)
    print("Example 3: Post-Check Validation")
    print("="*70)
    
    from app.qa import PostCheckValidator
    
    validator = PostCheckValidator()
    
    original_code = """
def calculate(x, y):
    return x + y

def process(data):
    result = []
    for item in data:
        result.append(item * 2)
    return result
"""
    
    fixed_code = """
def calculate(x: int, y: int) -> int:
    '''Add two numbers.'''
    return x + y

def process(data: list) -> list:
    '''Process data items.'''
    return [item * 2 for item in data]
"""
    
    print("\nRunning post-check validation...")
    result = await validator.run_all_checks(
        original_code=original_code,
        fixed_code=fixed_code,
        file_path="example.py",
        applied_fixes=[
            {"type": "add_docstring", "target": "calculate"},
            {"type": "add_type_hints", "target": "calculate"},
            {"type": "refactor_to_comprehension", "target": "process"}
        ]
    )
    
    print(f"\n✓ Validation Status: {'PASSED' if result['all_passed'] else 'FAILED'}")
    print(f"✓ Checks Passed: {result['checks_passed']}/{result['total_checks']}")
    print(f"✓ Total Issues: {result['total_issues']}")
    print(f"✓ Total Warnings: {result['total_warnings']}")
    
    print(f"\nValidation Summary:")
    summary = result["summary"]
    for key, value in summary.items():
        status = "✓" if value else "✗"
        print(f"  {status} {key}: {value}")


async def example_4_planning_validation():
    """Example 4: Task planning validation"""
    print("\n" + "="*70)
    print("Example 4: Planning Validation with Planner Expert")
    print("="*70)
    
    from app.qa import AIQAAgent
    
    ai_agent = AIQAAgent(agent_id="planner_1")
    
    plan = {
        "project": "Feature Development",
        "tasks": [
            {
                "id": "task-1",
                "description": "Implement API endpoint",
                "estimated_hours": 8,
                "dependencies": [],
                "complexity": "medium",
                "acceptance_criteria": [
                    "Endpoint responds with correct format",
                    "Error handling implemented",
                    "Unit tests written"
                ]
            },
            {
                "id": "task-2",
                "description": "Add database migration",
                "estimated_hours": 4,
                "dependencies": ["task-1"],
                "complexity": "low"
            },
            {
                "id": "task-3",
                "description": "Integration tests",
                "estimated_hours": 6,
                "dependencies": ["task-1", "task-2"],
                "complexity": "medium"
            }
        ]
    }
    
    print("\nValidating task planning...")
    result = await ai_agent.validate_planning(plan)
    
    print(f"\n✓ Validation Status: {'PASSED' if result['validation_passed'] else 'FAILED'}")
    
    print(f"\nPlanning Analysis:")
    print(f"  Tasks: {result['decision'].findings['total_tasks']}")
    print(f"  Circular Dependencies: {result['decision'].findings['circular_deps']}")
    
    effort = result['decision'].findings['effort_distribution']
    print(f"\nEffort Distribution:")
    print(f"  Total: {effort['total_effort']}h")
    print(f"  Average: {effort['avg_effort']:.1f}h")
    print(f"  Range: {effort['min_effort']}-{effort['max_effort']}h")
    
    if result['decision'].recommendations:
        print(f"\nRecommendations:")
        for rec in result['decision'].recommendations:
            print(f"  - {rec}")


async def example_5_workflow_integration():
    """Example 5: Integration with development workflow"""
    print("\n" + "="*70)
    print("Example 5: Workflow Integration - Dev Task Processing")
    print("="*70)
    
    gate = HybridQAGate(qa_level="standard", auto_fix=True, enable_postcheck=True)
    
    # Simulate dev task completion
    task_result = await gate.process_dev_task_with_hybrid_qa(
        task_id="TASK-2024-001",
        code_files=["app/feature.py"],  # In real scenario, these would exist
        author_agent="dev_agent_1",
        original_files=["app/feature.py.orig"]  # For comparison
    )
    
    print(f"\n✓ Task ID: {task_result.get('task_id')}")
    print(f"✓ Stage: {task_result.get('stage')}")
    print(f"✓ Status: {task_result.get('status')}")
    
    if task_result.get('status') == 'approved':
        print(f"\n✓ Code Approved for Merge!")
        review = task_result.get('hybrid_qa_review', {})
        print(f"  AI Consensus: {review.get('ai_consensus', 0):.2%}")
        print(f"  Issues Fixed: {review.get('issues_fixed', 0)}")
    else:
        print(f"\n✗ Code Needs Work")
        print(f"  Reason: {task_result.get('reason', 'Unknown')}")


async def example_6_specialist_team_decisions():
    """Example 6: Deep dive into specialist team decisions"""
    print("\n" + "="*70)
    print("Example 6: Specialist Team Decision Details")
    print("="*70)
    
    from app.qa import CodeExpert, PlannerExpert, FixerExpert, CleanupAgent
    
    print("\n1. Code Expert Analysis:")
    print("-" * 40)
    
    code_expert = CodeExpert()
    code_result = await code_expert.analyze_code(
        """
def unsafe_query(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
""",
        "db_operations.py"
    )
    
    print(f"  Confidence: {code_result.confidence:.2%}")
    print(f"  Findings: {code_result.findings['security_issues']}")
    print(f"  Recommendations: {code_result.recommendations[0] if code_result.recommendations else 'None'}")
    
    print("\n2. Cleanup Agent Analysis:")
    print("-" * 40)
    
    cleanup_agent = CleanupAgent()
    cleanup_result = await cleanup_agent.analyze_for_cleanup(
        """
import os
import sys
import json
unused_var = 42

def process():
    if False:
        print("Dead code")
    pass
""",
        "cleanup_example.py"
    )
    
    print(f"  Unused Imports: {cleanup_result.findings.get('unused_imports', [])}")
    print(f"  Dead Code Found: {len(cleanup_result.findings.get('dead_code', []))} blocks")
    print(f"  Formatting Issues: {len(cleanup_result.findings.get('formatting_issues', []))}")


async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("HYBRID QA SYSTEM - USAGE EXAMPLES")
    print("="*70)
    
    try:
        # Run examples
        await example_1_basic_code_review()
        await example_2_ai_specialist_analysis()
        await example_3_post_check_validation()
        await example_4_planning_validation()
        await example_5_workflow_integration()
        await example_6_specialist_team_decisions()
        
        print("\n" + "="*70)
        print("✓ All examples completed successfully!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
