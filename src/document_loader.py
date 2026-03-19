import os
import pandas as pd
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader
)

def load_document(file_path: str) -> str:
    """
    Loads a document using LangChain loaders and returns its textual content.
    Supports PDF, DOCX, TXT, CSV, and Excel spreadsheets.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    ext = os.path.splitext(file_path)[1].lower()
    docs: List[Document] = []

    try:
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
            docs = loader.load()
        elif ext in [".docx", ".doc"]:
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
        elif ext == ".txt":
            loader = TextLoader(file_path, encoding='utf-8')
            docs = loader.load()
        elif ext == ".csv":
            loader = CSVLoader(file_path, encoding='utf-8')
            docs = loader.load()
        elif ext in [".xls", ".xlsx"]:
            # Load excel using pandas and convert to a text format
            df = pd.read_excel(file_path)
            content = df.to_csv(index=False)
            docs = [Document(page_content=content, metadata={"source": file_path})]
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
            
        full_text = "\n\n".join([doc.page_content for doc in docs])
        return full_text

    except Exception as e:
        print(f"Error loading document {file_path}: {e}")
        raise
