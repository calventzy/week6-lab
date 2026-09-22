"""Unit tests for duckfine.DuckFine.

Run with:  python -m unittest test_duckfine -v
"""

import unittest

from duckfine import DuckFine


class TestInit(unittest.TestCase):
    """Constructor: stored member id and opening balance."""

    def test_member_id_is_stored(self):
        self.assertEqual(DuckFine("M001").member_id, "M001")

    def test_total_owed_starts_at_zero(self):
        self.assertEqual(DuckFine("M001").total_owed, 0.0)

    def test_member_id_is_not_validated(self):
        # __init__ accepts whatever it is given, including None.
        self.assertIsNone(DuckFine(None).member_id)

    def test_each_fine_has_its_own_total(self):
        first, second = DuckFine("M001"), DuckFine("M002")
        first.charge(10)
        self.assertEqual(second.total_owed, 0.0)


class TestClassConstants(unittest.TestCase):
    """The published fee policy."""

    def test_daily_fee(self):
        self.assertEqual(DuckFine.DAILY_FEE, 0.50)

    def test_grace_days(self):
        self.assertEqual(DuckFine.GRACE_DAYS, 2)

    def test_max_fee(self):
        self.assertEqual(DuckFine.MAX_FEE, 5.00)


class TestChargeGracePeriod(unittest.TestCase):
    """Days inside the grace period are forgiven."""

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_returned_on_time_is_free(self):
        self.assertEqual(self.fine.charge(0), 0.0)

    def test_one_day_late_is_free(self):
        self.assertEqual(self.fine.charge(1), 0.0)

    def test_last_grace_day_is_free(self):
        self.assertEqual(self.fine.charge(2), 0.0)

    def test_first_chargeable_day_is_one_daily_fee(self):
        self.assertEqual(self.fine.charge(3), 0.50)

    def test_free_charge_leaves_total_owed_at_zero(self):
        self.fine.charge(2)
        self.assertEqual(self.fine.total_owed, 0.0)


class TestChargeStandardFee(unittest.TestCase):
    """Standard (non-deluxe) fees below the cap."""

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_five_days_late_charges_three_days(self):
        self.assertEqual(self.fine.charge(5), 1.50)

    def test_ten_days_late_charges_eight_days(self):
        self.assertEqual(self.fine.charge(10), 4.00)

    def test_fee_exactly_at_the_cap_is_not_reduced(self):
        # 12 - 2 grace days = 10 chargeable days x 0.50 = 5.00, the cap itself.
        self.assertEqual(self.fine.charge(12), 5.00)

    def test_charge_adds_the_fee_to_total_owed(self):
        self.fine.charge(5)
        self.assertEqual(self.fine.total_owed, 1.50)


class TestChargeDeluxe(unittest.TestCase):
    """The deluxe flag doubles the fee before the cap is applied."""

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_deluxe_doubles_a_standard_fee(self):
        self.assertEqual(self.fine.charge(3, deluxe=True), 1.00)

    def test_deluxe_is_accepted_positionally(self):
        self.assertEqual(self.fine.charge(3, True), 1.00)

    def test_deluxe_defaults_to_false(self):
        self.assertEqual(self.fine.charge(3), 0.50)

    def test_deluxe_does_not_double_a_forgiven_charge(self):
        self.assertEqual(self.fine.charge(2, deluxe=True), 0.0)

    def test_deluxe_reaches_the_cap_in_half_the_days(self):
        # 7 - 2 = 5 chargeable days x 0.50 x 2 = 5.00, the cap itself.
        self.assertEqual(self.fine.charge(7, deluxe=True), 5.00)

    def test_truthy_non_boolean_doubles_the_fee(self):
        self.assertEqual(self.fine.charge(3, deluxe="yes"), 1.00)


class TestChargeCap(unittest.TestCase):
    """A single fine never exceeds MAX_FEE."""

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_standard_fee_is_capped(self):
        self.assertEqual(self.fine.charge(100), 5.00)

    def test_deluxe_fee_is_capped(self):
        self.assertEqual(self.fine.charge(100, deluxe=True), 5.00)

    def test_capped_charge_adds_only_the_cap_to_total_owed(self):
        self.fine.charge(100)
        self.assertEqual(self.fine.total_owed, 5.00)

    def test_cap_applies_per_charge_not_to_the_running_total(self):
        self.fine.charge(100)
        self.fine.charge(100)
        self.assertEqual(self.fine.total_owed, 10.00)


class TestChargeValidation(unittest.TestCase):
    """Negative lateness is rejected."""

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_negative_days_late_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.fine.charge(-1)

    def test_error_message_explains_the_problem(self):
        with self.assertRaisesRegex(ValueError, "days_late must not be negative"):
            self.fine.charge(-1)

    def test_rejected_charge_leaves_total_owed_unchanged(self):
        self.fine.charge(5)
        with self.assertRaises(ValueError):
            self.fine.charge(-1)
        self.assertEqual(self.fine.total_owed, 1.50)

    def test_negative_days_late_is_rejected_even_when_deluxe(self):
        with self.assertRaises(ValueError):
            self.fine.charge(-1, deluxe=True)

    def test_non_numeric_days_late_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.fine.charge("3")


class TestAccumulation(unittest.TestCase):
    """total_owed across repeated charges."""

    def setUp(self):
        self.fine = DuckFine("M001")

    def test_successive_charges_accumulate(self):
        self.fine.charge(3)
        self.fine.charge(5)
        self.assertEqual(self.fine.total_owed, 2.00)

    def test_forgiven_charges_do_not_change_the_total(self):
        self.fine.charge(5)
        self.fine.charge(1)
        self.assertEqual(self.fine.total_owed, 1.50)

    def test_mixed_standard_and_deluxe_charges_accumulate(self):
        self.fine.charge(3)
        self.fine.charge(3, deluxe=True)
        self.assertEqual(self.fine.total_owed, 1.50)

    def test_charge_returns_only_the_new_fee_not_the_total(self):
        self.fine.charge(5)
        self.assertEqual(self.fine.charge(3), 0.50)


if __name__ == "__main__":
    unittest.main()
