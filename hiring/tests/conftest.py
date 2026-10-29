import pytest

from hiring.models import Candidate


@pytest.fixture
def make_candidate(db):
    def make(**fields):
        defaults = {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "source": Candidate.Source.REFERRAL,
        }
        return Candidate.objects.create(**(defaults | fields))

    return make


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(username="staff", password="staff-pass-123")


@pytest.fixture
def staff_client(client, staff_user):
    client.force_login(staff_user)
    return client
