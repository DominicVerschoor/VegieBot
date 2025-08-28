import os
import sys
from pathlib import Path
from PyPDF2 import PdfMerger
import argparse

def combine_pdfs(input_folder, output_file):
    """
    Combine all PDF files in a folder into a single PDF.
    
    Args:
        input_folder (str): Path to folder containing PDF files
        output_file (str): Path for the output combined PDF file
    """
    pdf_merger = PdfMerger()
    pdf_files = []
    
    # Get all PDF files from the folder
    input_path = Path(input_folder)
    if not input_path.exists():
        print(f"Error: Input folder '{input_folder}' does not exist.")
        return False
    
    # Find all PDF files and sort them
    for file_path in input_path.glob("*.pdf"):
        pdf_files.append(file_path)
    
    if not pdf_files:
        print(f"No PDF files found in '{input_folder}'")
        return False
    
    # Sort files alphabetically
    pdf_files.sort()
    
    print(f"Found {len(pdf_files)} PDF files:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    
    try:
        # Merge all PDFs
        for pdf_file in pdf_files:
            print(f"Adding {pdf_file.name}...")
            pdf_merger.append(str(pdf_file))
        
        # Write the combined PDF
        with open(output_file, 'wb') as output:
            pdf_merger.write(output)
        
        pdf_merger.close()
        print(f"\nSuccessfully combined {len(pdf_files)} PDFs into '{output_file}'")
        return True
        
    except Exception as e:
        print(f"Error combining PDFs: {e}")
        pdf_merger.close()
        return False

def main():
    parser = argparse.ArgumentParser(description="Combine PDF files from a folder into a single PDF")
    parser.add_argument("input_folder", nargs='?', default="pdfs", help="Path to folder containing PDF files (default: pdfs)")
    parser.add_argument("-o", "--output", default="outputpdf/combined.pdf", 
                       help="Output filename (default: outputpdf/combined.pdf)")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    success = combine_pdfs(args.input_folder, args.output)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()