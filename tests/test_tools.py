from agent.tools import ReadPdfInput, SearchWebInput, read_pdf


def test_pdf_argument_rejects_path_traversal():
    try:
        ReadPdfInput(file_name="../secret.pdf")
    except ValueError:
        return
    raise AssertionError("path traversal should be rejected")


def test_search_argument_has_limits():
    value = SearchWebInput(query="MCP protocol")
    assert value.max_results == 5


def test_missing_pdf_reports_available_sources():
    result = read_pdf("missing.pdf", "method")
    assert result["ok"] is False
    assert "available" in result
