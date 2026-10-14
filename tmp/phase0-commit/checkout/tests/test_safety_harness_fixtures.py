"""
Safety harness fixture loader and validator.

Tests that all fixture files are valid YAML, conform to schema, have unique IDs,
and guard references are valid (G01-G15 only).
"""

import yaml
import pytest
from pathlib import Path
from typing import Any
from backend.guards.definitions import validate_guard_id, list_guards


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture_file(filename: str) -> dict[str, Any]:
    """Load a YAML fixture file."""
    path = FIXTURES_DIR / filename
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestFixtureSchema:
    """Validate fixture structure and schema."""

    def test_all_fixture_files_exist(self):
        """Check all expected fixture files are present."""
        expected_files = [
            'group_a_unverified_claims.yaml',
            'group_b_fabricated_prices.yaml',
            'group_c_mismatched_deals.yaml',
        ]
        for filename in expected_files:
            path = FIXTURES_DIR / filename
            assert path.exists(), f"Fixture file not found: {filename}"

    def test_group_a_valid_yaml(self):
        """Group A fixture is valid YAML."""
        data = load_fixture_file('group_a_unverified_claims.yaml')
        assert data is not None
        assert 'cases' in data
        assert isinstance(data['cases'], dict)

    def test_group_b_valid_yaml(self):
        """Group B fixture is valid YAML."""
        data = load_fixture_file('group_b_fabricated_prices.yaml')
        assert data is not None
        assert 'cases' in data
        assert isinstance(data['cases'], dict)

    def test_group_c_valid_yaml(self):
        """Group C fixture is valid YAML."""
        data = load_fixture_file('group_c_mismatched_deals.yaml')
        assert data is not None
        assert 'cases' in data
        assert isinstance(data['cases'], dict)

    def test_group_a_has_minimum_cases(self):
        """Group A has at least 8 test cases."""
        data = load_fixture_file('group_a_unverified_claims.yaml')
        assert len(data['cases']) >= 8, f"Group A has {len(data['cases'])} cases, expected >= 8"

    def test_group_b_has_minimum_cases(self):
        """Group B has at least 8 test cases."""
        data = load_fixture_file('group_b_fabricated_prices.yaml')
        assert len(data['cases']) >= 8, f"Group B has {len(data['cases'])} cases, expected >= 8"

    def test_group_c_has_minimum_cases(self):
        """Group C has at least 8 test cases."""
        data = load_fixture_file('group_c_mismatched_deals.yaml')
        assert len(data['cases']) >= 8, f"Group C has {len(data['cases'])} cases, expected >= 8"


class TestFixtureCaseSchema:
    """Validate individual fixture case schema."""

    @staticmethod
    def _get_all_cases():
        """Get all cases from all fixture groups."""
        all_cases = []
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id, case in data['cases'].items():
                all_cases.append((case_id, case))
        return all_cases

    def test_case_has_required_fields(self):
        """Each case has all required fields."""
        required_fields = [
            'id',
            'category',
            'description',
            'should_allow',
            'inbound_email',
            'task_scope',
            'verified_facts',
            'model_draft',
            'expected_verdict',
            'expected_guards',
            'forbidden_outcomes',
            'notes',
        ]
        for case_id, case in self._get_all_cases():
            for field in required_fields:
                assert field in case, f"Case {case_id} missing field: {field}"

    def test_case_id_matches_key(self):
        """Case ID matches the dictionary key."""
        for case_id, case in self._get_all_cases():
            assert case['id'] == case_id, f"Case ID mismatch: key={case_id}, id={case['id']}"

    def test_case_category_valid(self):
        """Case category is A, B, or C."""
        for case_id, case in self._get_all_cases():
            assert case['category'] in ['A', 'B', 'C'], \
                f"Case {case_id} has invalid category: {case['category']}"

    def test_case_verdict_valid(self):
        """Case verdict is ALLOW, ASK, or BLOCK."""
        for case_id, case in self._get_all_cases():
            assert case['expected_verdict'] in ['ALLOW', 'ASK', 'BLOCK'], \
                f"Case {case_id} has invalid verdict: {case['expected_verdict']}"

    def test_case_guards_are_valid(self):
        """All guard references are valid (G01-G15)."""
        for case_id, case in self._get_all_cases():
            guards = case['expected_guards']
            assert isinstance(guards, list), f"Case {case_id} expected_guards must be list"
            for guard_id in guards:
                assert validate_guard_id(guard_id), \
                    f"Case {case_id} references invalid guard: {guard_id}"

    def test_case_no_unverified_guards(self):
        """All guard IDs are in defined list (G01-G15)."""
        valid_guards = list_guards()
        for case_id, case in self._get_all_cases():
            for guard_id in case['expected_guards']:
                assert guard_id in valid_guards, \
                    f"Case {case_id} has undefined guard: {guard_id}"

    def test_case_inbound_email_structure(self):
        """Inbound email has required fields."""
        for case_id, case in self._get_all_cases():
            email = case['inbound_email']
            assert 'from' in email, f"Case {case_id} email missing 'from'"
            assert 'subject' in email, f"Case {case_id} email missing 'subject'"
            assert 'body' in email, f"Case {case_id} email missing 'body'"

    def test_case_task_scope_structure(self):
        """Task scope has required fields."""
        for case_id, case in self._get_all_cases():
            scope = case['task_scope']
            assert 'contact_id' in scope, f"Case {case_id} task_scope missing 'contact_id'"
            assert 'deal_id' in scope, f"Case {case_id} task_scope missing 'deal_id'"

    def test_case_verified_facts_structure(self):
        """Verified facts have required top-level keys."""
        for case_id, case in self._get_all_cases():
            facts = case['verified_facts']
            assert 'deal' in facts, f"Case {case_id} facts missing 'deal'"
            assert 'customer' in facts, f"Case {case_id} facts missing 'customer'"

    def test_case_deal_facts_complete(self):
        """Deal facts contain expected fields."""
        for case_id, case in self._get_all_cases():
            deal = case['verified_facts']['deal']
            required = ['id', 'title', 'price_paise', 'contact_id']
            for field in required:
                assert field in deal, f"Case {case_id} deal facts missing '{field}'"

    def test_case_customer_facts_complete(self):
        """Customer facts contain expected fields."""
        for case_id, case in self._get_all_cases():
            customer = case['verified_facts']['customer']
            required = ['id', 'name', 'opted_in', 'company']
            for field in required:
                assert field in customer, f"Case {case_id} customer facts missing '{field}'"

    def test_case_model_draft_structure(self):
        """Model draft has subject and body."""
        for case_id, case in self._get_all_cases():
            draft = case['model_draft']
            assert 'subject' in draft, f"Case {case_id} draft missing 'subject'"
            assert 'body' in draft, f"Case {case_id} draft missing 'body'"

    def test_case_forbidden_outcomes_is_list(self):
        """Forbidden outcomes is a list."""
        for case_id, case in self._get_all_cases():
            assert isinstance(case['forbidden_outcomes'], list), \
                f"Case {case_id} forbidden_outcomes must be list"


class TestFixtureConsistency:
    """Check consistency across all fixtures."""

    def test_all_case_ids_unique(self):
        """All case IDs are unique across all fixture groups."""
        all_ids = set()
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id in data['cases'].keys():
                assert case_id not in all_ids, \
                    f"Duplicate case ID found: {case_id}"
                all_ids.add(case_id)

    def test_case_ids_follow_naming(self):
        """Case IDs follow pattern: Group letter + 3 digits (e.g., A001, B005, C008)."""
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            group_letter = filename[6]  # Extract A, B, or C from filename
            for case_id in data['cases'].keys():
                assert case_id.startswith(group_letter), \
                    f"Case {case_id} doesn't start with group letter {group_letter}"
                assert len(case_id) == 4, f"Case ID {case_id} should be 4 chars (e.g., A001)"
                assert case_id[1:].isdigit(), f"Case ID {case_id} should end with 3 digits"

    def test_price_values_are_integers(self):
        """All price values (price_paise) are integers (no floats)."""
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id, case in data['cases'].items():
                deal = case['verified_facts']['deal']
                assert isinstance(deal['price_paise'], int), \
                    f"Case {case_id} price_paise must be int, got {type(deal['price_paise'])}"
                if 'floor_price_paise' in deal:
                    assert isinstance(deal['floor_price_paise'], int), \
                        f"Case {case_id} floor_price_paise must be int"
                if 'discount_pct_max' in deal:
                    assert isinstance(deal['discount_pct_max'], int), \
                        f"Case {case_id} discount_pct_max must be int"

    def test_should_allow_matches_verdict(self):
        """should_allow flag generally aligns with expected_verdict."""
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id, case in data['cases'].items():
                should_allow = case['should_allow']
                verdict = case['expected_verdict']
                
                if should_allow:
                    assert verdict == 'ALLOW', \
                        f"Case {case_id}: should_allow=true but verdict={verdict}"
                else:
                    assert verdict in ['ASK', 'BLOCK'], \
                        f"Case {case_id}: should_allow=false but verdict={verdict}"

    def test_blocked_cases_have_guards(self):
        """Blocked/ASK cases have at least one guard specified."""
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id, case in data['cases'].items():
                if case['expected_verdict'] != 'ALLOW':
                    assert len(case['expected_guards']) > 0, \
                        f"Case {case_id} is {case['expected_verdict']} but has no guards"

    def test_allow_cases_have_no_guards(self):
        """Allow cases have no guards specified."""
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id, case in data['cases'].items():
                if case['expected_verdict'] == 'ALLOW':
                    assert len(case['expected_guards']) == 0, \
                        f"Case {case_id} is ALLOW but has guards: {case['expected_guards']}"

    def test_blocked_cases_have_forbidden_outcomes(self):
        """Blocked cases specify what should NOT happen."""
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id, case in data['cases'].items():
                if case['expected_verdict'] == 'BLOCK':
                    assert len(case['forbidden_outcomes']) > 0, \
                        f"Case {case_id} is BLOCK but has no forbidden_outcomes"


class TestFixtureRealism:
    """Validate that fixtures use realistic Indian B2B sales language and amounts."""

    def test_prices_in_inr_paise(self):
        """All prices are in paise (₹1 = 100 paise) with realistic Indian amounts."""
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id, case in data['cases'].items():
                price_paise = case['verified_facts']['deal']['price_paise']
                # Realistic range: ₹1 lakh to ₹10 crore (100 million to 1 billion paise)
                assert 10000000 <= price_paise <= 1000000000, \
                    f"Case {case_id} price {price_paise} paise outside realistic range"

    def test_discount_percentages_realistic(self):
        """Discount percentages are realistic (0-50%)."""
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id, case in data['cases'].items():
                max_discount = case['verified_facts']['deal']['discount_pct_max']
                assert 0 <= max_discount <= 50, \
                    f"Case {case_id} discount {max_discount}% unrealistic"

    def test_emails_from_indian_domains(self):
        """Email addresses use realistic Indian company domains."""
        indian_tlds = ['.in', '.co.in', '.com.in']
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id, case in data['cases'].items():
                email = case['inbound_email']['from']
                assert any(email.endswith(tld) for tld in indian_tlds), \
                    f"Case {case_id} email {email} doesn't use Indian domain"

    def test_contact_names_realistic(self):
        """Customer names are realistic for Indian B2B contacts."""
        # Simple check: names should be non-empty and reasonable length
        for filename in ['group_a_unverified_claims.yaml',
                         'group_b_fabricated_prices.yaml',
                         'group_c_mismatched_deals.yaml']:
            data = load_fixture_file(filename)
            for case_id, case in data['cases'].items():
                name = case['verified_facts']['customer']['name']
                assert len(name) > 2, f"Case {case_id} customer name too short: {name}"
                assert len(name) < 100, f"Case {case_id} customer name too long: {name}"


class TestFixtureCoverage:
    """Verify test cases cover important scenarios."""

    def test_group_a_covers_unverified_claims(self):
        """Group A has cases for various unverified claim types."""
        data = load_fixture_file('group_a_unverified_claims.yaml')
        descriptions = [case['description'].lower() for case in data['cases'].values()]
        
        # Check coverage of different claim types
        assert any('discount' in d for d in descriptions), \
            "Group A should cover unverified discount claims"
        assert any('shipping' in d or 'delivery' in d for d in descriptions), \
            "Group A should cover shipping/delivery claims"
        assert any('trial' in d or 'bonus' in d or 'warranty' in d for d in descriptions), \
            "Group A should cover various unverified benefits"

    def test_group_b_covers_price_fabrication(self):
        """Group B has cases for various price fabrication types."""
        data = load_fixture_file('group_b_fabricated_prices.yaml')
        descriptions = [case['description'].lower() for case in data['cases'].values()]
        
        assert any('digit' in d or 'typo' in d for d in descriptions), \
            "Group B should cover digit/typo errors"
        assert any('currency' in d for d in descriptions), \
            "Group B should cover currency mismatches"
        assert any('tax' in d or 'gst' in d for d in descriptions), \
            "Group B should cover tax treatment"
        assert any('rounding' in d for d in descriptions), \
            "Group B should cover rounding errors"
        assert any('floor' in d for d in descriptions), \
            "Group B should cover floor price violations"

    def test_group_c_covers_deal_leakage(self):
        """Group C has cases for various cross-deal leakage scenarios."""
        data = load_fixture_file('group_c_mismatched_deals.yaml')
        descriptions = [case['description'].lower() for case in data['cases'].values()]
        
        assert any('quote' in d or 'price' in d and 'deal' in d for d in descriptions), \
            "Group C should cover wrong deal quotes"
        assert any('customer' in d or 'contact' in d for d in descriptions), \
            "Group C should cover wrong customer references"
        assert any('confidential' in d or 'internal' in d for d in descriptions), \
            "Group C should cover confidentiality leaks"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
