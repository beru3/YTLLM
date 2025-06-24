import pytest
import uuid
from unittest.mock import patch, MagicMock
from src.retrieval.vector_store import add_chunks_to_vector_store, search_vector_store, delete_chunks

# Sample test data
sample_chunks = [
    {
        "vector_id": str(uuid.uuid4()),
        "text": "This is a sample text about marketing strategies.",
        "embedding": [0.1, 0.2, 0.3],
        "video_id": "video123",
        "chunk_index": 0,
        "start_time": 10.5,
        "end_time": 15.2
    },
    {
        "vector_id": str(uuid.uuid4()),
        "text": "SEO is important for digital marketing.",
        "embedding": [0.2, 0.3, 0.4],
        "video_id": "video123",
        "chunk_index": 1,
        "start_time": 15.2,
        "end_time": 20.0
    },
    {
        "vector_id": str(uuid.uuid4()),
        "text": "Content marketing helps build brand awareness.",
        "embedding": [0.3, 0.4, 0.5],
        "document_id": 1,
        "chunk_index": 0,
        "page": 1
    }
]

@pytest.fixture
def mock_chroma_collection():
    """Create a mock ChromaDB collection."""
    collection = MagicMock()
    collection.add = MagicMock()
    collection.query = MagicMock(return_value={
        "documents": [["SEO is important for digital marketing."]],
        "metadatas": [[{"source_type": "video", "source_id": "video123", "start_time": 15.2, "end_time": 20.0}]],
        "distances": [[0.2]]
    })
    collection.delete = MagicMock()
    return collection

@pytest.fixture
def mock_chroma_client(mock_chroma_collection):
    """Create a mock ChromaDB client."""
    client = MagicMock()
    client.get_collection = MagicMock(return_value=mock_chroma_collection)
    return client

@patch("src.retrieval.vector_store.get_chroma_client")
@patch("src.retrieval.vector_store.get_or_create_collection")
def test_add_chunks_to_vector_store(mock_get_collection, mock_get_client, mock_chroma_client, mock_chroma_collection):
    """Test adding chunks to the vector store."""
    mock_get_client.return_value = mock_chroma_client
    mock_get_collection.return_value = mock_chroma_collection
    
    # Call the function
    add_chunks_to_vector_store(sample_chunks)
    
    # Check that the collection.add method was called correctly
    mock_chroma_collection.add.assert_called_once()
    
    # Extract the call arguments
    call_args = mock_chroma_collection.add.call_args[1]
    
    # Check that the IDs match
    assert call_args["ids"] == [chunk["vector_id"] for chunk in sample_chunks]
    
    # Check that the texts match
    assert call_args["documents"] == [chunk["text"] for chunk in sample_chunks]
    
    # Check that the embeddings match
    assert call_args["embeddings"] == [chunk["embedding"] for chunk in sample_chunks]

@patch("src.retrieval.vector_store.get_chroma_client")
@patch("src.retrieval.vector_store.get_or_create_collection")
def test_search_vector_store(mock_get_collection, mock_get_client, mock_chroma_client, mock_chroma_collection):
    """Test searching the vector store."""
    mock_get_client.return_value = mock_chroma_client
    mock_get_collection.return_value = mock_chroma_collection
    
    # Call the function
    results = search_vector_store("digital marketing")
    
    # Check that the collection.query method was called correctly
    mock_chroma_collection.query.assert_called_once()
    
    # Check that we got results
    assert len(results) == 1
    assert results[0]["text"] == "SEO is important for digital marketing."
    assert results[0]["source_type"] == "video"
    assert results[0]["source_id"] == "video123"
    assert results[0]["score"] == pytest.approx(0.8)  # 1.0 - 0.2

@patch("src.retrieval.vector_store.get_chroma_client")
@patch("src.retrieval.vector_store.get_or_create_collection")
def test_delete_chunks(mock_get_collection, mock_get_client, mock_chroma_client, mock_chroma_collection):
    """Test deleting chunks from the vector store."""
    mock_get_client.return_value = mock_chroma_client
    mock_get_collection.return_value = mock_chroma_collection
    
    # Vector IDs to delete
    vector_ids = [chunk["vector_id"] for chunk in sample_chunks[:2]]
    
    # Call the function
    delete_chunks(vector_ids)
    
    # Check that the collection.delete method was called correctly
    mock_chroma_collection.delete.assert_called_once_with(ids=vector_ids) 