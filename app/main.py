from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Lecture Bot")


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Lecture Bot API", "version": "0.1.0"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Request/Response models
class StartSessionRequest(BaseModel):
    student_id: str
    lecture_id: str


class StartSessionResponse(BaseModel):
    session_id: str
    message: str


class SendMessageRequest(BaseModel):
    session_id: str
    message: str


class SendMessageResponse(BaseModel):
    message: str
    session_active: bool


# API endpoints
@app.post("/start_session", response_model=StartSessionResponse)
def start_session(request: StartSessionRequest):
    """Start a new tutoring session."""
    # TODO: Implement session creation
    pass


@app.post("/send_message", response_model=SendMessageResponse)
def send_message(request: SendMessageRequest):
    """Send a message in an active session."""
    # TODO: Implement message handling
    pass
