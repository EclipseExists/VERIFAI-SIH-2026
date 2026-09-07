"""
VERIFAI — Case API Tests (Placeholder)
========================================

Full case tests require a running PostgreSQL database.
We will add proper tests after confirming the local DB setup works.

WHAT WILL GO HERE:
- test_create_case: POST /api/v1/cases creates a case and returns 201
- test_list_cases: GET /api/v1/cases returns a list
- test_get_case: GET /api/v1/cases/{id} returns a specific case
- test_get_case_not_found: GET with a fake UUID returns 404
- test_submit_decision: POST /api/v1/cases/{id}/decision records a decision
- test_submit_decision_not_found: Decision on a nonexistent case returns 404

These will use a test database (separate from development data).
"""


def test_placeholder():
    """
    Placeholder test to verify pytest runs.
    Replace with real tests once DB is configured.
    """
    assert True, "Placeholder — real case tests need a test database"

