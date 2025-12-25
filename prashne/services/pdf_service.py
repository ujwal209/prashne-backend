import pypdf
import io

def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extracts raw text from a PDF byte stream.
    """
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        if not text.strip():
            raise ValueError("Empty PDF or OCR required")
            
        return text
    except Exception as e:
        raise ValueError(f"PDF extraction failed: {str(e)}")
