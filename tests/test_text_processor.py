import pytest
from src.processing.text_processor import clean_text, chunk_text

def test_clean_text():
    """Test the clean_text function."""
    # Test basic cleaning
    text = "  Hello,  world!  "
    assert clean_text(text) == "Hello, world!"
    
    # Test removing special characters
    text = "Hello\n\tworld! This is a test."
    assert clean_text(text) == "Hello world! This is a test."
    
    # Test preserving important punctuation
    text = "Hello, world! This is a test. Is it working?"
    assert clean_text(text) == "Hello, world! This is a test. Is it working?"

def test_chunk_text():
    """Test the chunk_text function."""
    # Test basic chunking
    text = "This is the first sentence. This is the second sentence. This is the third sentence."
    chunks = chunk_text(text, chunk_size=10, chunk_overlap=2)
    
    # Should split into at least 2 chunks
    assert len(chunks) >= 2
    
    # First chunk should contain the first sentence
    assert "first sentence" in chunks[0]
    
    # Check for overlap
    for i in range(1, len(chunks)):
        # Some content from the previous chunk should be in this chunk
        assert any(word in chunks[i-1] and word in chunks[i] 
                  for word in ["This", "is", "the", "sentence"])
    
    # Test with empty text
    assert chunk_text("") == []
    
    # Test with text smaller than chunk size
    short_text = "Short text."
    assert chunk_text(short_text, chunk_size=100) == [short_text] 