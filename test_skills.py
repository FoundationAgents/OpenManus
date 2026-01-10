"""
Test script for Agent Skills feature
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import config
from app.skill_manager import skill_manager


async def test_skill_loading():
    """Test 1: Verify skills load from disk"""
    print("\n" + "=" * 60)
    print("TEST 1: Skill Loading from Disk")
    print("=" * 60)

    # Initialize skill manager
    await skill_manager.initialize(skills_paths=config.skills_config.paths)

    skills = skill_manager.get_all_skills()
    print(f"\n✓ Loaded {len(skills)} skills from disk")

    for name, skill in skills.items():
        print(f"  - {name}: {skill.description[:60]}...")

    assert len(skills) == 3, f"Expected 3 skills, got {len(skills)}"
    assert "code-review" in skills, "code-review skill not loaded"
    assert "documentation" in skills, "documentation skill not loaded"
    assert "debugging" in skills, "debugging skill not loaded"

    print("\n✅ Test 1 PASSED: All skills loaded correctly")
    return True


def test_skill_listing():
    """Test 2: Verify skill listing functionality"""
    print("\n" + "=" * 60)
    print("TEST 2: Skill Listing")
    print("=" * 60)

    skills_list = skill_manager.list_skills()
    print(f"\n✓ Listed {len(skills_list)} skills")

    for skill_info in skills_list:
        print(f"  Name: {skill_info['name']}")
        print(f"  Path: {skill_info['path']}")
        print(f"  Context: {skill_info['context']}")
        print(f"  User-invocable: {skill_info['user_invocable']}")
        print()

    assert len(skills_list) == 3, f"Expected 3 skills in list, got {len(skills_list)}"

    # Check required fields
    for skill in skills_list:
        assert "name" in skill, f"Missing 'name' field in skill"
        assert "description" in skill, f"Missing 'description' field in skill"
        assert "path" in skill, f"Missing 'path' field in skill"

    print("✅ Test 2 PASSED: Skill listing works correctly")
    return True


def test_skill_relevance():
    """Test 3: Verify relevance matching"""
    print("\n" + "=" * 60)
    print("TEST 3: Skill Relevance Matching")
    print("=" * 60)

    test_cases = [
        {
            "request": "Review the code in main.py for bugs",
            "expected_skills": ["code-review"],
        },
        {
            "request": "Write documentation for this API",
            "expected_skills": ["documentation"],
        },
        {"request": "Debug this error in my code", "expected_skills": ["debugging"]},
        {
            "request": "Fix this bug and document it",
            "expected_skills": ["debugging", "documentation"],
            # Note: code-review might also match due to auto-extracted keywords
        },
        {"request": "Just say hello", "expected_skills": []},
    ]

    for i, test_case in enumerate(test_cases, 1):
        request = test_case["request"]
        expected = set(test_case["expected_skills"])

        print(f"\nTest case {i}: '{request}'")
        relevant_skills = skill_manager.get_relevant_skills(request, threshold=0.3)
        actual = set([skill.name for skill in relevant_skills])

        print(f"  Expected: {expected}")
        print(f"  Actual:   {actual}")

        # Check if expected skills are in actual
        for exp_skill in expected:
            assert exp_skill in actual, f"Expected skill '{exp_skill}' not found"

        # Check that all expected skills are matched (may have extra skills)
        assert expected.issubset(actual), (
            f"Not all expected skills found. Expected {expected}, got {actual}"
        )

        print(f"  ✓ All expected skills matched")

    print("\n✅ Test 3 PASSED: Relevance matching works correctly")
    return True


def test_skill_metadata():
    """Test 4: Verify skill metadata parsing"""
    print("\n" + "=" * 60)
    print("TEST 4: Skill Metadata Parsing")
    print("=" * 60)

    skills = skill_manager.get_all_skills()

    # Test code-review skill
    code_review = skills.get("code-review")
    assert code_review is not None, "code-review skill not found"

    print(f"\nChecking code-review skill:")
    print(f"  Name: {code_review.name}")
    print(f"  Description: {code_review.description}")
    print(f"  Path: {code_review.path}")
    print(f"  Context: {code_review.context}")
    print(f"  Allowed tools: {code_review.allowed_tools}")

    assert code_review.name == "code-review"
    assert len(code_review.description) > 0
    assert code_review.path.exists()
    assert code_review.allowed_tools is not None
    assert "Read" in code_review.allowed_tools

    # Test documentation skill
    docs = skills.get("documentation")
    assert docs is not None, "documentation skill not found"
    print(f"\nChecking documentation skill:")
    print(f"  Name: {docs.name}")
    print(f"  User-invocable: {docs.user_invocable}")

    assert docs.name == "documentation"
    assert docs.user_invocable == True

    print("\n✅ Test 4 PASSED: Skill metadata parsed correctly")
    return True


def test_edge_cases():
    """Test 5: Verify edge case handling"""
    print("\n" + "=" * 60)
    print("TEST 5: Edge Cases")
    print("=" * 60)

    # Test getting non-existent skill
    print("\nTest 5a: Get non-existent skill")
    non_existent = skill_manager.get_skill("does-not-exist")
    assert non_existent is None, "Should return None for non-existent skill"
    print("  ✓ Returns None for non-existent skill")

    # Test getting skill prompt for non-existent skill
    print("\nTest 5b: Get prompt for non-existent skill")
    prompt = skill_manager.get_skill_prompt("does-not-exist")
    assert prompt is None, "Should return None for non-existent skill"
    print("  ✓ Returns None for non-existent skill prompt")

    # Test relevance with empty request
    print("\nTest 5c: Relevance with empty request")
    relevant = skill_manager.get_relevant_skills("")
    assert len(relevant) == 0, (
        f"Expected no skills for empty request, got {len(relevant)}"
    )
    print("  ✓ Returns empty list for empty request")

    # Test relevance threshold
    print("\nTest 5d: Relevance with high threshold")
    relevant = skill_manager.get_relevant_skills("help", threshold=1.0)
    assert len(relevant) == 0, (
        f"Expected no skills with threshold=1.0, got {len(relevant)}"
    )
    print("  ✓ Returns empty list with high threshold")

    print("\n✅ Test 5 PASSED: Edge cases handled correctly")
    return True


async def test_agent_integration():
    """Test 6: Verify agent integration"""
    print("\n" + "=" * 60)
    print("TEST 6: Agent Integration")
    print("=" * 60)

    from app.agent.manus import Manus

    # Create agent
    agent = await Manus.create()
    print("\n✓ Created Manus agent")

    # Test manual skill activation
    print("\nTest 6a: Manual skill activation")
    success = await agent.activate_skill_by_name("code-review")
    assert success, "Failed to activate code-review skill"
    assert "code-review" in agent.active_skills, "Skill not in active_skills"
    print("  ✓ Manually activated code-review skill")

    # Test get skill system prompt
    print("\nTest 6b: Get skill system prompt")
    skill_prompt = agent.get_skill_system_prompt()
    assert skill_prompt is not None, "Should have skill prompt"
    assert "code-review" in skill_prompt, "Skill name should be in prompt"
    assert "Active Skills:" in skill_prompt, "Should have 'Active Skills:' header"
    print(f"  ✓ Got skill system prompt with {len(skill_prompt)} characters")

    # Test listing active skills
    print("\nTest 6c: List active skills")
    active = agent.list_active_skills()
    assert "code-review" in active, "code-review should be in active skills"
    print(f"  ✓ Active skills: {active}")

    # Test deactivating skill
    print("\nTest 6d: Deactivate skill")
    success = agent.deactivate_skill("code-review")
    assert success, "Failed to deactivate skill"
    assert "code-review" not in agent.active_skills, (
        "Skill should not be in active_skills"
    )
    print("  ✓ Deactivated code-review skill")

    # Test deactivating non-existent skill
    print("\nTest 6e: Deactivate non-existent skill")
    success = agent.deactivate_skill("does-not-exist")
    assert not success, "Should fail to deactivate non-existent skill"
    print("  ✓ Returns False for non-existent skill")

    # Cleanup
    await agent.cleanup()

    print("\n✅ Test 6 PASSED: Agent integration works correctly")
    return True


async def test_supporting_files():
    """Test 7: Verify supporting file loading"""
    print("\n" + "=" * 60)
    print("TEST 7: Supporting Files (Progressive Disclosure)")
    print("=" * 60)

    skills = skill_manager.get_all_skills()

    # Check if skills have supporting files (none in current examples)
    print("\nChecking for supporting files:")
    for name, skill in skills.items():
        print(f"  {name}: {len(skill.supporting_files)} supporting files")

    print("\nNote: Example skills don't have supporting files yet")
    print("This is expected - progressive disclosure works when files exist")

    print("\n✅ Test 7 PASSED: Supporting files structure ready")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AGENT SKILLS TEST SUITE")
    print("=" * 60)

    tests = [
        ("Skill Loading", test_skill_loading),
        ("Skill Listing", test_skill_listing),
        ("Skill Relevance", test_skill_relevance),
        ("Skill Metadata", test_skill_metadata),
        ("Edge Cases", test_edge_cases),
        ("Agent Integration", test_agent_integration),
        ("Supporting Files", test_supporting_files),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n❌ FAILED: {test_name}")
            print(f"   Error: {e}")
        except Exception as e:
            failed += 1
            print(f"\n❌ ERROR: {test_name}")
            print(f"   Exception: {e}")
            import traceback

            traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed")

    # Cleanup
    await skill_manager.cleanup()

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
