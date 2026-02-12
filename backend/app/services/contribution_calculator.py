"""
Service for calculating staff contributions in multi-staff services.

Supports multiple calculation methods:
- PERCENTAGE: Split by predefined percentages
- FIXED: Predefined fixed amounts
- EQUAL: Equal split among all staff
- TIME_BASED: Split proportional to time spent
- HYBRID: Combination of base %, time, and skill weights
"""

from typing import List, Dict, Optional
from decimal import Decimal
from app.models.billing import ContributionSplitType


class ContributionCalculationError(Exception):
    """Raised when contribution calculation fails validation."""
    pass


class ContributionCalculator:
    """Calculate staff contributions for multi-staff services."""

    # Hybrid split weights (must sum to 100)
    BASE_PERCENT_WEIGHT = 40  # % of total allocated by base percentage
    TIME_WEIGHT = 30          # % of total allocated by time spent
    SKILL_WEIGHT = 30         # % of total allocated by skill complexity

    # Skill complexity weights by role type
    # Higher number = more complex/valuable role
    SKILL_WEIGHTS = {
        # Botox & Medical
        "Botox Application": 3,
        "Injection": 3,
        "Laser Treatment": 3,

        # Hair Services
        "Hair Coloring": 3,
        "Hair Cutting": 2,
        "Hair Styling": 2,
        "Hair Wash": 1,
        "Hair Drying": 1,
        "Blow Dry": 1,

        # Spa & Beauty
        "Facial Application": 2,
        "Massage": 2,
        "Makeup Application": 3,
        "Manicure": 2,
        "Pedicure": 2,

        # Support Tasks
        "Cleanup": 1,
        "Prep Work": 1,
        "Product Application": 1,

        # Default
        "default": 2
    }

    @classmethod
    def calculate_contributions(
        cls,
        line_total_paise: int,
        contributions: List[Dict],
        split_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Main entry point for calculating staff contributions.

        Args:
            line_total_paise: Total amount to split (in paise)
            contributions: List of contribution dicts with staff info
            split_type: Override split type (if all use the same type)

        Returns:
            Updated contributions with calculated contribution_amount

        Raises:
            ContributionCalculationError: If validation fails
        """
        if not contributions:
            raise ContributionCalculationError("No contributions provided")

        if line_total_paise <= 0:
            raise ContributionCalculationError("Line total must be positive")

        # Determine split type (all must be the same or use override)
        split_types = set(
            c.get("contribution_split_type", split_type)
            for c in contributions
        )

        if len(split_types) > 1:
            raise ContributionCalculationError(
                f"All contributions must use the same split type. Found: {split_types}"
            )

        actual_split_type = split_types.pop()

        # Route to appropriate calculator
        if actual_split_type == ContributionSplitType.PERCENTAGE.value:
            return cls.calculate_percentage(line_total_paise, contributions)
        elif actual_split_type == ContributionSplitType.FIXED.value:
            return cls.calculate_fixed(line_total_paise, contributions)
        elif actual_split_type == ContributionSplitType.EQUAL.value:
            return cls.calculate_equal(line_total_paise, contributions)
        elif actual_split_type == ContributionSplitType.TIME_BASED.value:
            return cls.calculate_time_based(line_total_paise, contributions)
        elif actual_split_type == ContributionSplitType.HYBRID.value:
            return cls.calculate_hybrid(line_total_paise, contributions)
        else:
            raise ContributionCalculationError(
                f"Unknown split type: {actual_split_type}"
            )

    @classmethod
    def calculate_percentage(
        cls,
        line_total_paise: int,
        contributions: List[Dict]
    ) -> List[Dict]:
        """
        Calculate simple percentage-based contributions.

        Args:
            line_total_paise: Total amount in paise
            contributions: List with 'contribution_percent' key

        Returns:
            Updated contributions with 'contribution_amount'

        Raises:
            ContributionCalculationError: If percentages don't sum to 100
        """
        total_percent = sum(
            c.get("contribution_percent", 0)
            for c in contributions
        )

        if total_percent != 100:
            raise ContributionCalculationError(
                f"Contribution percentages must sum to 100, got {total_percent}"
            )

        # Calculate base amounts
        for contrib in contributions:
            percent = contrib.get("contribution_percent", 0)
            contrib["contribution_amount"] = int(line_total_paise * percent / 100)

        # Handle rounding remainder
        cls._distribute_remainder(line_total_paise, contributions)

        return contributions

    @classmethod
    def calculate_fixed(
        cls,
        line_total_paise: int,
        contributions: List[Dict]
    ) -> List[Dict]:
        """
        Use predefined fixed amounts.

        Args:
            line_total_paise: Total amount in paise
            contributions: List with 'contribution_fixed' key

        Returns:
            Updated contributions with 'contribution_amount'

        Raises:
            ContributionCalculationError: If fixed amounts don't match total
        """
        total_fixed = sum(
            c.get("contribution_fixed", 0)
            for c in contributions
        )

        if total_fixed != line_total_paise:
            raise ContributionCalculationError(
                f"Fixed contributions ({total_fixed} paise) must equal "
                f"line total ({line_total_paise} paise)"
            )

        for contrib in contributions:
            contrib["contribution_amount"] = contrib.get("contribution_fixed", 0)

        return contributions

    @classmethod
    def calculate_equal(
        cls,
        line_total_paise: int,
        contributions: List[Dict]
    ) -> List[Dict]:
        """
        Calculate equal split among all staff.

        Args:
            line_total_paise: Total amount in paise
            contributions: List of contribution dicts

        Returns:
            Updated contributions with 'contribution_amount'
        """
        num_staff = len(contributions)
        base_amount = line_total_paise // num_staff
        remainder = line_total_paise % num_staff

        for i, contrib in enumerate(contributions):
            contrib["contribution_amount"] = base_amount
            # Give remainder to first staff member
            if i == 0:
                contrib["contribution_amount"] += remainder

        return contributions

    @classmethod
    def calculate_time_based(
        cls,
        line_total_paise: int,
        contributions: List[Dict]
    ) -> List[Dict]:
        """
        Calculate contributions based on time spent.

        Args:
            line_total_paise: Total amount in paise
            contributions: List with 'time_spent_minutes' key

        Returns:
            Updated contributions with 'contribution_amount'

        Raises:
            ContributionCalculationError: If time data is missing
        """
        total_time = sum(
            c.get("time_spent_minutes", 0)
            for c in contributions
        )

        if total_time <= 0:
            raise ContributionCalculationError(
                "Time-based calculation requires time_spent_minutes for all staff"
            )

        # Calculate proportional amounts
        for contrib in contributions:
            time_minutes = contrib.get("time_spent_minutes", 0)
            contrib["contribution_amount"] = int(
                line_total_paise * time_minutes / total_time
            )

        # Handle rounding remainder
        cls._distribute_remainder(line_total_paise, contributions)

        return contributions

    @classmethod
    def calculate_hybrid(
        cls,
        line_total_paise: int,
        contributions: List[Dict]
    ) -> List[Dict]:
        """
        Calculate hybrid contributions based on base %, time, and skill.

        Formula:
        - 40% of total split by base percentage
        - 30% of total split by time spent
        - 30% of total split by skill complexity

        Args:
            line_total_paise: Total amount in paise
            contributions: List with 'contribution_percent', 'time_spent_minutes',
                          and 'role_in_service' keys

        Returns:
            Updated contributions with component breakdowns

        Raises:
            ContributionCalculationError: If required data is missing
        """
        # Validate required data
        total_percent = sum(c.get("contribution_percent", 0) for c in contributions)
        if total_percent != 100:
            raise ContributionCalculationError(
                f"Base percentages must sum to 100 for hybrid calculation, got {total_percent}"
            )

        total_time = sum(c.get("time_spent_minutes", 0) for c in contributions)
        if total_time <= 0:
            raise ContributionCalculationError(
                "Hybrid calculation requires time_spent_minutes for all staff"
            )

        # Calculate component pools
        base_pool = int(line_total_paise * cls.BASE_PERCENT_WEIGHT / 100)
        time_pool = int(line_total_paise * cls.TIME_WEIGHT / 100)
        skill_pool = int(line_total_paise * cls.SKILL_WEIGHT / 100)

        # Calculate skill weights
        total_skill_weight = sum(
            cls._get_skill_weight(c.get("role_in_service", ""))
            for c in contributions
        )

        # Calculate components for each staff member
        for contrib in contributions:
            base_percent = contrib.get("contribution_percent", 0)
            time_minutes = contrib.get("time_spent_minutes", 0)
            role = contrib.get("role_in_service", "")
            skill_weight = cls._get_skill_weight(role)

            # Base component (by percentage)
            base_component = int(base_pool * base_percent / 100)

            # Time component (by time spent)
            time_component = int(time_pool * time_minutes / total_time)

            # Skill component (by role complexity)
            skill_component = int(skill_pool * skill_weight / total_skill_weight)

            # Store components
            contrib["base_percent_component"] = base_component
            contrib["time_component"] = time_component
            contrib["skill_component"] = skill_component
            contrib["contribution_amount"] = (
                base_component + time_component + skill_component
            )

        # Handle rounding remainder
        cls._distribute_remainder(line_total_paise, contributions)

        return contributions

    @classmethod
    def _get_skill_weight(cls, role: str) -> int:
        """
        Get skill complexity weight for a role.

        Args:
            role: Role name (e.g., "Botox Application")

        Returns:
            Skill weight (higher = more complex/valuable)
        """
        return cls.SKILL_WEIGHTS.get(role, cls.SKILL_WEIGHTS["default"])

    @classmethod
    def _distribute_remainder(cls, total: int, contributions: List[Dict]) -> None:
        """
        Distribute rounding remainder to ensure exact total.

        Adds/subtracts remainder from the staff member with highest contribution.

        Args:
            total: Expected total in paise
            contributions: List of contributions (modified in place)
        """
        allocated = sum(c["contribution_amount"] for c in contributions)
        remainder = total - allocated

        if remainder != 0:
            # Find contribution with highest amount
            max_contrib = max(contributions, key=lambda c: c["contribution_amount"])
            max_contrib["contribution_amount"] += remainder

    @classmethod
    def validate_contributions(
        cls,
        contributions: List[Dict],
        line_total_paise: int
    ) -> None:
        """
        Validate contributions after calculation.

        Args:
            contributions: Calculated contributions
            line_total_paise: Expected total

        Raises:
            ContributionCalculationError: If validation fails
        """
        # Check total matches
        total_allocated = sum(c["contribution_amount"] for c in contributions)
        if total_allocated != line_total_paise:
            raise ContributionCalculationError(
                f"Total contributions ({total_allocated}) must equal "
                f"line total ({line_total_paise})"
            )

        # Check all amounts are non-negative
        for contrib in contributions:
            if contrib["contribution_amount"] < 0:
                raise ContributionCalculationError(
                    f"Contribution amount cannot be negative: {contrib}"
                )

        # Check sequence order is unique
        sequence_orders = [c.get("sequence_order") for c in contributions]
        if len(sequence_orders) != len(set(sequence_orders)):
            raise ContributionCalculationError(
                "Sequence orders must be unique"
            )
