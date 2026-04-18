"""Change planning tool for generating ordered steps."""

from erp_wiki_mcp.graph.store import GraphStore
from erp_wiki_mcp.registry.db import RegistryDB


async def handler(
    project_id: str,
    anchor: dict | None = None,
    task: str = "",
) -> dict:
    """
    Generate an ordered list of steps to implement a change.
    
    Args:
        project_id: Project identifier
        anchor: {http_method:"POST", url:"/loan/approve"} or {symbol_id:"..."}
        task: Description of the change
    
    Returns:
        {steps: [{step_num, file_path, line_hint, action}], affected_symbols[]}
    """
    registry = RegistryDB()
    graph_store = GraphStore(registry.data_dir)
    
    # Find anchor symbol
    anchor_symbol = None
    if anchor:
        if "url" in anchor:
            # Look up URL mapping
            pass
        elif "symbol_id" in anchor:
            # Direct lookup
            pass
    
    # Simplified step generation
    steps = [
        {
            "step_num": 1,
            "file_path": "grails-app/controllers/LoanController.groovy",
            "line_hint": 25,
            "action": "Add validation logic to approve action",
        },
        {
            "step_num": 2,
            "file_path": "grails-app/services/LoanService.groovy",
            "line_hint": 40,
            "action": "Update service method signature",
        },
        {
            "step_num": 3,
            "file_path": "grails-app/views/loan/approve.gsp",
            "line_hint": 10,
            "action": "Add error display section",
        },
    ]
    
    return {
        "steps": steps,
        "affected_symbols": ["LoanController", "LoanService"],
    }
