from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
import os

def load_pdf_documents(file_path, chunk_size=1000, chunk_overlap=100):
    """
    Loads a PDF, splits it into pages, and then chunks the pages.
    Based on the logic from cell 8.
    
    Args:
        file_path (str): The path to the PDF file (e.g., "data/raw/legal_docs.pdf")
        chunk_size (int): The size of each text chunk.
        chunk_overlap (int): The overlap between chunks.
        
    Returns:
        list: A list of Document objects (chunks).
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return []
        
    print(f"Loading PDF from {file_path}...")
    loader = PyPDFLoader(file_path)
    pages = loader.load_and_split()
    
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    docs = text_splitter.split_documents(pages)
    print(f"Created {len(docs)} document chunks.")
    return docs

def load_jsonl_data(file_path):
    """
    Loads a JSONL file containing questions and answers.
    Based on the logic from cell 10.
    
    Args:
        file_path (str): The path to the JSONL file (e.g., "data/raw/train.jsonl")
        
    Returns:
        list: A list of dictionaries, where each dict has 'question' and 'answer'.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return []

    print(f"Loading JSONL data from {file_path}...")
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    print(f"Loaded {len(data)} Q&A pairs.")
    return data

if __name__ == '__main__':
    # This block allows you to test this file directly
    # Run: python src/data_loader.py
    
    # NOTE: Create a dummy file at 'data/raw/dummy.pdf' or use your real file
    # for this test to work. For now, it will likely print an error.
    print("Testing PDF loader...")
    pdf_docs = load_pdf_documents("data/raw/legal_docs.pdf")
    if pdf_docs:
        print(f"First chunk: {pdf_docs[0].page_content[:100]}...")

    # NOTE: Create a dummy file at 'data/raw/dummy.jsonl' or use your real file.
    print("\nTesting JSONL loader...")
    json_data = load_jsonl_data("data/raw/train.jsonl")
    if json_data:
        print(f"First Q&A pair: {json_data[0]}")
    
    print("data_loader.py is ready.")