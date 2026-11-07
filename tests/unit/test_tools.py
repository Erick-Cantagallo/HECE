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

@patch('hece.tools.time.sleep')
@patch('hece.tools.arxiv.Client')
def test_search_arxiv_failure(mock_client, mock_sleep):
    # Setup mock to simulate a connection or API error
    mock_client.side_effect = Exception("Simulated API Error")
    
    # Execute
    output = ScientificToolbox.search_arxiv("black holes")
    
    # Assertions
    assert output == ""
    assert "Simulated API Error" in ScientificToolbox.last_error  # the failure stays distinguishable
    assert mock_sleep.call_count == 2                             # it retried before giving up

@patch('hece.tools.arxiv.Search')
@patch('hece.tools.arxiv.Client')
def test_search_arxiv_relevance_filter_and_ids(mock_client, mock_search):
    def paper(title, summary, entry_id):
        m = MagicMock()
        m.title, m.summary, m.entry_id = title, summary, entry_id
        return m
    inst = MagicMock()
    mock_client.return_value = inst
    inst.results.return_value = [
        paper("The Higgs Portal and Cosmology", "dark matter and baryon asymmetry", "http://arxiv.org/abs/1412.4743v2"),
        paper("A portal gun concept", "we discuss a portal gun device", "http://arxiv.org/abs/2001.00001v1"),
    ]

    out = ScientificToolbox.search_arxiv("portal gun", max_results=2, keywords=["portal", "gun"])

    assert "Higgs" not in out              # only 1 of 2 keywords matched -> rejected
    assert "A portal gun concept" in out
    assert "ID: 2001.00001" in out         # version suffix stripped
    assert "- [1] Title: A portal gun concept" in out   # numbered so the LLM can cite [n]

@patch('hece.tools.arxiv.Search')
@patch('hece.tools.arxiv.Client')
def test_search_arxiv_nothing_relevant_returns_empty(mock_client, mock_search):
    m = MagicMock()
    m.title, m.summary, m.entry_id = "Unrelated", "nothing here", "http://arxiv.org/abs/1v1"
    inst = MagicMock(); inst.results.return_value = [m]; mock_client.return_value = inst
    assert ScientificToolbox.search_arxiv("portal gun", keywords=["portal", "gun"]) == ""


@patch('hece.tools.time.sleep')
@patch('hece.tools.arxiv.Search')
@patch('hece.tools.arxiv.Client')
def test_search_arxiv_recovers_after_transient_503(mock_client, mock_search, mock_sleep):
    paper = MagicMock()
    paper.title, paper.summary, paper.entry_id = "Desalination energy", "seawater desalination energy", "http://arxiv.org/abs/2001.00002v1"
    ok = MagicMock(); ok.results.return_value = [paper]
    mock_client.side_effect = [Exception("HTTP 503"), ok]

    out = ScientificToolbox.search_arxiv("energy desalination", keywords=["energy", "desalination"])

    assert "Desalination energy" in out and ScientificToolbox.last_error is None
    assert mock_sleep.call_count == 1


@patch('hece.tools.time.sleep')
@patch('hece.tools.arxiv.Client')
def test_rate_limit_429_is_not_retried(mock_client, mock_sleep):
    mock_client.side_effect = Exception("Page request resulted in HTTP 429")
    assert ScientificToolbox.search_arxiv("portal gun") == ""
    assert mock_sleep.call_count == 0 and "429" in ScientificToolbox.last_error
    assert mock_client.call_count == 1


@patch('hece.tools.time.sleep')
@patch('hece.tools.arxiv.Search')
@patch('hece.tools.arxiv.Client')
def test_cache_spares_the_api_and_expires(mock_client, mock_search, mock_sleep, tmp_path):
    paper = MagicMock()
    paper.title, paper.summary, paper.entry_id = "Cached paper", "about cached things", "http://arxiv.org/abs/2001.00009v1"
    ok = MagicMock(); ok.results.return_value = [paper]
    mock_client.return_value = ok
    old_dir = ScientificToolbox.cache_dir
    ScientificToolbox.cache_dir = str(tmp_path)
    try:
        first = ScientificToolbox.search_arxiv("cached things", use_cache=True)
        mock_client.side_effect = Exception("HTTP 503")           # the API would fail now...
        second = ScientificToolbox.search_arxiv("cached things", use_cache=True)
        assert first == second and "Cached paper" in second and ScientificToolbox.last_error is None
        assert ScientificToolbox.search_arxiv("cached things") == ""      # ...and without the cache it does
        ScientificToolbox.CACHE_TTL_SECONDS = -1                          # expired entries are ignored
        assert ScientificToolbox.search_arxiv("cached things", use_cache=True) == ""
    finally:
        ScientificToolbox.cache_dir = old_dir
        ScientificToolbox.CACHE_TTL_SECONDS = 7 * 24 * 3600
