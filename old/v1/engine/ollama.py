import subprocess
import signal
import requests
import json
import os # Import for file operations
from typing import List, Dict, Generator
import logging

logging.basicConfig(
    level=logging.INFO,  # Use DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Import LangChain components
from langchain_community.document_loaders import TextLoader, PyPDFLoader # Example loaders
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# Define the global variable outside the class
ollama_process = None

class OllamaEngine:
    def __init__(self, model_name='llama3.2:3b', embedding_model_name='nomic-embed-text', context=None, persist_directory='data/embeddings', documents_path='data/documents'):       
        self.model_name = model_name
        self.embedding_model_name = embedding_model_name
        self.persist_directory = persist_directory
        self.documents_path = documents_path
        self.vectorstore = None
        self.embedding_model = OllamaEmbeddings(model=self.embedding_model_name)
        self._initialize_vectorstore()

        self.context = "You're a desi hood rapper with high IQ, extermely cultures and street smart. You usually answer very non-challantly."
        
        # self.context=context

    def launch_model(self):
        """Starts the Ollama model in a subprocess."""
        global ollama_process
        if ollama_process is None:
            logger.info(f"Starting model: {self.model_name}")
            ollama_process = subprocess.Popen(['ollama', 'run', self.model_name])
        else:
            print("Model already running.")
    
    def stop_ollama_model(self):
        """Stops the Ollama model."""
        global ollama_process
        if ollama_process:
            logger.info("Stopping model...")
            ollama_process.send_signal(signal.SIGINT)
            ollama_process.wait()
            ollama_process = None
    
    def ask_ollama(self, prompt):
        """Sends a prompt and returns the full response (non-streaming)."""
        try:
            response = requests.post(
                'http://localhost:11434/api/chat',
                json={
                    'model': self.model_name,
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()['message']['content']
        except Exception as e:
            return f"[Error] {e}"
    
    def stream_ollama_response(self, prompt):
        """Streams the response from Ollama."""
        retrieved_context = ""
        if self.vectorstore:
            logger.info(f"Retrieving relevant documents for prompt: '{prompt}'")
            # Retrieve top K relevant documents
            # You can adjust 'k' based on how much context you want
            try:
                retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
                relevant_docs = retriever.invoke(prompt)
                
                if relevant_docs:
                    retrieved_context = "\n\nRelevant Information:\n" + "\n".join([doc.page_content for doc in relevant_docs])
                    logger.info(f"Retrieved {len(relevant_docs)} document chunks.")
                else:
                    logger.info("No relevant documents found.")
            except Exception as e:
                logger.info(f"Error during document retrieval: {e}")
                retrieved_context = "\n\n[Warning: Document retrieval failed.]"
        
        self.context += f"\n Relevant Context: {retrieved_context}. User: {prompt}"

        # prompt2 = f" You are fusion of Warren Buffet and also a cool guy. You believe in short on point answers wich high accuracy, you are not man of many words, but are man of precise words. You tend to simplify thing while explaining anything. User says: {prompt} "
        # prompt2 = f"You are a hood rapper with low IQ, but otherwise you're a PhD-level expert at music. User says: {prompt}"
        try:
            response = requests.post(
                'http://localhost:11434/api/chat',
                json={
                    'model': self.model_name,
                    'messages': [{'role': 'user', 'content': self.context}],
                    'stream': True,
                    'options': {
                        'temperature': 0.7
                        # 'num_predict': 1024,
                    }
                },
                
                stream=True,
                timeout=60
            )
            
            response.raise_for_status()
            
            self.context += "\nAssistant: "
            for line in response.iter_lines():
                if line:
                    try:
                        # Parse each line as JSON directly (no 'data:' prefix)
                        chunk_obj = json.loads(line.decode('utf-8'))
                        
                        # Check if this chunk contains content
                        if "message" in chunk_obj and "content" in chunk_obj["message"]:
                            content = chunk_obj["message"]["content"]
                            if content:  # Only yield non-empty content
                                self.context += content
                                yield content
                        
                        # Check if the response is done
                        if chunk_obj.get("done", False):
                            break
                            
                    except json.JSONDecodeError as e:
                        logger.info(f"JSON decode error: {e}")
                        continue
                    except Exception as e:
                        logger.info(f"Error processing chunk: {e}")
                        continue
                        
        except Exception as e:
            yield f"[Error] {e}"
        
    
    def _initialize_vectorstore(self):
        """Initializes or loads the ChromaDB vector store."""
        if os.path.exists(self.persist_directory) and os.listdir(self.persist_directory):
            logger.info(f"Loading existing ChromaDB from {self.persist_directory}")
            self.vectorstore = Chroma(persist_directory=self.persist_directory, embedding_function=self.embedding_model)
        else:
            logger.info("No existing ChromaDB found or directory is empty. Creating new vector store...")
            if self.documents_path:
                self._create_and_populate_vectorstore()
            else:
                logger.info("Warning: No documents path provided. RAG will not function without a populated vector store. Call 'ingest_documents' later.")
                # Create an empty vectorstore if no documents are provided initially
                self.vectorstore = Chroma(embedding_function=self.embedding_model, persist_directory=self.persist_directory)
    
    def _create_and_populate_vectorstore(self):
        """Loads, chunks, embeds documents, and populates the vector store."""
        logger.info(f"Loading documents from {self.documents_path}...")
        documents = self._load_documents(self.documents_path)
        if not documents:
            logger.info("No documents loaded. Vector store will be empty.")
            self.vectorstore = Chroma(embedding_function=self.embedding_model, persist_directory=self.persist_directory)
            return

        logger.info(f"Splitting {len(documents)} documents into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} chunks.")

        logger.info("Creating embeddings and storing in ChromaDB. This might take a while...")
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embedding_model,
            persist_directory=self.persist_directory
        )
        self.vectorstore.persist()
        logger.info(f"ChromaDB created and saved to {self.persist_directory}")
    
    def _load_documents(self, documents_path: str) -> List[Document]:
        """Loads documents from a specified path (file or directory)."""
        documents = []
        if os.path.isdir(documents_path):
            for root, _, files in os.walk(documents_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file.endswith(".txt"):
                        loader = TextLoader(file_path)
                        documents.extend(loader.load())
                    elif file.endswith(".pdf"):
                        try:
                            loader = PyPDFLoader(file_path)
                            documents.extend(loader.load())
                        except Exception as e:
                            logger.info(f"Could not load PDF {file_path}: {e}")
        elif os.path.isfile(documents_path):
            if documents_path.endswith(".txt"):
                loader = TextLoader(documents_path)
                documents.extend(loader.load())
            elif documents_path.endswith(".pdf"):
                try:
                    loader = PyPDFLoader(documents_path)
                    documents.extend(loader.load())
                except Exception as e:
                    logger.info(f"Could not load PDF {documents_path}: {e}")
        else:
            logger.info(f"Error: Documents path '{documents_path}' is neither a file nor a directory.")
        return documents

    def ingest_documents(self, documents_path: str):
        """Allows ingesting new documents after initialization."""
        self.documents_path = documents_path
        self._create_and_populate_vectorstore()