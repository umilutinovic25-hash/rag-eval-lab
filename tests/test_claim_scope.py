import pytest
from src.claim_checks import claim_risks


@pytest.mark.parametrize('answer,source,risk', [
    ('Each team has a budget of 800 EUR per year.', 'Each employee has a training budget of 800 EUR per year.', 'scope_conflict'),
    ('The budget is 800 EUR per person.', 'The budget is 800 EUR per team.', 'scope_conflict'),
    ('Employees work remotely at least 3 days per week.', 'Employees can work remotely up to 3 days per week.', 'bound_conflict'),
    ('Passwords must contain at most 12 characters.', 'Passwords must contain at least 12 characters.', 'bound_conflict'),
    ('Employees must work remotely 3 days per week.', 'Employees can work remotely up to 3 days per week.', 'modality_conflict'),
    ('Multi-factor authentication is optional for VPN.', 'Multi-factor authentication is required for VPN.', 'modality_conflict'),
])
def test_reject_changed_claim_scope(answer, source, risk):
    assert risk in claim_risks(answer, [source])


@pytest.mark.parametrize('answer,source', [
    ('The training budget is 800 EUR per person.', 'Each employee has a training budget of 800 EUR per year.'),
    ('Employees can work remotely 3 days per week.', 'Employees can work remotely up to 3 days per week.'),
    ('Employees may work remotely up to 3 days per week.', 'Employees can work remotely up to 3 days per week.'),
    ('The training budget is 800 EUR per employee.', 'Each employee has a budget of 800 EUR. Training is agreed with the team lead.'),
    ('Contact IT support by phone.', 'IT support may be contacted by phone. Security incidents must be reported.'),
    ('Passwords require at least 12 characters.', 'Passwords must contain at least 12 characters.'),
])
def test_preserve_supported_claim_scope(answer, source):
    assert not claim_risks(answer, [source])
