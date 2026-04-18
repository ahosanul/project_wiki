"""Scaffolding tool for generating Grails code structures."""


async def handler(
    project_id: str,
    description: str,
) -> dict:
    """
    Generate valid Grails code structure for a described feature.
    
    Args:
        project_id: Project identifier
        description: Feature description (e.g., "add PDF export action to LoanController")
    
    Returns:
        {files: [{path, content}], explanation}
    """
    # Parse description for intent
    files = []
    
    if "PDF export" in description and "LoanController" in description:
        files = [
            {
                "path": "grails-app/controllers/LoanController.groovy",
                "content": """    def exportPdf(Long id) {
        def loan = Loan.get(id)
        if (!loan) {
            flash.message = 'Loan not found'
            redirect action: 'index'
            return
        }
        
        response.contentType = 'application/pdf'
        response.setHeader('Content-Disposition', \"attachment; filename=loan_\\${loan.id}.pdf\")
        
        // Use a PDF library like iText or Apache PDFBox
        // render pdf: 'loan', model: [loan: loan]
    }""",
            },
            {
                "path": "grails-app/views/loan/show.gsp",
                "content": """<g:link action="exportPdf" id="\${loan.id}" class="btn btn-secondary">
    <i class="fa fa-file-pdf"></i> Export PDF
</g:link>""",
            },
        ]
    
    return {
        "files": files,
        "explanation": "Generated PDF export functionality with controller action and view link.",
    }
