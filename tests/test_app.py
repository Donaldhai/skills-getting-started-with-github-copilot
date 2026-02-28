"""
Comprehensive pytest tests for the FastAPI activities management backend.

Tests cover:
- GET /activities endpoint
- POST /activities/{activity}/signup endpoint
- Error handling and validation
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """
    Fixture providing a test client for the FastAPI app.
    
    This ensures test isolation by creating a fresh test client
    for each test function.
    """
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """
    Fixture to reset activities to initial state before and after each test.
    
    This ensures test isolation and prevents test interaction.
    """
    # Store original activities state
    from app import activities
    original_state = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state after test
    activities.clear()
    for name, activity in original_state.items():
        activities[name] = activity


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return at least the known activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        assert "Basketball Team" in data
        assert "Tennis Club" in data
        assert "Drama Club" in data
        assert "Art Class" in data
        assert "Debate Team" in data
        assert "Math Club" in data
    
    def test_get_activities_returns_proper_structure(self, client, reset_activities):
        """Test that GET /activities returns proper structure with all required fields"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Pick one activity and verify structure
        chess_club = data["Chess Club"]
        
        assert "description" in chess_club
        assert isinstance(chess_club["description"], str)
        
        assert "schedule" in chess_club
        assert isinstance(chess_club["schedule"], str)
        
        assert "max_participants" in chess_club
        assert isinstance(chess_club["max_participants"], int)
        
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
    
    def test_get_activities_participants_are_email_strings(self, client, reset_activities):
        """Test that participants list contains email addresses"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that participants are all strings (email addresses)
        for activity_name, activity in data.items():
            assert isinstance(activity["participants"], list)
            for participant in activity["participants"]:
                assert isinstance(participant, str)
                assert "@" in participant  # Basic email validation


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successfully_adds_participant(self, client, reset_activities):
        """Test that POST /activities/{activity}/signup successfully adds a participant"""
        activity_name = "Chess Club"
        new_email = "newstudent@mergington.edu"
        
        # Verify student is not already signed up
        response = client.get("/activities")
        assert new_email not in response.json()[activity_name]["participants"]
        
        # Sign up the student
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_email}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {new_email} for {activity_name}"
        
        # Verify student is now in the activity
        response = client.get("/activities")
        assert new_email in response.json()[activity_name]["participants"]
    
    def test_signup_returns_404_for_nonexistent_activity(self, client, reset_activities):
        """Test that POST /activities/{activity}/signup fails with 404 for non-existent activity"""
        nonexistent_activity = "Nonexistent Activity"
        email = "student@mergington.edu"
        
        response = client.post(
            f"/activities/{nonexistent_activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_signup_fails_when_student_already_signed_up(self, client, reset_activities):
        """Test that POST /activities/{activity}/signup fails with 400 when student already signed up"""
        activity_name = "Chess Club"
        # michael@mergington.edu is already signed up for Chess Club
        existing_email = "michael@mergington.edu"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": existing_email}
        )
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up"
    
    def test_signup_requires_email_parameter(self, client, reset_activities):
        """Test that email parameter is required for signup"""
        activity_name = "Chess Club"
        
        # Try to sign up without email parameter
        response = client.post(f"/activities/{activity_name}/signup")
        
        # Should fail with 422 (missing required parameter)
        assert response.status_code == 422
    
    def test_signup_with_different_activities(self, client, reset_activities):
        """Test signing up for different activities works independently"""
        email = "versatile@mergington.edu"
        activities_to_join = ["Chess Club", "Programming Class", "Basketball Team"]
        
        for activity_name in activities_to_join:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        response = client.get("/activities")
        activities_data = response.json()
        
        for activity_name in activities_to_join:
            assert email in activities_data[activity_name]["participants"]
    
    def test_signup_preserves_existing_participants(self, client, reset_activities):
        """Test that signing up new participant preserves existing participants"""
        activity_name = "Gym Class"
        new_email = "newcomer@mergington.edu"
        
        # Get initial participant count
        response = client.get("/activities")
        initial_participants = response.json()[activity_name]["participants"].copy()
        initial_count = len(initial_participants)
        
        # Sign up new participant
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_email}
        )
        assert response.status_code == 200
        
        # Verify all original participants are still there
        response = client.get("/activities")
        final_participants = response.json()[activity_name]["participants"]
        
        assert len(final_participants) == initial_count + 1
        for original_participant in initial_participants:
            assert original_participant in final_participants


class TestActivityStructureValidation:
    """Tests to validate activity data structure and constraints"""
    
    def test_all_activities_have_max_participants(self, client, reset_activities):
        """Test that all activities have a max_participants value"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "max_participants" in activity
            assert isinstance(activity["max_participants"], int)
            assert activity["max_participants"] > 0
    
    def test_all_activities_have_schedule(self, client, reset_activities):
        """Test that all activities have a schedule"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "schedule" in activity
            assert isinstance(activity["schedule"], str)
            assert len(activity["schedule"]) > 0
    
    def test_all_activities_have_description(self, client, reset_activities):
        """Test that all activities have a description"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "description" in activity
            assert isinstance(activity["description"], str)
            assert len(activity["description"]) > 0


class TestErrorHandling:
    """Tests for error handling and edge cases"""
    
    def test_signup_with_special_characters_in_activity_name(self, client, reset_activities):
        """Test signup with special characters in activity name"""
        activity_name = "Chess Club@#$"
        email = "student@mergington.edu"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
    
    def test_multiple_sequential_signups_same_activity(self, client, reset_activities):
        """Test multiple different students signing up for the same activity"""
        activity_name = "Programming Class"
        emails = [
            "alice@mergington.edu",
            "bob@mergington.edu",
            "charlie@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all signed up
        response = client.get("/activities")
        participants = response.json()[activity_name]["participants"]
        for email in emails:
            assert email in participants
