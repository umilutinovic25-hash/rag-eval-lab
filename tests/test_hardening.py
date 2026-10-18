import pytest

from src import llm


@pytest.mark.parametrize(
    'span,passage,accepted',
    [
        ('Budget is 900 EUR per employee.', 'Budget is 800 EUR per employee.', False),
        ('Share passwords with colleagues from IT.', 'Never share passwords, also not with colleagues from IT.', False),
        ('share passwords', 'Never share passwords.', False),
        ('budget carry over', 'Unused budget does not carry over.', False),
        ('Never share passwords', 'Never share passwords, also not with colleagues from IT.', True),
        ('800 EUR', 'Budget is 800 EUR per employee.', True),
        ('  "PARKING is limited"  ', 'Parking is limited: spaces are shared.', True),
        ('not carry over', 'Unused budget does not carry over.', True),
    ],
)
def test_span_preserves_words_order_numbers_and_negation(span, passage, accepted):
    assert llm.span_is_in_passage(span, passage) is accepted
