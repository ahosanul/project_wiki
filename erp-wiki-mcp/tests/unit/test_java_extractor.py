"""Unit tests for Java extractor."""

import json
from pathlib import Path

import pytest

from erp_wiki_mcp.extractors.java_extractor import extract_java
from erp_wiki_mcp.parsers.base import ParseResult


@pytest.fixture
def sample_java_file(tmp_path: Path) -> Path:
    """Create a sample Java file for testing."""
    content = """
package com.acme.loan;

import org.springframework.stereotype.Service;
import java.math.BigDecimal;

/**
 * Loan service for managing loan approvals.
 */
@Service
public class LoanService {
    
    @Autowired
    private LoanRepository loanRepository;
    
    /**
     * Approve a loan application.
     * @param loanId the loan ID
     * @param amount the loan amount
     * @return approval status
     */
    public boolean approveLoan(long loanId, BigDecimal amount) {
        Loan loan = loanRepository.findById(loanId);
        if (loan != null && amount.compareTo(BigDecimal.ZERO) > 0) {
            loan.setStatus("APPROVED");
            loanRepository.save(loan);
            return true;
        }
        return false;
    }
    
    public void rejectLoan(Long loanId) {
        Loan loan = loanRepository.get(loanId);
        loan.setStatus("REJECTED");
    }
}
"""
    java_file = tmp_path / "LoanService.java"
    java_file.write_text(content)
    return java_file


def test_extract_java_basic(sample_java_file: Path):
    """Test basic Java extraction."""
    source = sample_java_file.read_bytes()
    parse_result = ParseResult(
        file_path=str(sample_java_file),
        language="java",
        artifact_type="plain_java",
        status="ok",
        error=None,
        tree=None,
        raw_source=source,
    )
    
    result = extract_java(parse_result, "test_project", "test_run")
    
    # Should extract the class
    assert len(result.nodes) >= 1
    class_nodes = [n for n in result.nodes if n.kind == "class"]
    assert len(class_nodes) == 1
    
    cls = class_nodes[0]
    assert cls.name == "LoanService"
    assert cls.fqn == "com.acme.loan.LoanService"
    assert cls.properties.get("is_abstract") is False
    
    # Should extract methods
    method_nodes = [n for n in result.nodes if n.kind == "method"]
    assert len(method_nodes) >= 2
    
    # Check approveLoan method
    approve_method = next((m for m in method_nodes if m.name == "approveLoan"), None)
    assert approve_method is not None
    assert "loanId" in approve_method.properties.get("param_types", [])
    assert approve_method.docstring is not None
    assert "Approve a loan" in approve_method.docstring


def test_extract_java_fields(sample_java_file: Path):
    """Test field extraction with DI annotations."""
    source = sample_java_file.read_bytes()
    parse_result = ParseResult(
        file_path=str(sample_java_file),
        language="java",
        artifact_type="plain_java",
        status="ok",
        error=None,
        tree=None,
        raw_source=source,
    )
    
    result = extract_java(parse_result, "test_project", "test_run")
    
    # Should extract fields
    field_nodes = [n for n in result.nodes if n.kind == "field"]
    assert len(field_nodes) >= 1
    
    repo_field = next((f for f in field_nodes if "loanRepository" in f.name), None)
    assert repo_field is not None
    assert repo_field.properties.get("is_di_candidate") is True
    assert repo_field.properties.get("injection_point") is True


def test_extract_java_edges(sample_java_file: Path):
    """Test edge extraction."""
    source = sample_java_file.read_bytes()
    parse_result = ParseResult(
        file_path=str(sample_java_file),
        language="java",
        artifact_type="plain_java",
        status="ok",
        error=None,
        tree=None,
        raw_source=source,
    )
    
    result = extract_java(parse_result, "test_project", "test_run")
    
    # Should have DECLARES edges for methods and fields
    declares_edges = [e for e in result.raw_edges if e.type == "DECLARES"]
    assert len(declares_edges) >= 3  # At least 2 methods + 1 field
    
    # Should have INJECTS edge for @Autowired field
    injects_edges = [e for e in result.raw_edges if e.type == "INJECTS"]
    assert len(injects_edges) >= 1
    
    # Should have CALLS edges for method invocations
    calls_edges = [e for e in result.raw_edges if e.type == "CALLS"]
    assert len(calls_edges) >= 2  # findById, save, get, etc.
