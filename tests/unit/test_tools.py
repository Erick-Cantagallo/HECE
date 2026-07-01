# HECE/tests/unit/test_tools.py
import pytest
from unittest.mock import MagicMock, patch
from hece.tools import ScientificToolbox

@patch('hece.tools.arxiv.Client')
@patch('hece.tools.arxiv.Search')
def test_search_arxiv_success(mock_search, mock_client):
    # Setup mock data to simulate a successful ArXiv API response
    mock_client_instance = MagicMock()
    mock_client.return_value = mock_client_instance
    
    mock_result = MagicMock()
    mock_result.title = "Mocked Quantum Paper"
    mock_result.summary = "A mocked summary about quantum gravity."
    mock_client_instance.results.return_value = [mock_result]
    
    # Execute the toolbox method
    output = ScientificToolbox.search_arxiv("quantum gravity", max_results=1)
    
    # Assertions
    assert "REAL SCIENTIFIC LITERATURE RETRIEVED:" in output
    assert "Mocked Quantum Paper" in output
    assert "A mocked summary" in output

@patch('hece.tools.arxiv.Client')
def test_search_arxiv_failure(mock_client):
    # Setup mock to simulate a connection or API error
    mock_client.side_effect = Exception("Simulated API Error")
    
    # Execute
    output = ScientificToolbox.search_arxiv("black holes")
    
    # Assertions
    assert "Failed to retrieve external data" in output
    assert "Simulated API Error" in output