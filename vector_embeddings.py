from langchain_community.document_loaders import UnstructuredMarkdownLoader, CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Base directory of company data
base_dir = "FinSolve_AI/Company_Data"

all_docs = []

# Loop through all files in the directory structure
for root, dirs, files in os.walk(base_dir):
    for file in files:
        file_path = os.path.join(root, file)
        department = os.path.basename(root)
        
        if file.endswith(".md"):
            loader = UnstructuredMarkdownLoader(file_path)
            docs = loader.load()

            # Add metadata
            for doc in docs:
                doc.metadata["department"] = department
                doc.metadata["source"] = file  

            all_docs.extend(docs)

        # Load CSV files
        elif file.endswith(".csv"):
            loader = CSVLoader(file_path=file_path)
            docs = loader.load()

            for doc in docs:
                doc.metadata["department"] = department
                doc.metadata["source"] = file  

            all_docs.extend(docs)

# Text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", " ", ""]
)

# Split the documents
split_docs = text_splitter.split_documents(all_docs)

# Embedding model
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

# Create and persist Chroma vectorstore
chroma_db = Chroma.from_documents(
    documents=split_docs,
    embedding=embeddings,
    persist_directory="Chroma_Vector_Database"  # Vector store directory
)

chroma_db.persist()

print("Chroma vectorstore created and saved.")
