from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.html_bs import BSHTMLLoader
from langchain_community.vectorstores.lancedb import LanceDB as LanceDBVectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_openai import (
    AzureOpenAIEmbeddings,
    OpenAIEmbeddings,
)
from langchain_text_splitters import TokenTextSplitter

from backend._config import EmbedderSettings, EmbeddingModelType, Settings

from ._documents import DOCUMENTS_BY_FILENAME, as_dicts


def make_embedding_instance(embedder_settings: EmbedderSettings) -> Embeddings:
    underlying_embedding: Embeddings

    embedding_type = embedder_settings.provider_type
    embedding_model = embedder_settings.model_name
    embedding_api_key = embedder_settings.api_key
    embedding_api_version = embedder_settings.api_version
    embedding_api_endpoint = embedder_settings.api_endpoint
    embedding_api_deployment = embedder_settings.api_deployment

    if embedding_type == EmbeddingModelType.openai:
        underlying_embedding = OpenAIEmbeddings(
            model=embedding_model,
            api_key=embedding_api_key,
        )
    elif embedding_type == EmbeddingModelType.azure_openai:
        underlying_embedding = AzureOpenAIEmbeddings(
            model=embedding_model,
            api_version=embedding_api_version,
            api_key=embedding_api_key,
            azure_endpoint=embedding_api_endpoint,
            azure_deployment=embedding_api_deployment,
        )
    elif embedding_type == EmbeddingModelType.ollama:
        underlying_embedding = OllamaEmbeddings(
            model=embedding_model,
            base_url=embedding_api_endpoint,
        )
    else:
        raise ValueError(
            f"Unsupported embedding model type: {embedding_type}. Supported types are: openai, azure_openai, ollama."
        )

    return underlying_embedding


def make_vector_store(settings: Settings) -> VectorStore:
    vector_store = LanceDBVectorStore(
        uri=str(settings.DATA_DIR / "knowledge" / "vectorstore"),
        embedding=make_embedding_instance(embedder_settings=settings.embedder),
        table_name="ka",
        mode="append",
    )

    if settings.DATA_DIR.joinpath("knowledge", "vectorstore", "ka.lance").exists():
        print("Vector store already exists. Skipping document ingestion.")
        return vector_store

    text_splitter = TokenTextSplitter(
        chunk_size=256,
        chunk_overlap=50,
    )

    for filename, document_metadata in DOCUMENTS_BY_FILENAME.items():
        print("Loading document:", filename)
        file_path = settings.DATA_DIR / "knowledge" / filename

        documents: list[Document] = []

        if filename.endswith(".pdf"):
            pdf_loader = PyPDFLoader(file_path=file_path)
            documents = pdf_loader.load_and_split(text_splitter=text_splitter)

        elif filename.endswith(".html"):
            html_loader = BSHTMLLoader(file_path=file_path)
            documents = html_loader.load_and_split(text_splitter=text_splitter)

        print("Adding documents to vector store...")
        # vector_store.add_documents(documents)

        print(document_metadata)

        vector_store.add_texts(
            texts=[doc.page_content for doc in documents],
            metadatas=as_dicts([document_metadata for _ in documents]),
        )

    return vector_store
