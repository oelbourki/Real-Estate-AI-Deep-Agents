"""Financial analysis tools for real estate investment calculations."""

from pydantic import BaseModel, Field
from langchain_core.tools import tool
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ROIInput(BaseModel):
    """Input schema for ROI calculation."""

    purchase_price: float = Field(..., description="Property purchase price")
    monthly_rent: Optional[float] = Field(
        None, description="Expected monthly rental income"
    )
    annual_rent: Optional[float] = Field(
        None, description="Expected annual rental income (alternative to monthly)"
    )
    down_payment: float = Field(
        0.2, description="Down payment percentage (default: 0.2 for 20%)"
    )
    interest_rate: float = Field(
        0.065, description="Annual mortgage interest rate (default: 0.065 for 6.5%)"
    )
    loan_term_years: int = Field(30, description="Loan term in years (default: 30)")
    property_tax_rate: float = Field(
        0.012, description="Annual property tax rate (default: 0.012 for 1.2%)"
    )
    insurance_annual: Optional[float] = Field(None, description="Annual insurance cost")
    maintenance_rate: float = Field(
        0.01,
        description="Annual maintenance rate as % of property value (default: 0.01 for 1%)",
    )
    vacancy_rate: float = Field(0.05, description="Vacancy rate (default: 0.05 for 5%)")
    management_rate: Optional[float] = Field(
        None, description="Property management rate as % of rent (optional)"
    )


@tool("calculate_roi", args_schema=ROIInput)
def calculate_roi(
    purchase_price: float,
    monthly_rent: Optional[float] = None,
    annual_rent: Optional[float] = None,
    down_payment: float = 0.2,
    interest_rate: float = 0.065,
    loan_term_years: int = 30,
    property_tax_rate: float = 0.012,
    insurance_annual: Optional[float] = None,
    maintenance_rate: float = 0.01,
    vacancy_rate: float = 0.05,
    management_rate: Optional[float] = None,
) -> dict:
    """
    Calculate Return on Investment (ROI) for a rental property.
    Returns cash flow, ROI percentage, cap rate, and other financial metrics.
    """
    try:
        # Calculate annual rent
        if annual_rent:
            gross_annual_rent = annual_rent
        elif monthly_rent:
            gross_annual_rent = monthly_rent * 12
        else:
            return {"error": "Either monthly_rent or annual_rent must be provided"}

        # Loan calculations
        down_payment_amount = purchase_price * down_payment
        loan_amount = purchase_price - down_payment_amount

        # Monthly mortgage payment (P&I)
        monthly_rate = interest_rate / 12
        num_payments = loan_term_years * 12
        if loan_amount > 0:
            monthly_payment = (
                loan_amount
                * (monthly_rate * (1 + monthly_rate) ** num_payments)
                / ((1 + monthly_rate) ** num_payments - 1)
            )
        else:
            monthly_payment = 0

        annual_mortgage = monthly_payment * 12

        # Expenses
        property_tax = purchase_price * property_tax_rate
        insurance = insurance_annual or (
            purchase_price * 0.003
        )  # Default 0.3% if not provided
        maintenance = purchase_price * maintenance_rate
        vacancy_loss = gross_annual_rent * vacancy_rate
        management = (gross_annual_rent * management_rate) if management_rate else 0

        total_expenses = (
            annual_mortgage
            + property_tax
            + insurance
            + maintenance
            + vacancy_loss
            + management
        )

        # Income calculations
        net_annual_income = gross_annual_rent - total_expenses
        monthly_cash_flow = net_annual_income / 12

        # ROI calculations
        cash_on_cash_roi = (
            (net_annual_income / down_payment_amount * 100)
            if down_payment_amount > 0
            else 0
        )
        cap_rate = net_annual_income / purchase_price * 100

        # Break-even analysis
        break_even_rent = total_expenses / 12

        return {
            "purchase_price": purchase_price,
            "down_payment": down_payment_amount,
            "loan_amount": loan_amount,
            "gross_annual_rent": gross_annual_rent,
            "monthly_rent": gross_annual_rent / 12,
            "expenses": {
                "annual_mortgage": annual_mortgage,
                "monthly_mortgage": monthly_payment,
                "property_tax": property_tax,
                "insurance": insurance,
                "maintenance": maintenance,
                "vacancy_loss": vacancy_loss,
                "management": management,
                "total_annual": total_expenses,
                "total_monthly": total_expenses / 12,
            },
            "net_annual_income": net_annual_income,
            "monthly_cash_flow": monthly_cash_flow,
            "cash_on_cash_roi_percent": round(cash_on_cash_roi, 2),
            "cap_rate_percent": round(cap_rate, 2),
            "break_even_monthly_rent": round(break_even_rent, 2),
            "is_positive_cash_flow": net_annual_income > 0,
        }
    except Exception as e:
        logger.error(f"ROI calculation error: {e}")
        return {"error": f"ROI calculation failed: {str(e)}"}


class MortgageInput(BaseModel):
    """Input schema for mortgage calculation."""

    loan_amount: float = Field(..., description="Loan amount")
    interest_rate: float = Field(
        0.065, description="Annual interest rate (default: 0.065 for 6.5%)"
    )
    loan_term_years: int = Field(30, description="Loan term in years (default: 30)")
    down_payment: Optional[float] = Field(
        None, description="Down payment amount (optional, for total price calculation)"
    )


@tool("estimate_mortgage", args_schema=MortgageInput)
def estimate_mortgage(
    loan_amount: float,
    interest_rate: float = 0.065,
    loan_term_years: int = 30,
    down_payment: Optional[float] = None,
) -> dict:
    """
    Calculate monthly mortgage payment and total interest paid.
    """
    try:
        monthly_rate = interest_rate / 12
        num_payments = loan_term_years * 12

        if loan_amount > 0:
            monthly_payment = (
                loan_amount
                * (monthly_rate * (1 + monthly_rate) ** num_payments)
                / ((1 + monthly_rate) ** num_payments - 1)
            )
        else:
            monthly_payment = 0

        total_paid = monthly_payment * num_payments
        total_interest = total_paid - loan_amount

        result = {
            "loan_amount": loan_amount,
            "interest_rate_percent": interest_rate * 100,
            "loan_term_years": loan_term_years,
            "monthly_payment": round(monthly_payment, 2),
            "total_paid": round(total_paid, 2),
            "total_interest": round(total_interest, 2),
            "interest_percentage": round((total_interest / loan_amount * 100), 2)
            if loan_amount > 0
            else 0,
        }

        if down_payment:
            total_price = loan_amount + down_payment
            result["down_payment"] = down_payment
            result["total_price"] = total_price
            result["down_payment_percent"] = round(
                (down_payment / total_price * 100), 2
            )

        return result
    except Exception as e:
        logger.error(f"Mortgage calculation error: {e}")
        return {"error": f"Mortgage calculation failed: {str(e)}"}


class PropertyTaxInput(BaseModel):
    """Input schema for property tax calculation."""

    property_value: float = Field(..., description="Property assessed value")
    tax_rate: Optional[float] = Field(
        None, description="Annual tax rate (if not provided, uses default 1.2%)"
    )
    state: Optional[str] = Field(None, description="State (for state-specific rates)")


@tool("calculate_property_tax", args_schema=PropertyTaxInput)
def calculate_property_tax(
    property_value: float,
    tax_rate: Optional[float] = None,
    state: Optional[str] = None,
) -> dict:
    """
    Calculate annual and monthly property tax.
    Uses default rate of 1.2% if not specified.
    """
    try:
        # Default tax rates by state (simplified)
        state_rates = {
            "CA": 0.012,  # California
            "NY": 0.014,  # New York
            "TX": 0.018,  # Texas
            "FL": 0.011,  # Florida
        }

        if tax_rate:
            rate = tax_rate
        elif state and state.upper() in state_rates:
            rate = state_rates[state.upper()]
        else:
            rate = 0.012  # Default 1.2%

        annual_tax = property_value * rate
        monthly_tax = annual_tax / 12

        return {
            "property_value": property_value,
            "tax_rate_percent": rate * 100,
            "annual_tax": round(annual_tax, 2),
            "monthly_tax": round(monthly_tax, 2),
            "state": state,
        }
    except Exception as e:
        logger.error(f"Property tax calculation error: {e}")
        return {"error": f"Property tax calculation failed: {str(e)}"}


class ComparePropertiesInput(BaseModel):
    """Input schema for comparing multiple properties."""

    properties: str = Field(
        ...,
        description="JSON string with property data: [{'price': 500000, 'rent': 3000, ...}, ...]",
    )


@tool("compare_properties", args_schema=ComparePropertiesInput)
def compare_properties(properties: str) -> dict:
    """
    Compare multiple properties based on financial metrics.
    Input should be a JSON string with property data.
    """
    try:
        import json

        props = json.loads(properties)

        if not isinstance(props, list) or len(props) < 2:
            return {"error": "Please provide at least 2 properties to compare"}

        comparisons = []
        for i, prop in enumerate(props):
            roi_result = calculate_roi.invoke(
                {
                    "purchase_price": prop.get("price", 0),
                    "monthly_rent": prop.get("rent"),
                    "down_payment": prop.get("down_payment", 0.2),
                    "interest_rate": prop.get("interest_rate", 0.065),
                }
            )

            if "error" not in roi_result:
                comparisons.append(
                    {
                        "property_index": i + 1,
                        "price": prop.get("price"),
                        "roi_percent": roi_result.get("cash_on_cash_roi_percent"),
                        "cap_rate_percent": roi_result.get("cap_rate_percent"),
                        "monthly_cash_flow": roi_result.get("monthly_cash_flow"),
                        "is_positive_cash_flow": roi_result.get(
                            "is_positive_cash_flow"
                        ),
                    }
                )

        # Sort by ROI
        comparisons.sort(key=lambda x: x.get("roi_percent", 0), reverse=True)

        return {
            "properties_compared": len(comparisons),
            "rankings": comparisons,
            "best_roi": comparisons[0] if comparisons else None,
        }
    except Exception as e:
        logger.error(f"Property comparison error: {e}")
        return {"error": f"Property comparison failed: {str(e)}"}
