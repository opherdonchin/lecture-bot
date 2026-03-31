import fastapi as fa
import pydantic as pd
import sqlalchemy.orm as sqlalchemy_orm
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import app.bot_engine as bot_engine
import app.config as config_module
import app.db as db_module
import app.lecture_loader as lecture_loader
import app.models as models
import app.session_manager as session_manager

app = fa.FastAPI(title="Lecture Bot")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def root(request: fa.Request):
    """Serve the chat UI."""
    return templates.TemplateResponse(request, "chat.html")


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
    session = db.query(models.SessionModel).filter(models.SessionModel.session_id == request.session_id).first()
    if not session:
        raise fa.HTTPException(status_code=404, detail="Session not found")

    if session.ended_at is not None:
        raise fa.HTTPException(status_code=400, detail="Session has ended")

    state = session_manager.load_state(db, request.session_id)

    bot_reply, updated_state = bot_engine.generate_reply(request.message, state)

    session_manager.append_message(db, request.session_id, "user", request.message)
    session_manager.append_message(db, request.session_id, "assistant", bot_reply)
    session_manager.save_state(db, request.session_id, updated_state)

    db.commit()

    return SendMessageResponse(message=bot_reply, session_active=True)
