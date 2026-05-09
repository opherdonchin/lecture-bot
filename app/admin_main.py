from __future__ import annotations

import pathlib
import datetime as dt_module
import subprocess

import fastapi as fa
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile as StarletteUploadFile
import sqlalchemy.orm as sqlalchemy_orm

import app.admin_documents as admin_documents_module
import app.admin_generation as admin_generation_module
import app.admin_sessions as admin_sessions
import app.admin_workflow as workflow
import app.config as config_module
import app.db as db_module
import app.moodle_grade_import as moodle_grade_import
import app.root_path as root_path_module


app = fa.FastAPI(title="Lecture Bot Admin", root_path=config_module.get_settings().admin_root_path)
app.add_middleware(
    root_path_module.RootPathStripMiddleware,
    configured_root_path=config_module.get_settings().admin_root_path,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = fa.Depends(security)) -> str:
    settings = config_module.get_settings()
    if not settings.admin_username or not settings.admin_password:
        raise fa.HTTPException(status_code=500, detail="Admin credentials are not configured.")
    if credentials.username != settings.admin_username or credentials.password != settings.admin_password:
        raise fa.HTTPException(
            status_code=401,
            detail="Incorrect admin username or password.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _lectures_dir() -> pathlib.Path:
    lectures_dir = config_module.get_settings().lectures_dir
    lectures_dir.mkdir(parents=True, exist_ok=True)
    return lectures_dir


def _submissions_dir() -> pathlib.Path:
    submissions_dir = config_module.get_settings().moodle_submissions_dir
    submissions_dir.mkdir(parents=True, exist_ok=True)
    return submissions_dir


def _url_path(request: fa.Request, route_name: str, **path_params: str) -> str:
    return request.url_for(route_name, **path_params).path


def _template_context(request: fa.Request, values: dict):
    return {
        **values,
        "url_path": lambda route_name, **path_params: _url_path(request, route_name, **path_params),
    }


def _render_home(request: fa.Request):
    return templates.TemplateResponse(
        request,
        "admin_home.html",
        _template_context(request, {}),
    )


def _render_index(request: fa.Request, notice: str | None = None, error: str | None = None):
    lectures_dir = _lectures_dir()
    lecture_rows = []
    for lecture_dir in workflow.list_lecture_dirs(lectures_dir):
        config = workflow.load_lecture_config(lecture_dir)
        summary = workflow.lecture_summary(config, lecture_dir)
        lecture_rows.append(
            {
                "lecture_id": lecture_dir.name,
                "title": config.get("title", lecture_dir.name),
                "file_count": len(workflow.list_files(lecture_dir)),
                "current_step": summary["current_step"],
            }
        )
    return templates.TemplateResponse(
        request,
        "admin_index.html",
        _template_context(
            request,
            {
                "notice": notice,
                "error": error,
                "lectures": lecture_rows,
            },
        ),
    )


def _moodle_database_path() -> pathlib.Path:
    database_path = db_module._sqlite_file_path(config_module.get_settings().database_url)
    if database_path is None:
        raise ValueError("Moodle grade import currently requires a file-backed SQLite database.")
    return database_path


def _grade_file_info(path: pathlib.Path) -> dict:
    if not path.exists():
        return {"exists": False, "name": path.name, "size_bytes": 0, "modified_at": ""}
    modified_at = dt_module.datetime.fromtimestamp(path.stat().st_mtime, tz=dt_module.timezone.utc)
    return {
        "exists": True,
        "name": path.name,
        "size_bytes": path.stat().st_size,
        "modified_at": modified_at.strftime("%Y-%m-%d %H:%M UTC"),
    }


def _grade_context(
    *,
    notice: str | None = None,
    error: str | None = None,
    summary: dict[str, int] | None = None,
) -> dict:
    settings = config_module.get_settings()
    submissions_dir = _submissions_dir()
    lecture_rows = []
    archives = {}
    for lecture_dir in workflow.list_lecture_dirs(_lectures_dir()):
        lecture_id = lecture_dir.name
        archive_path = moodle_grade_import.default_submission_zip_path(submissions_dir, lecture_id)
        archives[lecture_id] = archive_path
        config = workflow.load_lecture_config(lecture_dir)
        lecture_rows.append(
            {
                "lecture_id": lecture_id,
                "title": config.get("title", lecture_id),
                "archive": _grade_file_info(archive_path),
            }
        )

    return {
        "notice": notice,
        "error": error,
        "summary": summary,
        "lectures": lecture_rows,
        "participants_file": _grade_file_info(settings.moodle_participants_csv),
        "upload_file": _grade_file_info(settings.moodle_grade_import_csv),
        "report_file": _grade_file_info(settings.moodle_grade_import_report_csv),
        "has_archives": any(path.exists() for path in archives.values()),
    }


def _render_grades(
    request: fa.Request,
    *,
    notice: str | None = None,
    error: str | None = None,
    summary: dict[str, int] | None = None,
):
    return templates.TemplateResponse(
        request,
        "admin_grades.html",
        _template_context(request, _grade_context(notice=notice, error=error, summary=summary)),
    )


def _run_grade_import() -> dict[str, int]:
    settings = config_module.get_settings()
    submissions_dir = _submissions_dir()
    known_lecture_ids = {lecture_dir.name for lecture_dir in workflow.list_lecture_dirs(_lectures_dir())}
    archives = {
        lecture_id: path
        for lecture_id, path in moodle_grade_import.discover_submission_archives(submissions_dir).items()
        if lecture_id in known_lecture_ids
    }
    if not archives:
        raise ValueError("No lecture submission ZIPs have been uploaded yet.")
    result = moodle_grade_import.prepare_moodle_grade_import(
        submission_archives=archives,
        participants_csv_path=settings.moodle_participants_csv,
        db_path=_moodle_database_path(),
    )
    moodle_grade_import.write_grade_import_outputs(
        result,
        upload_csv_path=settings.moodle_grade_import_csv,
        report_csv_path=settings.moodle_grade_import_report_csv,
    )
    return result.summary


def _session_filters_from_params(
    *,
    student_id: str = "",
    student_match: str = "contains",
    lecture_id: str = "",
    start_date: str = "",
    end_date: str = "",
    min_user_turns: str = "",
    max_user_turns: str = "",
    min_grade: str = "",
    max_grade: str = "",
    page: int = 1,
    page_size: int = admin_sessions.DEFAULT_PAGE_SIZE,
) -> admin_sessions.SessionFilters:
    return admin_sessions.SessionFilters(
        student_id=student_id,
        student_match="exact" if student_match == "exact" else "contains",
        lecture_id=lecture_id,
        start_date=start_date,
        end_date=end_date,
        min_user_turns=min_user_turns,
        max_user_turns=max_user_turns,
        min_grade=min_grade,
        max_grade=max_grade,
        page=page,
        page_size=page_size,
    )


def _render_sessions(
    request: fa.Request,
    db: sqlalchemy_orm.Session,
    filters: admin_sessions.SessionFilters,
    error: str | None = None,
):
    try:
        session_page = admin_sessions.list_sessions(db, filters)
    except ValueError as exc:
        session_page = {
            "rows": [],
            "total": 0,
            "page": admin_sessions.normalized_page(filters.page),
            "page_size": admin_sessions.normalized_page_size(filters.page_size),
            "has_previous": False,
            "has_next": False,
        }
        error = str(exc)

    lectures = [lecture_dir.name for lecture_dir in workflow.list_lecture_dirs(_lectures_dir())]
    return templates.TemplateResponse(
        request,
        "admin_sessions.html",
        _template_context(
            request,
            {
                "filters": filters,
                "session_page": session_page,
                "lectures": lectures,
                "error": error,
                "max_export_sessions": admin_sessions.MAX_EXPORT_SESSIONS,
            },
        ),
    )


def _render_lecture(
    request: fa.Request,
    lecture_id: str,
    notice: str | None = None,
    error: str | None = None,
    build_log: list[str] | None = None,
):
    lecture_dir = workflow.resolve_lecture_dir(_lectures_dir(), lecture_id)
    lecture_dir.mkdir(parents=True, exist_ok=True)
    config = workflow.load_lecture_config(lecture_dir)
    files = workflow.list_files(lecture_dir)
    summary = workflow.lecture_summary(config, lecture_dir)
    return templates.TemplateResponse(
        request,
        "admin_lecture.html",
        _template_context(
            request,
            {
                "lecture_id": lecture_id,
                "lecture_dir": lecture_dir,
                "config": config,
                "files": files,
                "summary": summary,
                "notice": notice,
                "error": error,
                "build_log": build_log or [],
                "source_keys": workflow.SOURCE_KEYS,
                "display_labels": workflow.DISPLAY_LABELS,
                "target_by_key": workflow.TARGET_BY_KEY,
                "bundle_stage_files": {
                    "minutes": workflow.required_bundle_files("minutes"),
                    "rubric": workflow.required_bundle_files("rubric"),
                },
            },
        ),
    )


_STUDENT_SERVICE = "lecture-bot.service"


def _restart_student_app() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "restart", _STUDENT_SERVICE],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return True, "Student app restarted successfully."
        return False, f"systemctl returned exit code {result.returncode}: {(result.stderr or result.stdout).strip()}"
    except FileNotFoundError:
        return False, "systemctl not found — restart is not supported in this environment."
    except subprocess.TimeoutExpired:
        return False, "Restart command timed out."
    except Exception as exc:
        return False, f"Unexpected error: {exc}"


@app.post("/restart-student-app", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="restart_student_app")
def restart_student_app(request: fa.Request):
    ok, message = _restart_student_app()
    notice = message if ok else None
    error = None if ok else message
    return _render_index(request, notice=notice, error=error)


@app.get("/", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="admin_root")
def admin_root(request: fa.Request):
    return _render_home(request)


@app.get("/analysis", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="admin_analysis")
def admin_analysis(request: fa.Request):
    return templates.TemplateResponse(
        request,
        "admin_analysis.html",
        _template_context(request, {}),
    )


@app.get("/lectures", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="admin_lectures")
def admin_lectures(request: fa.Request):
    return _render_index(request)


@app.get("/grades", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="admin_grades")
def admin_grades(request: fa.Request):
    return _render_grades(request)


@app.post("/grades/participants", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="upload_grade_participants")
async def upload_grade_participants(
    request: fa.Request,
    uploaded_file: fa.UploadFile = fa.File(...),
):
    if not uploaded_file.filename:
        return _render_grades(request, error="Choose a participants CSV file to upload.")
    try:
        workflow.save_uploaded_file(config_module.get_settings().moodle_participants_csv, uploaded_file)
    except Exception as exc:
        return _render_grades(request, error=str(exc))
    return _render_grades(request, notice="Participants CSV updated.")


@app.post("/grades/submissions", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="upload_grade_submissions")
async def upload_grade_submissions(request: fa.Request):
    form = await request.form()
    saved: list[str] = []
    submissions_dir = _submissions_dir()
    for lecture_dir in workflow.list_lecture_dirs(_lectures_dir()):
        field_name = f"submission_{lecture_dir.name}"
        uploaded_file = form.get(field_name)
        if not isinstance(uploaded_file, StarletteUploadFile) or not uploaded_file.filename:
            continue
        destination = moodle_grade_import.default_submission_zip_path(submissions_dir, lecture_dir.name)
        try:
            workflow.save_uploaded_file(destination, uploaded_file)
        except Exception as exc:
            return _render_grades(request, error=str(exc))
        saved.append(lecture_dir.name)

    if not saved:
        return _render_grades(request, error="Choose at least one lecture submission ZIP to upload.")

    try:
        summary = _run_grade_import()
    except Exception as exc:
        return _render_grades(
            request,
            error=f"Saved {', '.join(saved)}, but grade import preparation failed: {exc}",
        )
    return _render_grades(
        request,
        notice=f"Saved {', '.join(saved)} and regenerated Moodle import files.",
        summary=summary,
    )


@app.post("/grades/prepare", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="prepare_grade_import")
async def prepare_grade_import(request: fa.Request):
    try:
        summary = _run_grade_import()
    except Exception as exc:
        return _render_grades(request, error=str(exc))
    return _render_grades(request, notice="Regenerated Moodle import files.", summary=summary)


@app.get("/grades/files/{kind}", dependencies=[fa.Depends(require_admin)], name="download_grade_file")
def download_grade_file(kind: str):
    settings = config_module.get_settings()
    paths = {
        "import": settings.moodle_grade_import_csv,
        "report": settings.moodle_grade_import_report_csv,
    }
    target = paths.get(kind)
    if target is None or not target.exists():
        raise fa.HTTPException(status_code=404, detail="File not found.")
    return FileResponse(target, media_type="text/csv", filename=target.name)


@app.get("/sessions", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="admin_sessions")
def admin_session_list(
    request: fa.Request,
    student_id: str = "",
    student_match: str = "contains",
    lecture_id: str = "",
    start_date: str = "",
    end_date: str = "",
    min_user_turns: str = "",
    max_user_turns: str = "",
    min_grade: str = "",
    max_grade: str = "",
    page: int = 1,
    page_size: int = admin_sessions.DEFAULT_PAGE_SIZE,
    db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db),
):
    filters = _session_filters_from_params(
        student_id=student_id,
        student_match=student_match,
        lecture_id=lecture_id,
        start_date=start_date,
        end_date=end_date,
        min_user_turns=min_user_turns,
        max_user_turns=max_user_turns,
        min_grade=min_grade,
        max_grade=max_grade,
        page=page,
        page_size=page_size,
    )
    return _render_sessions(request, db, filters)


@app.post("/sessions/export", dependencies=[fa.Depends(require_admin)], name="export_sessions")
async def export_sessions(
    request: fa.Request,
    db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db),
):
    form = await request.form()
    selected_session_ids = [str(value) for value in form.getlist("session_id")]
    settings = config_module.get_settings()
    try:
        zip_bytes = admin_sessions.build_sessions_export_zip(
            db=db,
            session_ids=selected_session_ids,
            database_url=settings.database_url,
            lectures_dir=settings.lectures_dir,
        )
    except ValueError as exc:
        raise fa.HTTPException(status_code=400, detail=str(exc)) from exc

    timestamp = dt_module.datetime.now(dt_module.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"lecture_bot_sessions_{timestamp}.zip"
    return StreamingResponse(
        iter([zip_bytes]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/lectures", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="create_lecture")
async def create_lecture(
    request: fa.Request,
    lecture_id: str = fa.Form(...),
    title: str = fa.Form(""),
    course: str = fa.Form(""),
):
    try:
        lecture_dir = workflow.create_lecture_folder(_lectures_dir(), lecture_id, title, course)
    except Exception as exc:
        return _render_index(request, error=str(exc))
    return _render_lecture(request, lecture_dir.name, notice="Lecture folder created.")


@app.get("/lectures/{lecture_id}", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="lecture_detail")
def lecture_detail(request: fa.Request, lecture_id: str):
    return _render_lecture(request, lecture_id)


@app.post("/lectures/{lecture_id}/metadata", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="update_lecture_metadata")
async def update_lecture_metadata(
    request: fa.Request,
    lecture_id: str,
    title: str = fa.Form(""),
    course: str = fa.Form(""),
    active: str | None = fa.Form(None),
):
    lecture_dir = workflow.resolve_lecture_dir(_lectures_dir(), lecture_id)
    config = workflow.load_lecture_config(lecture_dir)
    updated = workflow.update_metadata(config, title=title, course=course, active=active is not None)
    workflow.save_lecture_config(lecture_dir, updated)
    return _render_lecture(request, lecture_id, notice="Lecture metadata updated.")


@app.post("/lectures/{lecture_id}/sources", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="update_sources")
async def update_sources(
    request: fa.Request,
    lecture_id: str,
    slides_source: str = fa.Form(""),
    handout_source: str = fa.Form(""),
    notebook_source: str = fa.Form(""),
    transcript_source: str = fa.Form(""),
):
    lecture_dir = workflow.resolve_lecture_dir(_lectures_dir(), lecture_id)
    config = workflow.load_lecture_config(lecture_dir)
    updated = workflow.update_selected_sources(
        config,
        {
            "slides": slides_source,
            "handout": handout_source,
            "notebook": notebook_source,
            "transcript": transcript_source,
        },
    )
    workflow.save_lecture_config(lecture_dir, updated)
    return _render_lecture(request, lecture_id, notice="Selected source files updated.")


@app.post("/lectures/{lecture_id}/upload", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="upload_file")
async def upload_file(
    request: fa.Request,
    lecture_id: str,
    uploaded_file: fa.UploadFile = fa.File(...),
):
    lecture_dir = workflow.resolve_lecture_dir(_lectures_dir(), lecture_id)
    if not uploaded_file.filename:
        return _render_lecture(request, lecture_id, error="Choose a file to upload.")
    destination = lecture_dir / pathlib.Path(uploaded_file.filename).name
    workflow.save_uploaded_file(destination, uploaded_file)
    return _render_lecture(request, lecture_id, notice=f"Uploaded {destination.name}.")


@app.post("/lectures/{lecture_id}/delete", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="delete_file")
async def delete_file(
    request: fa.Request,
    lecture_id: str,
    filename: str = fa.Form(...),
):
    lecture_dir = workflow.resolve_lecture_dir(_lectures_dir(), lecture_id)
    config = workflow.load_lecture_config(lecture_dir)
    try:
        workflow.delete_file(lecture_dir, filename)
    except Exception as exc:
        return _render_lecture(request, lecture_id, error=str(exc))

    updated = workflow.update_selected_sources(
        config,
        {
            key: ""
            if config.get("files", {}).get(key, {}).get("source") == filename
            else config.get("files", {}).get(key, {}).get("source", "")
            for key in workflow.SOURCE_KEYS
        },
    )
    workflow.save_lecture_config(lecture_dir, updated)
    return _render_lecture(request, lecture_id, notice=f"Deleted {filename}.")


@app.post("/lectures/{lecture_id}/build/local", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="build_local")
async def build_local(
    request: fa.Request,
    lecture_id: str,
):
    lecture_dir = workflow.resolve_lecture_dir(_lectures_dir(), lecture_id)
    config = workflow.load_lecture_config(lecture_dir)
    try:
        build_log = workflow.build_local_sources(lecture_dir, config)
    except Exception as exc:
        return _render_lecture(request, lecture_id, error=str(exc))
    workflow.save_lecture_config(lecture_dir, config)
    return _render_lecture(
        request,
        lecture_id,
        notice="Local lecture files prepared. Next step: use the minutes prompt and upload the returned minutes.json.",
        build_log=build_log,
    )


@app.get("/lectures/{lecture_id}/prompt/{stage}.txt", dependencies=[fa.Depends(require_admin)], name="download_prompt")
def download_prompt(lecture_id: str, stage: str):
    prompt_text = workflow.build_manual_prompt(stage)
    filename = f"{lecture_id}_{stage}_prompt.txt"
    return StreamingResponse(
        iter([prompt_text.encode("utf-8")]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/lectures/{lecture_id}/bundle/{stage}.zip", dependencies=[fa.Depends(require_admin)], name="download_bundle")
def download_bundle(lecture_id: str, stage: str):
    lecture_dir = workflow.resolve_lecture_dir(_lectures_dir(), lecture_id)
    bundle = workflow.build_bundle_bytes(lecture_dir, stage)
    filename = f"{lecture_id}_{stage}_bundle.zip"
    return StreamingResponse(
        iter([bundle]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/lectures/{lecture_id}/files/{filename}", dependencies=[fa.Depends(require_admin)], name="download_lecture_file")
def download_lecture_file(lecture_id: str, filename: str):
    lecture_dir = workflow.resolve_lecture_dir(_lectures_dir(), lecture_id)
    target = (lecture_dir / filename).resolve()
    if target.parent != lecture_dir.resolve() or not target.exists():
        raise fa.HTTPException(status_code=404, detail="File not found.")
    return FileResponse(target)


@app.get("/documents", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="admin_documents")
def admin_documents_list(
    request: fa.Request,
    db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db),
):
    grouped = admin_documents_module.list_all_documents(db)
    return templates.TemplateResponse(
        request,
        "admin_documents.html",
        _template_context(request, {"grouped_docs": grouped}),
    )


@app.get("/documents/tutor-prompts", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="admin_tutor_prompts")
def admin_tutor_prompts(
    request: fa.Request,
    notice: str = "",
    error: str = "",
    db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db),
):
    prompts = admin_documents_module.list_tutor_prompts(db)
    return templates.TemplateResponse(
        request,
        "admin_tutor_prompts.html",
        _template_context(request, {
            "prompts": prompts,
            "notice": notice or None,
            "error": error or None,
        }),
    )


@app.get("/documents/{document_id}", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="admin_document_detail")
def admin_document_detail(
    request: fa.Request,
    document_id: str,
    notice: str = "",
    error: str = "",
    db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db),
):
    doc = admin_documents_module.get_document_detail(db, document_id)
    if doc is None:
        raise fa.HTTPException(status_code=404, detail=f"Document {document_id!r} not found.")
    return templates.TemplateResponse(
        request,
        "admin_document_detail.html",
        _template_context(request, {
            "doc": doc,
            "notice": notice or None,
            "error": error or None,
        }),
    )


@app.post("/documents/{document_id}/activate", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="activate_document")
def activate_document(
    request: fa.Request,
    document_id: str,
    db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db),
):
    ok, message = admin_documents_module.activate_tutor_prompt(db, document_id)
    if ok:
        return RedirectResponse(
            url=str(request.url_for("admin_tutor_prompts")) + f"?notice={message}",
            status_code=303,
        )
    doc = admin_documents_module.get_document_detail(db, document_id)
    if doc is None:
        raise fa.HTTPException(status_code=404, detail=f"Document {document_id!r} not found.")
    return templates.TemplateResponse(
        request,
        "admin_document_detail.html",
        _template_context(request, {"doc": doc, "notice": None, "error": message}),
    )


@app.get("/generate-tutor-prompt", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="generate_tutor_prompt_form")
def generate_tutor_prompt_form(
    request: fa.Request,
    db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db),
):
    context_docs = admin_generation_module.get_generation_context(db)
    return templates.TemplateResponse(
        request,
        "admin_generate.html",
        _template_context(request, {"context_docs": context_docs, "result": None}),
    )


@app.post("/generate-tutor-prompt", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="generate_tutor_prompt")
async def generate_tutor_prompt(
    request: fa.Request,
    spec_title: str = fa.Form(""),
    spec_text: str = fa.Form(""),
    db: sqlalchemy_orm.Session = fa.Depends(db_module.get_db),
):
    context_docs = admin_generation_module.get_generation_context(db)
    if not spec_text.strip():
        return templates.TemplateResponse(
            request,
            "admin_generate.html",
            _template_context(request, {
                "context_docs": context_docs,
                "result": {"ok": False, "run_id": None, "error": "Spec text is required."},
                "form_title": spec_title,
                "form_spec": spec_text,
            }),
        )
    result = admin_generation_module.run_generation(db, spec_text.strip(), spec_title.strip())
    return templates.TemplateResponse(
        request,
        "admin_generate.html",
        _template_context(request, {
            "context_docs": context_docs,
            "result": result,
            "form_title": spec_title,
            "form_spec": spec_text,
        }),
    )


@app.post("/lectures/{lecture_id}/generated/{kind}", response_class=HTMLResponse, dependencies=[fa.Depends(require_admin)], name="upload_generated_artifact")
async def upload_generated_artifact(
    request: fa.Request,
    lecture_id: str,
    kind: str,
    uploaded_file: fa.UploadFile = fa.File(...),
):
    lecture_dir = workflow.resolve_lecture_dir(_lectures_dir(), lecture_id)
    config = workflow.load_lecture_config(lecture_dir)
    if not uploaded_file.filename:
        return _render_lecture(request, lecture_id, error="Choose a file to upload.")
    try:
        updated = workflow.save_generated_artifact(lecture_dir, config, kind, uploaded_file)
        workflow.save_lecture_config(lecture_dir, updated)
    except Exception as exc:
        return _render_lecture(request, lecture_id, error=str(exc))

    if kind == "minutes":
        notice = "Saved minutes.json. Next step: download the rubric prompt and support bundle, then upload rubric.md."
    else:
        notice = "Saved rubric.md and refreshed topics in lecture_config.json."
    return _render_lecture(request, lecture_id, notice=notice)
