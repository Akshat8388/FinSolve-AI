# Database
import sqlite3
# Fast API
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse,StreamingResponse
from pydantic import BaseModel
# Langchain
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings,ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from prompts import classifier_prompt,greeting_prompt,RAG_prompt
from langchain_core.output_parsers import StrOutputParser
# load environment variables
from dotenv import load_dotenv

import warnings
import os
warnings.filterwarnings("ignore")

load_dotenv()

app = FastAPI()

# Enabling CORS so frontend (any origin) can access this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Defining and mounting frontend directories
frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
scripts_dir = os.path.join(frontend_dir, 'scripts')
styles_dir = os.path.join(frontend_dir, 'styles')

app.mount("/scripts", StaticFiles(directory=scripts_dir), name="scripts")
app.mount("/styles", StaticFiles(directory=styles_dir), name="styles")

#================================================= SQLite Database ==================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "users.db")

def get_db_connection(): # database connection function
    return sqlite3.connect(DATABASE_PATH)

def create_users_table():
    conn = get_db_connection() 
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_users_table()

# ============================================ Embeddings & Vector Store =========================================
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

vector_db = Chroma(
    persist_directory="../Chroma_Vector_Database",
    embedding_function=embeddings
)

# ==============================================LLM Models Setups ================================================

llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.2-3B-Instruct",
    task="conversational",
    temperature=0.3,
    streaming=True
)
model = ChatHuggingFace(llm=llm) # Main Model for RAG

greeting_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite",Streaming=True,temperature=0.9) # Model for Greeting query

parser = StrOutputParser() # String Output Parser

#============================================= Request Data Schemas ================================================
# Pydantic models
class SignupData(BaseModel):
    name: str
    email: str
    password: str
    role: str

class LoginData(BaseModel):
    name: str
    password: str
    role : str
    
class ChatInput(BaseModel):
    query: str
    role: str    
    session_id: str
    
# ========================================= Signup Endpoint ======================================== 
# Signup route
@app.post("/signup")
def signup(data: SignupData):
    """Registers a new user."""
    conn = get_db_connection() 
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (data.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="User already exists")

    cursor.execute(
        "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
        (data.email, data.name, data.password, data.role)
    )
    conn.commit()
    conn.close()
   
    return {"message": "Signup successful", "user": {"name": data.name, "role": data.role}}

# ================================================ Login Endpoint ===================================================
# Login route
@app.post("/login")
def login_user(data: LoginData):
    """Authenticates a user."""
    conn = get_db_connection() 
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE name=? AND password=? AND role=?", 
                   (data.name, data.password, data.role))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials or role")
    
    return {"message": "Login successful", "user": {"name": data.name, "role": data.role}}

# ==================================================== Chat Endpoint ==============================================

chat_context_window = {}  # Stores message history per user session

# chat Interface
@app.post("/chat_Interface")
def chat_response(data: ChatInput):
    query = data.query
    role = data.role.lower() 
    session_id = data.session_id
    
    # Initialize session history
    if session_id not in chat_context_window:
        chat_context_window[session_id] = []

    # Retrieve vector documents based on role
    if role == "executive":   
        retriever = vector_db.as_retriever(search_kwargs={"k": 5})
    else:     
        retriever = vector_db.as_retriever(search_kwargs={"k": 5, "filter": {"department": role}})
    
    # Classifier chain (Prompt → Gemini → OutputParser)    
    classifier_chain = classifier_prompt | greeting_model | parser     
     
    def generate():
        try:
            classification = classifier_chain.invoke({"query": query}).strip()
            
            history = chat_context_window[session_id]
            
            print(f"Classification: {classification}")
            
            # Convert history to proper format for MessagesPlaceholder
            formatted_history = []
            for msg in history:
                if msg["role"] == "user":
                    formatted_history.append(("human", msg["content"]))
                else:
                    formatted_history.append(("assistant", msg["content"]))
            
            full_response = ""
            # CASE 1: Greeting talk
            if classification == "Greeting":
                # Use greeting prompt
                prompt_messages = greeting_prompt.format_messages(
                    messages=formatted_history, 
                    input=query, 
                    role=role
                )
                
                for chunk in greeting_model.stream(prompt_messages):
                    content = chunk.content if hasattr(chunk, "content") else str(chunk)
                    full_response += content
                    yield content
            
            # CASE 2: RAG Query        
            else: 
                # Use RAG chain
                docs = retriever.invoke(query)
                context = "\n\n".join([doc.page_content for doc in docs])
                meta_data = [doc.metadata for doc in docs]
                source = meta_data[0] 
                
                # Format source for display
                source_str = source.get("source", "Company Database")
                
                prompt_messages = RAG_prompt.format_messages(
                    messages=formatted_history, 
                    input=query, 
                    context=context, 
                    source=source_str,
                    role=role
                )
                
                for chunk in model.stream(prompt_messages):
                    content = chunk.content if hasattr(chunk, "content") else str(chunk)
                    full_response += content
                    yield content
                
            # Update history
            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": full_response})
            
            # Limit context window to last 6 messages (3 turns)
            chat_context_window[session_id] = history[-6:]
            
        except Exception as e:
            error_msg = f"Error streaming response: {str(e)}"
            print(error_msg)
            yield error_msg
            
    return StreamingResponse(generate(), media_type="text/plain")

# ============================================= Frontend HTML Routes =========================================
# Serve auth.html at root "/"
@app.get("/", response_class=HTMLResponse)
def serve_auth():
    return FileResponse(os.path.join(BASE_DIR, "../frontend/auth.html"))

# Serve chat.html at "/chat"
@app.get("/chat", response_class=HTMLResponse)
def serve_chat():
    return FileResponse(os.path.join(BASE_DIR, "../frontend/chat.html"))