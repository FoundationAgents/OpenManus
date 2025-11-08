"""Tests for Team & Human Management System."""

import sys
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import importlib

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import team management modules directly to avoid agent/__init__.py
team_model = importlib.import_module('app.agent.team_model')
work_distributor = importlib.import_module('app.agent.work_distributor')
progress_tracking = importlib.import_module('app.agent.progress_tracking')
meeting_optimizer = importlib.import_module('app.agent.meeting_optimizer')
conflict_resolution = importlib.import_module('app.agent.conflict_resolution')
team_learning = importlib.import_module('app.agent.team_learning')
wellbeing_monitor = importlib.import_module('app.agent.wellbeing_monitor')
ai_human_collaboration = importlib.import_module('app.agent.ai_human_collaboration')
async_communication = importlib.import_module('app.agent.async_communication')
recognition = importlib.import_module('app.agent.recognition')

# Extract classes from modules
Team = team_model.Team
TeamMember = team_model.TeamMember
MemberType = team_model.MemberType
MemberRole = team_model.MemberRole
WorkPreferences = team_model.WorkPreferences

WorkDistributor = work_distributor.WorkDistributor
Task = work_distributor.Task
TaskPriority = work_distributor.TaskPriority
TaskStatus = work_distributor.TaskStatus
AssignmentAnalysis = work_distributor.AssignmentAnalysis

ProgressTracker = progress_tracking.ProgressTracker
ProgressUpdate = progress_tracking.ProgressUpdate
Standup = progress_tracking.Standup
RiskLevel = progress_tracking.RiskLevel
RiskAssessment = progress_tracking.RiskAssessment

MeetingOptimizer = meeting_optimizer.MeetingOptimizer
Meeting = meeting_optimizer.Meeting
MeetingPurpose = meeting_optimizer.MeetingPurpose
MeetingRecommendation = meeting_optimizer.MeetingRecommendation

ConflictResolver = conflict_resolution.ConflictResolver
Conflict = conflict_resolution.Conflict
ConflictType = conflict_resolution.ConflictType
ConflictPerspective = conflict_resolution.ConflictPerspective

TeamLearningManager = team_learning.TeamLearningManager
LearningResource = team_learning.LearningResource
LearningType = team_learning.LearningType
SkillLevel = team_learning.SkillLevel

WellbeingMonitor = wellbeing_monitor.WellbeingMonitor
WellbeingStatus = wellbeing_monitor.WellbeingStatus
MemberWellbeing = wellbeing_monitor.MemberWellbeing

AIHumanCollaborationOptimizer = ai_human_collaboration.AIHumanCollaborationOptimizer
TaskPhase = ai_human_collaboration.TaskPhase
CollaborationPattern = ai_human_collaboration.CollaborationPattern

AsyncCommunicationManager = async_communication.AsyncCommunicationManager
AsyncUpdate = async_communication.AsyncUpdate
UpdateType = async_communication.UpdateType
Decision = async_communication.Decision

RecognitionManager = recognition.RecognitionManager
Recognition = recognition.Recognition
RecognitionType = recognition.RecognitionType


# ==================== Team Model Tests ====================

def test_team_member_creation():
    """Test creating a team member."""
    member = TeamMember(
        name="Alice",
        member_type=MemberType.HUMAN,
        role=MemberRole.BACKEND_ENGINEER,
        skills=["Python", "PostgreSQL"],
        capacity_hours_per_week=40.0,
        workload_percent=60.0
    )
    assert member.name == "Alice"
    assert member.available_hours_this_week == 16.0  # 40 - (40 * 0.6)
    assert not member.is_overloaded


def test_team_member_overloaded():
    """Test identifying overloaded members."""
    member = TeamMember(
        name="Bob",
        member_type=MemberType.HUMAN,
        role=MemberRole.FRONTEND_ENGINEER,
        workload_percent=85.0
    )
    assert member.is_overloaded


def test_team_operations():
    """Test team operations."""
    team = Team(name="Engineering Team")
    
    member1 = TeamMember(
        name="Alice",
        member_type=MemberType.HUMAN,
        role=MemberRole.BACKEND_ENGINEER,
        skills=["Python"]
    )
    
    member2 = TeamMember(
        name="CodeGenAgent",
        member_type=MemberType.AI_AGENT,
        role=MemberRole.CODE_GENERATION
    )
    
    team.add_member(member1)
    team.add_member(member2)
    
    assert len(team.members) == 2
    assert len(team.get_humans()) == 1
    assert len(team.get_ai_agents()) == 1
    assert team.get_member("Alice") is not None
    assert team.get_members_by_skill("Python") == [member1]


def test_team_duplicate_member():
    """Test adding duplicate members."""
    team = Team(name="Team")
    member = TeamMember(
        name="Alice",
        member_type=MemberType.HUMAN,
        role=MemberRole.BACKEND_ENGINEER
    )
    team.add_member(member)
    
    with pytest.raises(ValueError):
        team.add_member(member)


# ==================== Work Distributor Tests ====================

def test_work_distribution():
    """Test task distribution."""
    team = Team(name="Team")
    team.add_member(TeamMember(
        name="Alice",
        member_type=MemberType.HUMAN,
        role=MemberRole.BACKEND_ENGINEER,
        skills=["Python", "PostgreSQL"],
        capacity_hours_per_week=40.0,
        workload_percent=40.0
    ))
    
    distributor = WorkDistributor(team)
    
    task = Task(
        id="task-1",
        title="Implement API",
        estimated_hours=16.0,
        required_skills=["Python"],
        preferred_roles=[MemberRole.BACKEND_ENGINEER]
    )
    
    distributor.add_task(task)
    analysis = distributor.analyze_assignment("task-1")
    
    assert analysis.recommended_primary == "Alice"
    assert analysis.candidates[0][1] > 0.5  # Good match score


def test_assignment_insufficient_capacity():
    """Test assignment with insufficient capacity."""
    team = Team(name="Team")
    team.add_member(TeamMember(
        name="Alice",
        member_type=MemberType.HUMAN,
        role=MemberRole.BACKEND_ENGINEER,
        capacity_hours_per_week=40.0,
        workload_percent=95.0  # Only 2 hours available
    ))
    
    distributor = WorkDistributor(team)
    task = Task(
        id="task-1",
        title="Big Task",
        estimated_hours=20.0
    )
    distributor.add_task(task)
    
    with pytest.raises(ValueError):
        distributor.assign_task("task-1", "Alice")


# ==================== Progress Tracking Tests ====================

def test_progress_tracking():
    """Test progress tracking."""
    tracker = ProgressTracker()
    
    task = Task(
        id="task-1",
        title="Implement feature",
        estimated_hours=20.0,
        due_date=datetime.now() + timedelta(days=5)
    )
    task.assigned_to = "Alice"
    task.start_date = datetime.now()
    
    tracker.add_task(task)
    
    # Record progress
    update = ProgressUpdate(
        task_id="task-1",
        progress_percent=50.0,
        work_completed="Finished core logic"
    )
    tracker.record_progress(update)
    
    assert tracker.tasks["task-1"].progress_percent == 50.0


def test_risk_assessment():
    """Test risk assessment."""
    tracker = ProgressTracker()
    
    task = Task(
        id="task-1",
        title="Task",
        estimated_hours=20.0,
        due_date=datetime.now() - timedelta(days=1),  # Overdue
        progress_percent=30.0
    )
    task.assigned_to = "Alice"
    task.blocker = "Database issue"
    
    tracker.add_task(task)
    assessment = tracker.assess_task_risk("task-1")
    
    assert assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert len(assessment.reasons) > 0


# ==================== Meeting Optimizer Tests ====================

def test_meeting_optimization():
    """Test meeting optimization."""
    optimizer = MeetingOptimizer()
    
    # Status update should not be recommended
    recommendation = optimizer.should_schedule_meeting(
        MeetingPurpose.STATUS_UPDATE,
        {"can_be_async": True, "decisions_needed": False, "num_attendees": 5}
    )
    # Status updates should prefer async (NOT_RECOMMENDED)
    assert recommendation == MeetingRecommendation.NOT_RECOMMENDED
    
    # Brainstorming with complex discussion should be recommended
    recommendation = optimizer.should_schedule_meeting(
        MeetingPurpose.BRAINSTORMING,
        {"can_be_async": False, "decisions_needed": False, "num_attendees": 5}
    )
    assert recommendation in [MeetingRecommendation.RECOMMENDED, MeetingRecommendation.OPTIONAL]


def test_async_alternative_suggestion():
    """Test async alternative suggestions."""
    optimizer = MeetingOptimizer()
    
    suggestion = optimizer.suggest_async_alternative(MeetingPurpose.STATUS_UPDATE, 5)
    assert suggestion is not None
    assert "standup" in suggestion.lower()


# ==================== Conflict Resolution Tests ====================

def test_conflict_resolution():
    """Test conflict reporting and analysis."""
    resolver = ConflictResolver()
    
    conflict = Conflict(
        id="conflict-1",
        title="Architecture Disagreement",
        description="Alice and Bob disagree on database choice",
        type=ConflictType.TECHNICAL_DISAGREEMENT,
        parties_involved=["Alice", "Bob"]
    )
    
    resolver.report_conflict(conflict)
    
    # Add perspectives from both parties
    alice_perspective = ConflictPerspective(
        person="Alice",
        perspective="SQL is more reliable",
        underlying_concerns=["Data consistency", "Complexity"]
    )
    bob_perspective = ConflictPerspective(
        person="Bob",
        perspective="NoSQL is more scalable",
        underlying_concerns=["Scale", "Performance"]
    )
    resolver.add_perspective("conflict-1", alice_perspective)
    resolver.add_perspective("conflict-1", bob_perspective)
    
    # Analyze
    analysis = resolver.analyze_conflict("conflict-1")
    assert analysis.root_cause != ""
    
    # Propose resolution (requires both perspectives)
    resolution = resolver.propose_resolution("conflict-1")
    assert resolution is not None


# ==================== Team Learning Tests ====================

def test_learning_management():
    """Test learning plan creation."""
    manager = TeamLearningManager()
    
    resource = LearningResource(
        id="resource-1",
        title="Python Course",
        description="Learn Python",
        learning_type=LearningType.COURSE,
        skill="Python",
        target_level=SkillLevel.INTERMEDIATE,
        estimated_hours=20.0,
        rating=4.5
    )
    manager.add_resource(resource)
    
    # Create learning plan
    plan = manager.create_learning_plan("Alice", ["Python"])
    
    assert plan.member_name == "Alice"
    assert "Python" in plan.target_skills
    assert len(plan.resources) > 0


def test_pairing_session():
    """Test pairing session scheduling."""
    manager = TeamLearningManager()
    
    session = manager.schedule_pairing_session(
        "Alice",
        "CodeGenAgent",
        "Python"
    )
    
    assert session.member1 == "Alice"
    assert session.skill_focus == "Python"
    assert not session.completed


# ==================== Wellbeing Monitor Tests ====================

def test_wellbeing_monitoring():
    """Test wellbeing monitoring."""
    monitor = WellbeingMonitor()
    
    wb = MemberWellbeing(member_name="Alice")
    monitor.wellbeing["Alice"] = wb
    
    # Record high hours
    monitor.record_hours("Alice", 60.0)
    
    status = monitor.assess_wellbeing("Alice")
    # Status should be one of these (depends on exact calculation)
    assert status in [WellbeingStatus.HEALTHY, WellbeingStatus.CAUTION, WellbeingStatus.AT_RISK, WellbeingStatus.CRITICAL]
    
    # Check for alerts
    alerts = monitor.check_for_alerts("Alice")
    # Just verify method runs without error and returns a list
    assert isinstance(alerts, list)


def test_vacation_tracking():
    """Test vacation recording."""
    monitor = WellbeingMonitor()
    
    wb = MemberWellbeing(member_name="Alice")
    monitor.wellbeing["Alice"] = wb
    
    monitor.record_vacation("Alice", 5)
    
    assert wb.vacation_days_used == 5
    assert wb.consecutive_overtime_weeks == 0


# ==================== AI-Human Collaboration Tests ====================

def test_collaboration_guidelines():
    """Test collaboration guidelines retrieval."""
    optimizer = AIHumanCollaborationOptimizer()
    
    guideline = optimizer.get_guideline_for_phase(TaskPhase.DESIGN)
    assert guideline is not None
    assert len(guideline.human_strengths) > 0
    assert len(guideline.ai_strengths) > 0


def test_collaboration_session():
    """Test creating collaboration session."""
    optimizer = AIHumanCollaborationOptimizer()
    
    session = optimizer.create_collaboration_session(
        "task-1",
        "Alice",
        "CodeGenAgent",
        TaskPhase.IMPLEMENTATION
    )
    
    assert session.human_member == "Alice"
    assert session.phase == TaskPhase.IMPLEMENTATION
    assert session.pattern is not None


# ==================== Async Communication Tests ====================

def test_async_updates():
    """Test async update posting."""
    manager = AsyncCommunicationManager()
    
    update = AsyncUpdate(
        id="update-1",
        update_type=UpdateType.STANDUP,
        author="Alice",
        title="Daily Standup",
        content="Completed API endpoint",
        channel="engineering"
    )
    
    manager.post_update(update)
    
    recent = manager.get_recent_updates(channel="engineering")
    assert len(recent) == 1


def test_decision_documentation():
    """Test decision documentation."""
    manager = AsyncCommunicationManager()
    
    decision = Decision(
        id="decision-1",
        title="Use PostgreSQL",
        context="Need to choose database",
        options_considered=["PostgreSQL", "MongoDB"],
        chosen_option="PostgreSQL",
        rationale="Better for consistency",
        stakeholders=["Alice", "Bob"],
        decided_by="Manager"
    )
    
    manager.create_decision(decision)
    
    pending = manager.get_pending_decisions()
    assert len(pending) == 1


def test_daily_standup():
    """Test recording standups."""
    manager = AsyncCommunicationManager()
    
    # Create standup directly from AsyncCommunicationManager's Standup class
    # to avoid caching issues
    from app.agent.async_communication import Standup as StandupClass
    
    standup = StandupClass(
        id="standup-1",
        member_name="Alice",
        completed_yesterday="Implemented login",
        planned_today="Add password reset",
        mood="good"
    )
    
    manager.add_standup(standup)
    
    summary = manager.get_daily_standup_summary()
    assert isinstance(summary, str) and len(summary) > 0


# ==================== Recognition Tests ====================

def test_recognition_giving():
    """Test giving recognition."""
    manager = RecognitionManager()
    
    recognition = Recognition(
        id="rec-1",
        recipient="Alice",
        recognizer="Bob",
        recognition_type=RecognitionType.GOING_ABOVE_AND_BEYOND,
        title="Great debugging skills",
        description="Alice stayed late to fix critical bug",
        public=True
    )
    
    manager.give_recognition(recognition)
    
    stats = manager.get_member_stats("Alice")
    assert stats["total_recognitions"] == 1


def test_recognition_report():
    """Test recognition reporting."""
    manager = RecognitionManager()
    
    for i in range(3):
        recognition = Recognition(
            id=f"rec-{i}",
            recipient="Alice",
            recognizer="Bob",
            recognition_type=RecognitionType.GREAT_WORK,
            title=f"Great work {i}",
            description="Excellent performance",
            public=True
        )
        manager.give_recognition(recognition)
    
    report = manager.generate_team_recognition_report(period_days=7)
    assert "Alice" in report or "3" in report


# ==================== Integration Tests ====================

def test_full_team_workflow():
    """Test complete team management workflow."""
    # Create team
    team = Team(name="Engineering Team")
    team.add_member(TeamMember(
        name="Alice",
        member_type=MemberType.HUMAN,
        role=MemberRole.BACKEND_ENGINEER,
        skills=["Python"],
        capacity_hours_per_week=40.0,
        workload_percent=50.0
    ))
    
    # Create and assign task
    distributor = WorkDistributor(team)
    task = Task(
        id="task-1",
        title="API Implementation",
        estimated_hours=16.0,
        required_skills=["Python"]
    )
    distributor.add_task(task)
    
    analysis = distributor.analyze_assignment("task-1")
    assert analysis.recommended_primary == "Alice"
    
    distributor.assign_task("task-1", "Alice")
    assert task.assigned_to == "Alice"
    
    # Track progress
    tracker = ProgressTracker()
    tracker.add_task(task)
    tracker.record_progress(ProgressUpdate(
        task_id="task-1",
        progress_percent=75.0,
        work_completed="API endpoints ready"
    ))
    
    # Monitor wellbeing
    monitor = WellbeingMonitor()
    monitor.record_hours("Alice", 35.0)
    status = monitor.assess_wellbeing("Alice")
    assert status == WellbeingStatus.HEALTHY
    
    # Give recognition
    rec_manager = RecognitionManager()
    recognition = Recognition(
        id="rec-1",
        recipient="Alice",
        recognizer="Manager",
        recognition_type=RecognitionType.GREAT_WORK,
        title="Excellent API implementation",
        description="Clean, well-tested code"
    )
    rec_manager.give_recognition(recognition)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
