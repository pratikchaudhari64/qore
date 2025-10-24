from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
import os

from langchain_community.llms import Ollama
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

DATA_PATH = "../data/documents" # Create this directory and put your PDFs here
VECTOR_DB_PATH = "../data/embeddings"
# LLM_MODEL = "llama3.2:3b"  # Or llama3.2-vision:latest, gemma3:12b-it-qat, etc.
EMBED_MODEL = "nomic-embed-text"

# Ensure directories exist and are writable
os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(VECTOR_DB_PATH, exist_ok=True)

# Verify write permissions
if not os.access(VECTOR_DB_PATH, os.W_OK):
    raise PermissionError(f"No write permission for {VECTOR_DB_PATH}")

def ingest_documents():
    documents = []
    for file in sorted(os.listdir(DATA_PATH)):
        if file.endswith(".pdf"):
            print(os.path.join(DATA_PATH, file))
            loader = PyPDFLoader(os.path.join(DATA_PATH, file))
            documents.extend(loader.load())
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")

    embeddings = OllamaEmbeddings(model="nomic-embed-text") # Or mxbai-embed-large
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=VECTOR_DB_PATH,
    )
    vector_store.persist()
    print(f"Vector store created at {VECTOR_DB_PATH}")