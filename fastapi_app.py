
import os
import csv
import io
import uvicorn
from fastapi import FastAPI, HTTPException, Body, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import json
from datetime import datetime, timedelta
from jose import JWTError, jwt

from dotenv import load_dotenv
from src.vanna_sql import MyVanna
from src.config import load_config

from cachetools import TTLCache

# --- Configure Logging ---
class CSVFormatter(logging.Formatter):
    def __init__(self):
        super().__init__()
        self.output = io.StringIO()
        self.writer = csv.writer(self.output, quoting=csv.QUOTE_MINIMAL)

    def format(self, record):
        row = [
            self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            record.name,
            record.levelname,
            record.getMessage()
        ]
        self.output.seek(0)
        self.output.truncate(0)
        self.writer.writerow(row)
        return self.output.getvalue().strip()

# Create CSV handler
csv_handler = logging.FileHandler('vanna_activity.csv', encoding='utf-8')
csv_handler.setFormatter(CSVFormatter())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vanna_activity.log', encoding='utf-8'),
        csv_handler,
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("VannaAPI")

# --- Demo Auth Configuration ---
SECRET_KEY = "demo-secret-key-change-in-production"
ALGORITHM = "HS256"
DEMO_PASSWORD = "123"

# In-memory user storage: {email: user_id}
USER_STORE = {}

# --- 1. Load Config & Env ---
load_dotenv()
config = load_config()
from contextlib import asynccontextmanager

# Global instance
vn = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global vn
    print("Starting up: Initializing Vanna and Database connection...")
    try:
        # Initialize Vanna
        vn = MyVanna(config=config)
        print("✅ MyVanna instance initialized.")
        
        # Connect to DB
        host = os.getenv("REDSHIFT_HOST")
        dbname = os.getenv("REDSHIFT_DB")
        user = os.getenv("REDSHIFT_USER")
        password = os.getenv("REDSHIFT_PASSWORD")
        port = int(os.getenv("REDSHIFT_PORT", 5439))

        vn.connect_to_postgres(
            host=host,
            dbname=dbname,
            user=user,
            password=password,
            port=port
        )
        print("✅ Connected to Database (Redshift/Postgres)")
    except Exception as e:
        print(f"Initialization failed: {e}")
    
    yield
    print("🛑 Shutting down...")


import uuid

# --- 4. Define API Schemas (Pydantic) ---

class LoginRequest(BaseModel):
    email: str = Field(..., description="Company email address")
    password: str = Field(..., description="Password (demo: '123')")

class LoginResponse(BaseModel):
    access_token: str
    user_id: str
    email: str
    message: str

class AskRequest(BaseModel):
    question: str = Field(..., description="The natural language question to ask.")
    include_explanation: bool = Field(True, description="Whether to generate an explanation for the SQL.")
    allow_llm_to_see_data: bool = Field(False, description="Allow LLM to run intermediate SQL for data introspection.")

class AskResponse(BaseModel):
    request_id: str
    question: str
    sql: str
    explanation: Optional[str] = None
    valid: bool = True 

class RunSQLRequest(BaseModel):
    request_id: str = Field(..., description="The ID of the request to link context.")
    sql: str = Field(..., description="The SQL query to execute.")

class RunSQLResponse(BaseModel):
    columns: List[str]
    data: List[Dict[str, Any]]

class FollowupResponse(BaseModel):
    questions: List[str]

class FeedbackRequest(BaseModel):
    request_id: str = Field(..., description="The ID of the request to provide feedback on.")
    is_correct: bool = Field(..., description="Whether the SQL result was correct.")
    edited_sql: Optional[str] = Field(None, description="If incorrect, the manually corrected SQL.")

class FeedbackResponse(BaseModel):
    message: str
    trained: bool = False    

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# --- 5. Create FastAPI App ---
app = FastAPI(
    title="Vanna Text-to-SQL API",
    description="A typed REST API for generating and running SQL queries using Vanna + Gemini + Qdrant.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS (important if you build a custom UI later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


REQUEST_CACHE = TTLCache(maxsize=500, ttl=3600)

# Mount Static Files 
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the Login UI."""
    with open("static/login.html", "r", encoding="utf-8") as f:
        return f.read()
    return HTMLResponse(
        content=html,
        status_code=200,
        headers={"Content-Type": "text/html; charset=utf-8"}
    )

# --- 6. Endpoints ---

# Auth Helper Functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id, "email": email}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Demo login: Password is always '123'
    Creates new user if email doesn't exist
    """
    # Check password
    if request.password != DEMO_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password. Demo password is '123'")
    
    # Check if user exists
    if request.email in USER_STORE:
        user_id = USER_STORE[request.email]
        message = "Welcome back!"
        logger.info(f"LOGIN | User ID: {user_id} | Email: {request.email}")
    else:
        # Create new user
        user_id = str(uuid.uuid4())
        USER_STORE[request.email] = user_id
        message = "Account created successfully!"
        logger.info(f"NEW USER | User ID: {user_id} | Email: {request.email}")
    
    # Create token
    access_token = create_access_token({"sub": user_id, "email": request.email})
    
    return LoginResponse(
        access_token=access_token,
        user_id=user_id,
        email=request.email,
        message=message
    )

def generate_sql_explanation(question: str, sql: str) -> str:
    """
    Generate a human-readable explanation of why this SQL was generated.
    Explains table/column selection and the reasoning behind it.
    """
    prompt = f"""You are a data analyst explaining your SQL query reasoning to a business user.

Question asked: "{question}"

SQL generated:
{sql}

Please provide a clear, point-wise explanation covering:
1. What the user was asking for
2. Which tables were selected and why
3. Which columns were used and their purpose
4. Any filters/conditions applied and why
5. The overall logic of the query

Format your response as numbered points, be concise and professional."""

    try:
        explanation = vn.submit_prompt(prompt)
        return explanation
    except Exception as e:
        return f"Unable to generate explanation: {str(e)}"

@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "vanna-backend"}

@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest, current_user: dict = Depends(get_current_user)):
    """
    Generates SQL from a natural language question.
    Returns a request_id for tracking context.
    """
    try:
        # Log incoming request
        logger.info(f"NEW QUESTION | User: {current_user['email']} ({current_user['user_id']}) | Question: {request.question}")
        
        # 1. Generate SQL
        sql = vn.generate_sql(
            question=request.question,
            allow_llm_to_see_data=request.allow_llm_to_see_data
        )
        
        # 2. Validate
        valid = vn.is_sql_valid(sql)

        # 3. Generate explanation if requested
        explanation = None
        if request.include_explanation:
            explanation = generate_sql_explanation(request.question, sql)
            
        # 4. Cache Context
        request_id = str(uuid.uuid4())
        REQUEST_CACHE[request_id] = {
            "question": request.question,
            "sql": sql,
            "df": None,
            "executed": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log SQL generation
        logger.info(f"SQL GENERATED | User: {current_user['email']} | Request ID: {request_id} | Valid: {valid} | SQL: {sql[:100]}...")
        
        return AskResponse(
            request_id=request_id,
            question=request.question,
            sql=sql,
            explanation=explanation,
            valid=valid
        )
    except Exception as e:
        logger.error(f"ERROR in /ask | Question: {request.question} | Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run_sql", response_model=RunSQLResponse)
def run_sql_query(request: RunSQLRequest, current_user: dict = Depends(get_current_user)):
    """
    Executes a given SQL query. 
    Updates the request context with results for follow-up generation.
    """
    try:
        logger.info(f"EXECUTING SQL | User: {current_user['email']} | Request ID: {request.request_id}")
        
        # Execute SQL
        df = vn.run_sql(sql=request.sql)
        
        if df is None:
             logger.warning(f"NO RESULTS | Request ID: {request.request_id}")
             raise HTTPException(status_code=400, detail="Query returned no results or failed.")

        # Update Cache with DataFrame for followups
        if request.request_id in REQUEST_CACHE:
             REQUEST_CACHE[request.request_id]["df"] = df
             REQUEST_CACHE[request.request_id]["sql"] = request.sql
             REQUEST_CACHE[request.request_id]["executed"] = True
             REQUEST_CACHE[request.request_id]["execution_time"] = datetime.now().isoformat()

        # Convert to JSON
        data = df.to_dict(orient='records')
        columns = df.columns.tolist()
        
        logger.info(f"SQL EXECUTED | User: {current_user['email']} | Request ID: {request.request_id} | Rows: {len(data)} | Columns: {len(columns)}")
        
        return RunSQLResponse(columns=columns, data=data)
    except Exception as e:
        logger.error(f"EXECUTION ERROR | Request ID: {request.request_id} | Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/followups", response_model=FollowupResponse)
def get_followup_questions(request_id: str):
    """
    Generate suggested follow-up questions based on the previous question, SQL, and results.
    Requires a valid request_id where run_sql has been called.
    """
    try:
        context = REQUEST_CACHE.get(request_id)
        if not context:
            raise HTTPException(status_code=404, detail="Request ID not found.")
            
        if context.get("df") is None:
             raise HTTPException(status_code=400, detail="SQL results not available. Run SQL first.")

        questions = vn.generate_followup_questions(
            question=context["question"],
            sql=context["sql"],
            df=context["df"]
        )
        return FollowupResponse(questions=questions)
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Followup generation error: {e}")
        return FollowupResponse(questions=[])

@app.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    """
    Submit user feedback on query results.
    If correct: add to training.
    If incorrect with edited_sql: update cache and allow re-run.
    """
    try:
        context = REQUEST_CACHE.get(request.request_id)
        if not context:
            raise HTTPException(status_code=404, detail="Request ID not found.")
        
        if request.is_correct:
            # User confirmed result is correct → train Vanna
            logger.info(f"TRAINING | User: {current_user['email']} | Request ID: {request.request_id} | Question: {context['question']} | SQL: {context['sql'][:100]}...")
            
            vn.add_question_sql(
                question=context["question"],
                sql=context["sql"]
            )
            return FeedbackResponse(
                message="Thank you! Added to training data.",
                trained=True
            )
        else:
            # User said it's incorrect
            if request.edited_sql:
                logger.info(f"SQL EDITED | User: {current_user['email']} | Request ID: {request.request_id} | Old SQL: {context['sql'][:50]}... | New SQL: {request.edited_sql[:50]}...")
                
                # User provided corrected SQL → update cache
                context["sql"] = request.edited_sql
                context["df"] = None  # Reset df so they can re-run
                context["edited"] = True
                context["edit_time"] = datetime.now().isoformat()
                REQUEST_CACHE[request.request_id] = context
                return FeedbackResponse(
                    message="SQL updated. You can now re-run the query.",
                    trained=False
                )
            else:
                return FeedbackResponse(
                    message="Please provide the corrected SQL.",
                    trained=False
                )
    except Exception as e:
        logger.error(f"FEEDBACK ERROR | Request ID: {request.request_id} | Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=5000, reload=True)
