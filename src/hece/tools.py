# HECE/src/hece/tools.py
import arxiv

class ScientificToolbox:
    """
    A collection of external tools to fetch real-world data for RAG.
    """
    
    @staticmethod
    def search_arxiv(query: str, max_results: int = 2) -> str:
        """
        Searches the ArXiv database for scientific papers matching the query.
        Returns a formatted string containing the titles and summaries.
        """
        try:
            # Construct a basic client
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            results_text = "REAL SCIENTIFIC LITERATURE RETRIEVED:\n"
            for paper in client.results(search):
                results_text += f"\n- Title: {paper.title}\n"
                # Limiting summary length to keep prompt size manageable
                results_text += f"  Summary: {paper.summary[:300]}...\n"
                
            return results_text
        except Exception as e:
            return f"Failed to retrieve external data: {str(e)}"