from langchain_core.vectorstores import VectorStore
from pydantic import BaseModel

from ._documents import DocumentMetadata


class SearchResult(BaseModel):
    page_content: str
    metadata: DocumentMetadata

    def to_string(self) -> str:
        return f"""
## Passage from {self.metadata.filename} (Title - {self.metadata.title}):

{self.page_content}
"""


class Searcher:
    def __init__(self, vector_store: VectorStore, max_results: int = 5) -> None:
        self._retriever = vector_store.as_retriever(search_kwargs={"k": max_results})
        self._max_results = max_results

    async def file_search(self, query: str) -> str:
        """Find the relevant passages in the knowledge base.

        Args:
            query: The user query.

        Returns:
            A string containing the relevant passages.
        """
        documents = await self._retriever.ainvoke(query)
        search_results = [
            SearchResult(page_content=doc.page_content, metadata=DocumentMetadata(**doc.metadata)).to_string()
            for doc in documents
        ]

        passages = "\n".join(search_results)

        return "Here are the relevant passages found:\n\n" + passages if passages else "No relevant passages found."
