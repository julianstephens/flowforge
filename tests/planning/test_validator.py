from flowforge.planning.io import load_and_validate_plan
from flowforge.planning.validator import Validator


class TestValidator:
    def test_valid_plan(self, test_plans):
        for valid_plan_path in test_plans["valid"]:
            plan = load_and_validate_plan(valid_plan_path)
            validator = Validator(plan, valid_plan_path)
            diags = validator.validate()
            assert len(diags) == 0, f"Expected no diagnostics, but got: {diags}"

    def test_invalid_plan(self, test_plans):
        for invalid_plan_path in test_plans["invalid"]:
            plan = load_and_validate_plan(invalid_plan_path)
            validator = Validator(plan, invalid_plan_path)
            diags = validator.validate()
            assert len(diags) > 0, "Expected diagnostics for invalid plan, but got none"
