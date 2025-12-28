import sys
from pypdf import PdfReader

def inspect_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        print(f"Number of pages: {len(reader.pages)}")
        
        for i, page in enumerate(reader.pages):
            print(f"\n--- Page {i+1} ---")
            text = page.extract_text()
            print(text)
            
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_pdf.py <pdf_path>")
        sys.exit(1)
    
    inspect_pdf(sys.argv[1])
