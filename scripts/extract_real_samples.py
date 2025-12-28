import os
import sys
import pypdf
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

SAMPLE_FILES = {
    "Type_A_Annual": "analysis/sample_pdfs/A_10072764.pdf",
    "Type_D_Campaign": "analysis/sample_pdfs/D_40004863.pdf",
    "Type_W_Withdrawal": "analysis/sample_pdfs/W_8025.pdf",
    "Type_X_Extension": "analysis/sample_pdfs/X_30025539.pdf",
    "Type_T_Termination": "analysis/sample_pdfs/T_10063342.pdf",
    "Type_P_PTR": "analysis/sample_pdfs/P_20026590_real.pdf"
}

OUTPUT_DIR = "analysis/sample_text"

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file using pypdf."""
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        return None

def main():
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    project_root = os.getcwd()
    
    for type_name, rel_path in SAMPLE_FILES.items():
        abs_path = os.path.join(project_root, rel_path)
        if not os.path.exists(abs_path):
            logger.warning(f"Sample file not found: {abs_path}")
            continue
            
        logger.info(f"Extracting text from {type_name} ({rel_path})...")
        text = extract_text_from_pdf(abs_path)
        
        if text:
            output_path = os.path.join(OUTPUT_DIR, f"{type_name}.txt")
            with open(output_path, "w") as f:
                f.write(text)
            logger.info(f"Saved extracted text to {output_path}")
            
            # Print first 500 chars to verify
            print(f"\n--- {type_name} Preview ---\n{text[:500]}\n---------------------------\n")

if __name__ == "__main__":
    main()
