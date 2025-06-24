import os
import logging
import tempfile
import urllib.request
from typing import List, Dict, Any, Optional, Tuple
import pypdf
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config.config import GOOGLE_APPLICATION_CREDENTIALS

logger = logging.getLogger(__name__)

def download_file(url: str, output_path: Optional[str] = None) -> str:
    """
    Download a file from a URL.
    
    Args:
        url: URL to download
        output_path: Path to save the file (optional)
        
    Returns:
        Path to the downloaded file
    """
    if not output_path:
        # Create a temporary file
        fd, output_path = tempfile.mkstemp()
        os.close(fd)
    
    try:
        # Download the file
        urllib.request.urlretrieve(url, output_path)
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise

def process_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        List of text chunks
    """
    try:
        # Open the PDF
        with open(file_path, "rb") as f:
            pdf = pypdf.PdfReader(f)
            
            # Extract text from each page
            chunks = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text.strip():
                    chunks.append({
                        "text": text.strip(),
                        "page": i + 1
                    })
            
            return chunks
            
    except Exception as e:
        logger.error(f"Failed to process PDF: {e}")
        raise
    finally:
        # Clean up temporary file if it's a temp file
        if file_path.startswith(tempfile.gettempdir()):
            try:
                os.unlink(file_path)
            except OSError:
                pass

def process_google_sheet(sheet_url: str) -> List[Dict[str, Any]]:
    """
    Extract text from a Google Sheet.
    
    Args:
        sheet_url: URL to Google Sheet
        
    Returns:
        List of text chunks (one per sheet)
    """
    try:
        # Authenticate with Google Sheets API
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            GOOGLE_APPLICATION_CREDENTIALS, scope
        )
        client = gspread.authorize(credentials)
        
        # Open the sheet
        sheet = client.open_by_url(sheet_url)
        
        # Extract text from each worksheet
        chunks = []
        for i, worksheet in enumerate(sheet.worksheets()):
            # Get all values
            values = worksheet.get_all_values()
            
            # Convert to text
            text = "\n".join(["\t".join(row) for row in values])
            
            if text.strip():
                chunks.append({
                    "text": text.strip(),
                    "sheet_name": worksheet.title,
                    "sheet_index": i
                })
        
        return chunks
        
    except Exception as e:
        logger.error(f"Failed to process Google Sheet: {e}")
        raise

def process_document(url: str, doc_type: str) -> List[Dict[str, Any]]:
    """
    Process a document from a URL.
    
    Args:
        url: URL to document
        doc_type: Type of document (pdf, sheet)
        
    Returns:
        List of text chunks
    """
    logger.info(f"Processing {doc_type} document from {url}")
    
    if doc_type.lower() == "pdf":
        # Download and process PDF
        file_path = download_file(url)
        chunks = process_pdf(file_path)
        
    elif doc_type.lower() == "sheet":
        # Process Google Sheet
        chunks = process_google_sheet(url)
        
    else:
        raise ValueError(f"Unsupported document type: {doc_type}")
    
    logger.info(f"Extracted {len(chunks)} chunks from {url}")
    
    return chunks 