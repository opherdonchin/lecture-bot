import json as j

import fastapi as fa
import pydantic as pd
import sqlalchemy.orm as sqlalchemy_orm

import app.bot_engine as bot_engine
import app.config as config_module
import app.db as db_module
import app.lecture_loader as lecture_loader
import app.models as models
import app.session_manager as session_manager

app = fa.FastAPI(title="Lecture Bot")


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Lecture Bot API", "version": "0.1.0"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Request/Response models
class StartSessionRequest(pd.BaseModel):
    student_id: str
    lecture_id: str


class StartSessionResponse(pd.BaseModel):
    session_id: str
    message: str


class SendMessageRequest(pd.BaseModel):
    session_id: str
    message: str


class SendMessageResponse(pd.BaseModel):
    message: str
    session_active: bool


# API endpoints
@app.post("/start_session", response_model=StartSessionResponse)
def start_session(request: StartSessionRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Start a new tutoring session."""
    settings = config_module.get_settings()
    
    # Load the lecture package
    try:
        lecture_package = lecture_loader.load_lecture_package(settings.lectures_dir, request.lecture_id)
    except lecture_loader.LectureNotFoundError as e:
        raise fa.HTTPException(status_code=404, detail=str(e))
    
    # Create the session
    session = session_manager.create_session(db, request.student_id, request.lecture_id, lecture_package)
    
    # Generate opening message
    opening_message = bot_engine.build_opening_message(lecture_package)
    
    # Save the opening message
    session_manager.append_message(db, session.session_id, "assistant", opening_message)
    
    return StartSessionResponse(session_id=session.session_id, message=opening_message)


@app.post("/send_message", response_model=SendMessageResponse)
def send_message(request: SendMessageRequest, db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db)):
    """Send a message in an active session."""
    # Get the session
    session = db.query(models.SessionModel).filter(models.SessionModel.session_id == request.session_id).first()
    if not session:
        raise fa.HTTPException(status_code=404, detail="Session not found")
    
    if session.ended_at is not None:
        raise fa.HTTPException(status_code=400, detail="Session has ended")
    
    # Get the session state
    session_state = db.query(models.SessionStateModel).filter(models.SessionStateModel.session_id == request.session_id).first()
    if not session_state:
        raise fa.HTTPException(status_code=404, detail="Session state not found")
    
    # Parse the state
    state = j.loads(session_state.state_json)
    
    # Generate a reply
    bot_reply, updated_state = bot_engine.generate_reply(request.message, state)
    
    # Save user message
    session_manager.append_message(db, request.session_id, "user", request.message)
    
    # Save bot reply
    session_manager.append_message(db, request.session_id, "assistant", bot_reply)
    
    # Update session state
    session_state.state_json = j.dumps(updated_state, ensure_ascii=False)
    db.commit()
    
    return SendMessageResponse(message=bot_reply, session_active=True)
