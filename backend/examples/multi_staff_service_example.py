"""
Example script demonstrating multi-staff service contribution system.

This script shows the complete workflow:
1. Create a service with staff role templates
2. Create a bill with multi-staff contributions
3. View the calculated contributions

Run this script after running migrations to see the system in action.
"""

import requests
from typing import Dict, Any
import json

# Configuration
BASE_URL = "http://localhost:8000/api"
# Replace with actual auth token
AUTH_TOKEN = "your_auth_token_here"

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


def create_service_category() -> str:
    """Create a service category for specialized treatments."""
    url = f"{BASE_URL}/catalog/categories"
    data = {
        "name": "Specialized Treatments",
        "description": "Complex treatments requiring multiple staff",
        "display_order": 10
    }

    response = requests.post(url, json=data, headers=HEADERS)
    response.raise_for_status()

    category = response.json()
    print(f"✓ Created category: {category['name']} (ID: {category['id']})")
    return category["id"]


def create_botox_service(category_id: str) -> str:
    """Create Botox treatment service."""
    url = f"{BASE_URL}/catalog/services"
    data = {
        "category_id": category_id,
        "name": "Botox Treatment",
        "description": "Complete botox application with hair treatment",
        "base_price": 500000,  # ₹5000
        "duration_minutes": 65,
        "display_order": 1
    }

    response = requests.post(url, json=data, headers=HEADERS)
    response.raise_for_status()

    service = response.json()
    print(f"✓ Created service: {service['name']} - ₹{service['base_price']/100:.2f}")
    return service["id"]


def create_staff_templates(service_id: str) -> None:
    """Create staff role templates for Botox service."""
    templates = [
        {
            "role_name": "Botox Application",
            "role_description": "Apply botox to designated facial areas",
            "sequence_order": 1,
            "contribution_type": "percentage",
            "default_contribution_percent": 50,
            "estimated_duration_minutes": 30,
            "is_required": True
        },
        {
            "role_name": "Hair Wash",
            "role_description": "Gentle hair wash post-treatment",
            "sequence_order": 2,
            "contribution_type": "percentage",
            "default_contribution_percent": 25,
            "estimated_duration_minutes": 15,
            "is_required": True
        },
        {
            "role_name": "Hair Drying & Styling",
            "role_description": "Dry and style hair",
            "sequence_order": 3,
            "contribution_type": "percentage",
            "default_contribution_percent": 25,
            "estimated_duration_minutes": 20,
            "is_required": False
        }
    ]

    url = f"{BASE_URL}/catalog/services/{service_id}/staff-templates"

    print(f"\n✓ Creating staff role templates:")
    for template in templates:
        response = requests.post(url, json=template, headers=HEADERS)
        response.raise_for_status()

        created = response.json()
        print(f"  - {created['role_name']}: {created['default_contribution_percent']}% "
              f"(~{created['estimated_duration_minutes']} min)")


def create_bill_with_multi_staff(service_id: str, staff_ids: Dict[str, str]) -> Dict[str, Any]:
    """
    Create a bill with multi-staff contributions.

    Args:
        service_id: Botox service ID
        staff_ids: Dict mapping roles to staff IDs
            e.g., {"application": "staff_id_1", "wash": "staff_id_2", "styling": "staff_id_3"}

    Returns:
        Created bill data
    """
    url = f"{BASE_URL}/pos/bills"

    # Example 1: Percentage-based split
    bill_data = {
        "customer_name": "Priya Sharma",
        "customer_phone": "9876543210",
        "items": [
            {
                "service_id": service_id,
                "quantity": 1,
                "staff_contributions": [
                    {
                        "staff_id": staff_ids["application"],
                        "role_in_service": "Botox Application",
                        "sequence_order": 1,
                        "contribution_split_type": "percentage",
                        "contribution_percent": 50
                    },
                    {
                        "staff_id": staff_ids["wash"],
                        "role_in_service": "Hair Wash",
                        "sequence_order": 2,
                        "contribution_split_type": "percentage",
                        "contribution_percent": 25
                    },
                    {
                        "staff_id": staff_ids["styling"],
                        "role_in_service": "Hair Drying & Styling",
                        "sequence_order": 3,
                        "contribution_split_type": "percentage",
                        "contribution_percent": 25
                    }
                ]
            }
        ]
    }

    response = requests.post(url, json=bill_data, headers=HEADERS)
    response.raise_for_status()

    bill = response.json()
    print(f"\n✓ Created bill (ID: {bill['id']})")
    print(f"  Total: ₹{bill['rounded_total']/100:.2f}")
    return bill


def create_bill_with_hybrid_calculation(service_id: str, staff_ids: Dict[str, str]) -> Dict[str, Any]:
    """
    Create a bill with hybrid contribution calculation.

    Hybrid combines:
    - 40% by base percentage
    - 30% by time spent
    - 30% by skill complexity
    """
    url = f"{BASE_URL}/pos/bills"

    bill_data = {
        "customer_name": "Anjali Verma",
        "customer_phone": "9876543211",
        "items": [
            {
                "service_id": service_id,
                "quantity": 1,
                "staff_contributions": [
                    {
                        "staff_id": staff_ids["application"],
                        "role_in_service": "Botox Application",
                        "sequence_order": 1,
                        "contribution_split_type": "hybrid",
                        "contribution_percent": 50,
                        "time_spent_minutes": 35,
                        "notes": "Senior specialist, extra time for precision"
                    },
                    {
                        "staff_id": staff_ids["wash"],
                        "role_in_service": "Hair Wash",
                        "sequence_order": 2,
                        "contribution_split_type": "hybrid",
                        "contribution_percent": 25,
                        "time_spent_minutes": 12,
                        "notes": "Quick and efficient"
                    },
                    {
                        "staff_id": staff_ids["styling"],
                        "role_in_service": "Hair Drying & Styling",
                        "sequence_order": 3,
                        "contribution_split_type": "hybrid",
                        "contribution_percent": 25,
                        "time_spent_minutes": 18
                    }
                ]
            }
        ]
    }

    response = requests.post(url, json=bill_data, headers=HEADERS)
    response.raise_for_status()

    bill = response.json()
    print(f"\n✓ Created bill with HYBRID calculation (ID: {bill['id']})")
    print(f"  Total: ₹{bill['rounded_total']/100:.2f}")
    return bill


def display_bill_contributions(bill: Dict[str, Any]) -> None:
    """Display staff contributions from a bill."""
    print(f"\n{'='*60}")
    print(f"BILL SUMMARY - Invoice: {bill.get('invoice_number', 'DRAFT')}")
    print(f"{'='*60}")
    print(f"Customer: {bill['customer_name']}")
    print(f"Total: ₹{bill['rounded_total']/100:.2f}")
    print(f"\nServices:")

    for item in bill["items"]:
        print(f"\n  {item['item_name']} - ₹{item['line_total']/100:.2f}")

        if item.get("staff_contributions"):
            print(f"  Staff Contributions:")

            for contrib in sorted(item["staff_contributions"], key=lambda x: x["sequence_order"]):
                print(f"    {contrib['sequence_order']}. {contrib['role_in_service']}")
                print(f"       Staff ID: {contrib['staff_id']}")
                print(f"       Contribution: ₹{contrib['contribution_amount']/100:.2f}")

                if contrib.get("time_spent_minutes"):
                    print(f"       Time Spent: {contrib['time_spent_minutes']} minutes")

                # Show hybrid breakdown if available
                if contrib.get("base_percent_component"):
                    print(f"       Breakdown:")
                    print(f"         Base ({contrib.get('contribution_percent', 0)}%): "
                          f"₹{contrib['base_percent_component']/100:.2f}")
                    if contrib.get("time_component"):
                        print(f"         Time: ₹{contrib['time_component']/100:.2f}")
                    if contrib.get("skill_component"):
                        print(f"         Skill: ₹{contrib['skill_component']/100:.2f}")

    print(f"{'='*60}\n")


def main():
    """Run the complete example workflow."""
    print("=" * 60)
    print(" Multi-Staff Service Contribution System - Example")
    print("=" * 60)

    # Step 1: Create category
    print("\n[STEP 1] Creating service category...")
    category_id = create_service_category()

    # Step 2: Create service
    print("\n[STEP 2] Creating Botox service...")
    service_id = create_botox_service(category_id)

    # Step 3: Create staff templates
    print("\n[STEP 3] Creating staff role templates...")
    create_staff_templates(service_id)

    # Step 4: Simulate staff IDs (replace with actual staff IDs from your system)
    staff_ids = {
        "application": "01STAFF_AAAAAAAAAAAAAAAAAAA",  # Replace with real staff ID
        "wash": "01STAFF_BBBBBBBBBBBBBBBBBBB",          # Replace with real staff ID
        "styling": "01STAFF_CCCCCCCCCCCCCCCCCCC"       # Replace with real staff ID
    }

    print("\n[STEP 4] Creating bills with multi-staff contributions...")

    # Example 1: Percentage-based split
    print("\n--- Example 1: Percentage-based Split ---")
    bill1 = create_bill_with_multi_staff(service_id, staff_ids)
    display_bill_contributions(bill1)

    # Example 2: Hybrid calculation
    print("\n--- Example 2: Hybrid Calculation ---")
    bill2 = create_bill_with_hybrid_calculation(service_id, staff_ids)
    display_bill_contributions(bill2)

    print("\n✅ Example completed successfully!")
    print("\nKey Takeaways:")
    print("1. Staff templates define standard roles and splits for services")
    print("2. At checkout, assign actual staff to each role")
    print("3. System automatically calculates contributions")
    print("4. Hybrid mode combines base %, time, and skill weights")
    print("5. All contributions always sum to exact service price")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. Backend is running (docker-compose up)")
        print("2. Migration has been run (alembic upgrade head)")
        print("3. AUTH_TOKEN is valid")
        print("4. Staff IDs in staff_ids dict are real staff IDs from your system")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
