"""MCP interface for the synthetic enterprise AI portfolio analytics demo."""

from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from analytics import available_periods, compare_periods, portfolio_summary, program_detail


server = MCPServer(
    "Synthetic Portfolio Analytics",
    version="1.0.0",
    instructions="Read-only analytics over a small synthetic enterprise AI portfolio dataset. All value figures are illustrative.",
)


READ_ONLY_HINT = ToolAnnotations(read_only_hint=True, open_world_hint=False)


@server.tool(annotations=READ_ONLY_HINT)
def list_available_data() -> dict[str, Any]:
    """List periods and synthetic AI program IDs available for analysis."""
    return available_periods()


@server.tool(annotations=READ_ONLY_HINT)
def get_portfolio_summary(period: str) -> dict[str, Any]:
    """Get portfolio spend, modeled value, adoption, and risk totals for YYYY-MM."""
    try:
        return portfolio_summary(period)
    except ValueError as exc:
        return {"error": str(exc)}


@server.tool(annotations=READ_ONLY_HINT)
def compare_portfolio_periods(from_period: str, to_period: str) -> dict[str, Any]:
    """Compare two available YYYY-MM periods using absolute metric changes."""
    try:
        return compare_periods(from_period, to_period)
    except ValueError as exc:
        return {"error": str(exc)}


@server.tool(annotations=READ_ONLY_HINT)
def get_program_detail(program_id: str) -> dict[str, Any]:
    """Get monthly observations for a program ID returned by list_available_data."""
    try:
        return program_detail(program_id)
    except ValueError as exc:
        return {"error": str(exc)}


@server.resource("analytics://portfolio/data-dictionary")
def data_dictionary() -> str:
    """Explain the fields and calculation boundaries in the synthetic dataset."""
    return (
        "Dataset fields: spend_usd is invented monthly program spend; modeled_value_usd is an illustrative "
        "benefit estimate; modeled_net_value_usd equals modeled_value_usd minus spend_usd; weighted_adoption_pct "
        "equals total active_users divided by total eligible_users; open_risks is a synthetic count. "
        "None of these figures are measured company outcomes."
    )


@server.prompt()
def monthly_portfolio_review(period: str) -> str:
    """Prepare a human-led review using the portfolio summary tool for a month."""
    return (
        f"Review the synthetic portfolio for {period}. Call get_portfolio_summary for that period. "
        "Separate spend, modeled value, adoption, and open risks. State that the dataset is synthetic, "
        "avoid causal claims, and identify questions a human owner should validate."
    )


if __name__ == "__main__":
    server.run(transport="stdio")
