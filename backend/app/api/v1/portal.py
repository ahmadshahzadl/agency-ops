"""Client portal: everything an external client user may see or do.

Portal users (users.client_id set, 'client' role with zero internal
permissions) are locked out of the whole internal API; this namespace is
their entire surface. Every query filters by the caller's client_id, and
responses are sanitized: no assignees, no internal notes, no QA states,
no draft documents."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from app.models import (
    Client as ClientModel, Project as ProjectModel, Task as TaskModel,
    Milestone as MilestoneModel, Invoice as InvoiceModel, Quote as QuoteModel,
    Agreement as AgreementModel, Notification as NotificationModel, User as UserModel,
    Board as BoardModel, BoardMember as BoardMemberModel,
)
from app.api.deps import get_portal_user
from app.services.activity_service import log_activity, notifications_updated_this_request, tasks_updated_this_request
from app.services import email_service

router = APIRouter(prefix="/portal", tags=["portal"])


# ---------- response shapes (sanitized) ----------

class PortalTask(BaseModel):
    title: str
    status: str  # todo | in_progress | review | done (qa states masked)
    item_type: str
    due_date: Optional[str] = None


class PortalMilestone(BaseModel):
    name: str
    due_date: Optional[str] = None
    completed: bool
    task_total: int = 0
    task_done: int = 0


class PortalProject(BaseModel):
    id: UUID
    name: str
    status: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_tasks: int = 0
    percent_done: int = 0


class PortalProjectDetail(PortalProject):
    milestones: list[PortalMilestone] = []
    tasks: list[PortalTask] = []


class PortalInvoice(BaseModel):
    id: UUID
    number: str
    amount: Decimal
    currency: str
    status: str
    issued_at: Optional[str] = None
    due_date: Optional[str] = None
    paid_total: Decimal = Decimal("0")


class PortalQuoteItem(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class PortalQuote(BaseModel):
    id: UUID
    number: str
    title: str
    status: str
    currency: str
    total: Decimal
    valid_until: Optional[str] = None
    terms: Optional[str] = None
    items: list[PortalQuoteItem] = []


class PortalOverview(BaseModel):
    client_name: str
    projects: list[PortalProject] = []
    open_invoices: int = 0
    pending_quotes: int = 0
    pending_agreements: int = 0


class IssueReport(BaseModel):
    title: str
    description: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    severity: str = "medium"


# ---------- helpers ----------

def _client_status(s: str) -> str:
    return "review" if s in ("review", "qa_failed") else s


def _project_summary(db: Session, p: ProjectModel) -> PortalProject:
    total = db.query(func.count(TaskModel.id)).filter(TaskModel.project_id == p.id).scalar() or 0
    done = db.query(func.count(TaskModel.id)).filter(TaskModel.project_id == p.id, TaskModel.status == "done").scalar() or 0
    return PortalProject(
        id=p.id, name=p.name, status=p.status or "active",
        start_date=str(p.start_date) if p.start_date else None,
        end_date=str(p.end_date) if p.end_date else None,
        total_tasks=total, percent_done=round(done * 100 / total) if total else 0,
    )


def _own_project(db: Session, user, project_id: UUID) -> ProjectModel:
    p = db.query(ProjectModel).filter(
        ProjectModel.id == project_id,
        ProjectModel.client_id == user.client_id,
        ProjectModel.deleted_at.is_(None),
    ).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return p


# ---------- endpoints ----------

@router.get("/overview", response_model=PortalOverview)
def overview(db: Session = Depends(get_db), user: UserModel = Depends(get_portal_user)):
    client = db.query(ClientModel).filter(ClientModel.id == user.client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client account not found")
    projects = db.query(ProjectModel).filter(
        ProjectModel.client_id == user.client_id, ProjectModel.deleted_at.is_(None)
    ).order_by(ProjectModel.created_at.desc()).all()
    open_invoices = db.query(func.count(InvoiceModel.id)).filter(
        InvoiceModel.client_id == user.client_id, InvoiceModel.status.in_(["sent", "overdue"])
    ).scalar() or 0
    pending_quotes = db.query(func.count(QuoteModel.id)).filter(
        QuoteModel.client_id == user.client_id, QuoteModel.status == "sent"
    ).scalar() or 0
    pending_agreements = db.query(func.count(AgreementModel.id)).filter(
        AgreementModel.client_id == user.client_id, AgreementModel.status == "sent"
    ).scalar() or 0
    return PortalOverview(
        client_name=client.name,
        projects=[_project_summary(db, p) for p in projects],
        open_invoices=open_invoices,
        pending_quotes=pending_quotes,
        pending_agreements=pending_agreements,
    )


@router.get("/projects/{project_id}", response_model=PortalProjectDetail)
def project_detail(project_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_portal_user)):
    p = _own_project(db, user, project_id)
    summary = _project_summary(db, p)
    milestones = db.query(MilestoneModel).filter(MilestoneModel.project_id == p.id).order_by(
        MilestoneModel.position, MilestoneModel.due_date.nulls_last()
    ).all()
    pms = []
    for m in milestones:
        mt = db.query(func.count(TaskModel.id)).filter(TaskModel.milestone_id == m.id).scalar() or 0
        md = db.query(func.count(TaskModel.id)).filter(TaskModel.milestone_id == m.id, TaskModel.status == "done").scalar() or 0
        pms.append(PortalMilestone(
            name=m.name, due_date=str(m.due_date) if m.due_date else None,
            completed=m.completed_at is not None, task_total=mt, task_done=md,
        ))
    tasks = db.query(TaskModel).filter(TaskModel.project_id == p.id).order_by(
        TaskModel.status, TaskModel.order_index, TaskModel.created_at
    ).limit(200).all()
    return PortalProjectDetail(
        **summary.model_dump(),
        milestones=pms,
        tasks=[
            PortalTask(
                title=t.title, status=_client_status(t.status), item_type=t.item_type or "task",
                due_date=str(t.due_date) if t.due_date else None,
            )
            for t in tasks
        ],
    )


class PortalIssueCreated(BaseModel):
    id: UUID
    title: str
    status: str = "todo"


@router.post("/projects/{project_id}/issues", response_model=PortalIssueCreated, status_code=status.HTTP_201_CREATED)
def report_issue(
    project_id: UUID,
    data: IssueReport,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_portal_user),
):
    """Client-reported issue becomes a bug task on the project and notifies the project owner."""
    p = _own_project(db, user, project_id)
    if data.severity not in ("low", "medium", "high", "critical"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid severity")
    if not data.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title is required")
    # Land the report on the project's board so it shows up in the To do
    # column immediately; a project with no board yet gets one created.
    board = db.query(BoardModel).filter(BoardModel.project_id == p.id).order_by(
        BoardModel.position, BoardModel.created_at
    ).first()
    if not board:
        board = BoardModel(project_id=p.id, name=f"{p.name} board", created_by=p.owner_id)
        db.add(board)
        db.flush()
        if p.owner_id:
            db.add(BoardMemberModel(board_id=board.id, user_id=p.owner_id))
    max_order = db.query(func.coalesce(func.max(TaskModel.order_index), -1)).filter(
        TaskModel.board_id == board.id, TaskModel.status == "todo"
    ).scalar()
    task = TaskModel(
        project_id=p.id,
        board_id=board.id,
        order_index=(max_order if max_order is not None else -1) + 1,
        title=data.title.strip()[:255],
        description=(data.description or "").strip() or None,
        status="todo",
        item_type="bug",
        severity=data.severity,
        steps_to_reproduce=(data.steps_to_reproduce or "").strip() or None,
        environment="reported via client portal",
        created_by=user.id,
    )
    db.add(task)
    db.flush()
    tasks_updated_this_request.set(True)
    if p.owner_id:
        db.add(NotificationModel(
            user_id=p.owner_id,
            title="Client reported an issue",
            message=f'{user.full_name or user.email} reported on {p.name}: "{task.title}"',
            link=f"/tasks?highlight={task.id}",
            type="task",
            reference_id=None,
        ))
        notifications_updated_this_request.set(True)
        owner = db.query(UserModel).filter(UserModel.id == p.owner_id).first()
        if owner:
            email_service.send_notification(
                owner.email, "Client reported an issue",
                f'{user.full_name or user.email} reported an issue on {p.name}: "{task.title}"',
                f"/tasks?highlight={task.id}",
            )
    log_activity(db, user.id, "client_issue_reported", "task", task.id, details=f"Issue on {p.name}: {task.title}")
    db.commit()
    return PortalIssueCreated(id=task.id, title=task.title)


@router.get("/invoices", response_model=list[PortalInvoice])
def invoices(db: Session = Depends(get_db), user: UserModel = Depends(get_portal_user)):
    """Client's invoices — drafts stay internal until sent."""
    from app.api.v1.finance import paid_total_for, _apply_overdue
    rows = db.query(InvoiceModel).filter(
        InvoiceModel.client_id == user.client_id, InvoiceModel.status != "draft"
    ).order_by(InvoiceModel.created_at.desc()).all()
    _apply_overdue(db, rows)
    return [
        PortalInvoice(
            id=i.id, number=i.number, amount=i.amount, currency=i.currency, status=i.status,
            issued_at=str(i.issued_at) if i.issued_at else None,
            due_date=str(i.due_date) if i.due_date else None,
            paid_total=paid_total_for(db, i.id),
        )
        for i in rows
    ]


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_portal_user)):
    from fastapi.responses import Response
    from app.api.v1.finance import _invoice_pdf_bytes
    inv = db.query(InvoiceModel).filter(
        InvoiceModel.id == invoice_id, InvoiceModel.client_id == user.client_id, InvoiceModel.status != "draft"
    ).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return Response(
        content=_invoice_pdf_bytes(db, inv),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{inv.number}.pdf"'},
    )


def _own_visible_quote(db: Session, user, quote_id: UUID) -> QuoteModel:
    q = db.query(QuoteModel).options(joinedload(QuoteModel.items)).filter(
        QuoteModel.id == quote_id, QuoteModel.client_id == user.client_id, QuoteModel.status != "draft"
    ).first()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    return q


def _portal_quote(q: QuoteModel) -> PortalQuote:
    return PortalQuote(
        id=q.id, number=q.number, title=q.title, status=q.status, currency=q.currency,
        total=q.total, valid_until=str(q.valid_until) if q.valid_until else None, terms=q.terms,
        items=[
            PortalQuoteItem(
                description=i.description, quantity=i.quantity, unit_price=i.unit_price,
                line_total=(i.quantity * i.unit_price).quantize(Decimal("0.01")),
            )
            for i in q.items
        ],
    )


@router.get("/quotes", response_model=list[PortalQuote])
def quotes(db: Session = Depends(get_db), user: UserModel = Depends(get_portal_user)):
    from app.api.v1.quotes import _apply_expiry
    rows = db.query(QuoteModel).options(joinedload(QuoteModel.items)).filter(
        QuoteModel.client_id == user.client_id, QuoteModel.status != "draft"
    ).order_by(QuoteModel.created_at.desc()).all()
    _apply_expiry(db, rows)
    return [_portal_quote(q) for q in rows]


@router.get("/quotes/{quote_id}/pdf")
def quote_pdf(quote_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_portal_user)):
    from fastapi.responses import Response
    from app.services.pdf_service import build_quote_pdf
    q = _own_visible_quote(db, user, quote_id)
    return Response(
        content=build_quote_pdf(q),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{q.number}.pdf"'},
    )


def _decide_quote(db: Session, user, quote_id: UUID, accept: bool) -> QuoteModel:
    from app.api.v1.quotes import _apply_expiry, _notify_quote_creator
    q = _own_visible_quote(db, user, quote_id)
    _apply_expiry(db, [q])
    if q.status != "sent":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A {q.status} quote cannot be {'accepted' if accept else 'declined'}")
    if accept:
        q.status = "accepted"
        q.accepted_at = datetime.utcnow()
    else:
        q.status = "rejected"
    outcome = "accepted" if accept else "rejected"
    _notify_quote_creator(db, q, user, f"{outcome} by the client")
    log_activity(db, user.id, f"quote_{outcome}", "quote", q.id, details=f"Quote {q.number} {outcome} via client portal")
    db.commit()
    db.refresh(q)
    return q


@router.post("/quotes/{quote_id}/accept", response_model=PortalQuote)
def accept_quote(quote_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_portal_user)):
    return _portal_quote(_decide_quote(db, user, quote_id, accept=True))


@router.post("/quotes/{quote_id}/decline", response_model=PortalQuote)
def decline_quote(quote_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_portal_user)):
    return _portal_quote(_decide_quote(db, user, quote_id, accept=False))


# ---------- service agreements ----------

class PortalClause(BaseModel):
    heading: str
    body: str


class PortalAgreement(BaseModel):
    id: UUID
    number: str
    title: str
    status: str
    effective_date: Optional[str] = None
    valid_until: Optional[str] = None
    contract_value: Optional[Decimal] = None
    currency: str
    clauses: list[PortalClause] = []
    accepted_at: Optional[datetime] = None
    accepted_by_name: Optional[str] = None


class AgreementAcceptIn(BaseModel):
    signer_name: str


class AgreementDeclineIn(BaseModel):
    reason: Optional[str] = None


def _portal_agreement(a: AgreementModel) -> PortalAgreement:
    return PortalAgreement(
        id=a.id, number=a.number, title=a.title, status=a.status,
        effective_date=str(a.effective_date) if a.effective_date else None,
        valid_until=str(a.valid_until) if a.valid_until else None,
        contract_value=a.contract_value, currency=a.currency,
        clauses=[PortalClause(**c) for c in (a.clauses or [])],
        accepted_at=a.accepted_at, accepted_by_name=a.accepted_by_name,
    )


def _own_visible_agreement(db: Session, user, agreement_id: UUID) -> AgreementModel:
    a = db.query(AgreementModel).filter(
        AgreementModel.id == agreement_id,
        AgreementModel.client_id == user.client_id,
        AgreementModel.status != "draft",
    ).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agreement not found")
    return a


def _notify_agreement_creator(db: Session, a: AgreementModel, actor, outcome: str) -> None:
    if not a.created_by:
        return
    msg = f'Agreement {a.number} "{a.title}" was {outcome}'
    db.add(NotificationModel(user_id=a.created_by, title=f"Agreement update", message=msg, link="/agreements", type="agreement", reference_id=None))
    notifications_updated_this_request.set(True)
    creator = db.query(UserModel).filter(UserModel.id == a.created_by).first()
    if creator:
        email_service.send_notification(creator.email, "Agreement update", msg, "/agreements")


@router.get("/agreements", response_model=list[PortalAgreement])
def agreements(db: Session = Depends(get_db), user: UserModel = Depends(get_portal_user)):
    from app.api.v1.agreements import _apply_expiry as _agr_expiry
    rows = db.query(AgreementModel).filter(
        AgreementModel.client_id == user.client_id, AgreementModel.status != "draft"
    ).order_by(AgreementModel.created_at.desc()).all()
    _agr_expiry(db, rows)
    return [_portal_agreement(a) for a in rows]


@router.get("/agreements/{agreement_id}/pdf")
def agreement_pdf(agreement_id: UUID, db: Session = Depends(get_db), user: UserModel = Depends(get_portal_user)):
    from fastapi.responses import Response
    from app.services.pdf_service import build_agreement_pdf
    a = _own_visible_agreement(db, user, agreement_id)
    return Response(
        content=build_agreement_pdf(a),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{a.number}.pdf"'},
    )


@router.post("/agreements/{agreement_id}/accept", response_model=PortalAgreement)
def accept_agreement(
    agreement_id: UUID,
    data: AgreementAcceptIn,
    request: Request,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_portal_user),
):
    """Clickwrap acceptance: an affirmative action with a preserved record of
    who accepted, when, and from where — the legally meaningful artifact."""
    from app.api.v1.agreements import _apply_expiry as _agr_expiry
    a = _own_visible_agreement(db, user, agreement_id)
    _agr_expiry(db, [a])
    if a.status != "sent":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A {a.status} agreement cannot be accepted")
    signer = data.signer_name.strip()
    if not signer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please type your full name to sign")
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    a.status = "signed"
    a.accepted_at = datetime.utcnow()
    a.accepted_by_name = signer
    a.accepted_ip = (ip or "")[:64] or None
    a.acceptance_method = "portal"
    _notify_agreement_creator(db, a, user, f"signed by {signer} via the client portal")
    log_activity(db, user.id, "agreement_signed", "agreement", a.id, details=f"Agreement {a.number} signed by {signer} via client portal")
    db.commit()
    db.refresh(a)
    return _portal_agreement(a)


@router.post("/agreements/{agreement_id}/decline", response_model=PortalAgreement)
def decline_agreement(
    agreement_id: UUID,
    data: AgreementDeclineIn,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_portal_user),
):
    from app.api.v1.agreements import _apply_expiry as _agr_expiry
    a = _own_visible_agreement(db, user, agreement_id)
    _agr_expiry(db, [a])
    if a.status != "sent":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A {a.status} agreement cannot be declined")
    a.status = "declined"
    a.decline_reason = (data.reason or "").strip() or None
    _notify_agreement_creator(db, a, user, "declined by the client" + (f": {a.decline_reason}" if a.decline_reason else ""))
    log_activity(db, user.id, "agreement_declined", "agreement", a.id, details=f"Agreement {a.number} declined via client portal")
    db.commit()
    db.refresh(a)
    return _portal_agreement(a)


# Screenshots on client-reported issues. Portal users cannot touch the
# internal attachments API, so this is a narrow, heavily-guarded upload:
# only onto bug tasks the caller reported themselves, images only.
PORTAL_IMAGE_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "gif", "webp"})
PORTAL_MAX_ISSUE_ATTACHMENTS = 5


@router.post("/issues/{task_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_issue_attachment(
    task_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_portal_user),
):
    import os
    import secrets as _secrets
    from app.config import get_settings
    from app.models import Attachment as AttachmentModel

    task = db.query(TaskModel).join(ProjectModel, TaskModel.project_id == ProjectModel.id).filter(
        TaskModel.id == task_id,
        TaskModel.created_by == user.id,
        TaskModel.environment == "reported via client portal",
        ProjectModel.client_id == user.client_id,
        ProjectModel.deleted_at.is_(None),
    ).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    existing = db.query(func.count(AttachmentModel.id)).filter(
        AttachmentModel.entity_type == "task", AttachmentModel.entity_id == task.id
    ).scalar() or 0
    if existing >= PORTAL_MAX_ISSUE_ATTACHMENTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"At most {PORTAL_MAX_ISSUE_ATTACHMENTS} screenshots per issue")

    settings = get_settings()
    original = (file.filename or "image").strip().replace("\\", "/").split("/")[-1][:255] or "image"
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in PORTAL_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only images (png, jpg, gif, webp) can be attached to an issue")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File exceeds {settings.max_upload_mb} MB limit")

    stored_name = f"{_secrets.token_hex(16)}.{ext}"
    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(os.path.join(settings.upload_dir, stored_name), "wb") as f:
        f.write(content)
    att = AttachmentModel(
        entity_type="task",
        entity_id=task.id,
        filename=original,
        stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        uploaded_by=user.id,
    )
    db.add(att)
    log_activity(db, user.id, "client_issue_attachment", "task", task.id, details=f"Screenshot on issue: {original}")
    db.commit()
    return {"id": str(att.id), "filename": original}
