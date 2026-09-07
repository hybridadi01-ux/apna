from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import hashlib, os, secrets, uuid

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv(Path(__file__).parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./synapsedesk.db")
SECRET = os.getenv("JWT_SECRET", "dev-only-change-this-secret")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
security = HTTPBearer(auto_error=False)

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(String, primary_key=True); name = Column(String, nullable=False); slug = Column(String, unique=True, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True); organization_id = Column(String, ForeignKey("organizations.id"), index=True)
    name = Column(String, nullable=False); email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False); role = Column(String, nullable=False, default="requester"); active = Column(Boolean, default=True)

class Team(Base):
    __tablename__ = "teams"
    id = Column(String, primary_key=True); organization_id = Column(String, index=True); name = Column(String, nullable=False); color = Column(String, default="#2563eb")

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True); organization_id = Column(String, index=True); number = Column(String, index=True)
    title = Column(String, nullable=False); description = Column(Text, nullable=False); requester = Column(String, nullable=False); requester_email = Column(String, nullable=False)
    team = Column(String, default="IT Support"); assignee = Column(String, default="Unassigned"); status = Column(String, default="New", index=True)
    priority = Column(String, default="Medium", index=True); category = Column(String, default="General"); sla_status = Column(String, default="NORMAL")
    sla_deadline = Column(DateTime); tags = Column(String, default="support"); created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc)); updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Comment(Base):
    __tablename__ = "comments"
    id = Column(String, primary_key=True); organization_id = Column(String, index=True); ticket_id = Column(String, index=True); author = Column(String); content = Column(Text); comment_type = Column(String, default="public"); created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True); organization_id = Column(String, index=True); actor = Column(String); action = Column(String); entity = Column(String); entity_id = Column(String); detail = Column(Text); created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(String, primary_key=True); organization_id = Column(String, index=True); ticket_id = Column(String, index=True); filename = Column(String); path = Column(String); size = Column(Integer); created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)
app = FastAPI(title="SynapseDesk API", version="1.0.0", description="Lightweight multi-tenant ticket operations API", openapi_url="/api/openapi.json", docs_url="/api/docs", redoc_url="/api/redoc")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "*").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def db():
    session = SessionLocal()
    try: yield session
    finally: session.close()

def hash_password(password): return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def public_user(user): return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "organization_id": user.organization_id}
def token(user): return jwt.encode({"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET, algorithm="HS256")
def current_user(credentials: HTTPAuthorizationCredentials = Depends(security), session: Session = Depends(db)):
    if not credentials: raise HTTPException(401, "Authentication required")
    try: payload = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError: raise HTTPException(401, "Invalid or expired token")
    user = session.get(User, payload.get("sub"))
    if not user or not user.active: raise HTTPException(401, "User not found")
    return user
def require(*roles):
    def dependency(user=Depends(current_user)):
        if roles and user.role not in roles: raise HTTPException(403, "Insufficient permissions")
        return user
    return dependency
def iso(value): return value.isoformat() if value else None
def ticket_json(t, session):
    comments = session.query(Comment).filter_by(ticket_id=t.id, organization_id=t.organization_id).order_by(Comment.created_at).all()
    return {"id": t.id, "number": t.number, "title": t.title, "description": t.description, "requester": t.requester, "requester_email": t.requester_email, "team": t.team, "assignee": t.assignee, "status": t.status, "priority": t.priority, "category": t.category, "sla_status": t.sla_status, "sla_deadline": iso(t.sla_deadline), "tags": t.tags.split(","), "created_at": iso(t.created_at), "updated_at": iso(t.updated_at), "comments": [{"id": c.id, "author": c.author, "content": c.content, "comment_type": c.comment_type, "created_at": iso(c.created_at)} for c in comments]}
def audit(session, user, action, entity, entity_id, detail=""):
    session.add(AuditLog(id=str(uuid.uuid4()), organization_id=user.organization_id, actor=user.name, action=action, entity=entity, entity_id=entity_id, detail=detail))

class Login(BaseModel): email: str; password: str
class Register(Login): name: str; organization_name: str = "New Organization"
class TicketCreate(BaseModel): title: str; description: str; requester: str; requester_email: str; priority: str = "Medium"; team: str = "IT Support"; category: str = "General"; tags: list[str] = []
class TicketUpdate(BaseModel): status: Optional[str] = None; priority: Optional[str] = None; team: Optional[str] = None; assignee: Optional[str] = None
class CommentCreate(BaseModel): content: str; comment_type: str = "public"
class ActionRequest(BaseModel): action: str; update: Optional[str] = None

@app.get("/api/health")
def health(): return {"status": "ok", "service": "synapsedesk-api", "ai_provider": os.getenv("AI_PROVIDER", "none")}

@app.post("/api/auth/register")
def register(data: Register, session: Session = Depends(db)):
    email = data.email.lower().strip()
    if session.query(User).filter_by(email=email).first(): raise HTTPException(409, "Email already registered")
    org = Organization(id=str(uuid.uuid4()), name=data.organization_name, slug=f"{data.organization_name.lower().replace(' ', '-')}-{secrets.token_hex(2)}")
    user = User(id=str(uuid.uuid4()), organization_id=org.id, name=data.name, email=email, password_hash=hash_password(data.password), role="admin")
    session.add_all([org, user]); session.commit()
    return {"token": token(user), "user": public_user(user)}

@app.post("/api/auth/login")
def login(data: Login, session: Session = Depends(db)):
    user = session.query(User).filter_by(email=data.email.lower().strip()).first()
    if not user or not bcrypt.checkpw(data.password.encode(), user.password_hash.encode()): raise HTTPException(401, "Invalid email or password")
    return {"token": token(user), "user": public_user(user)}

@app.get("/api/auth/me")
def me(user=Depends(current_user)): return public_user(user)
@app.post("/api/auth/logout")
def logout(): return {"message": "Session ended"}

@app.get("/api/dashboard")
def dashboard(user=Depends(current_user), session: Session = Depends(db)):
    tickets = session.query(Ticket).all() if user.role == "superadmin" else session.query(Ticket).filter_by(organization_id=user.organization_id).all()
    mine = [t for t in tickets if t.assignee == user.name]
    return {"total": len(tickets), "open": sum(t.status not in ["Resolved", "Closed", "Cancelled"] for t in tickets), "critical": sum(t.priority == "Critical" for t in tickets), "at_risk": sum(t.sla_status == "AT_RISK" for t in tickets), "breached": sum(t.sla_status == "BREACHED" for t in tickets), "resolved": sum(t.status == "Resolved" for t in tickets), "mine": len(mine), "team_workload": [{"team": name, "count": sum(t.team == name for t in tickets)} for name in ["IT Support", "DevOps", "HR", "Finance"]]}

@app.get("/api/tickets")
def tickets(user=Depends(current_user), session: Session = Depends(db), status: Optional[str] = None):
    query = session.query(Ticket) if user.role == "superadmin" else session.query(Ticket).filter_by(organization_id=user.organization_id)
    if user.role == "requester": query = query.filter_by(requester_email=user.email)
    if status: query = query.filter_by(status=status)
    return [ticket_json(t, session) for t in query.order_by(Ticket.updated_at.desc()).all()]

@app.get("/api/my/tickets")
def my_tickets(user=Depends(current_user), session: Session = Depends(db)):
    """Requester-safe view: employees can only see tickets they submitted."""
    query = session.query(Ticket).filter_by(organization_id=user.organization_id, requester_email=user.email)
    return [ticket_json(t, session) for t in query.order_by(Ticket.updated_at.desc()).all()]

@app.post("/api/tickets")
def create_ticket(data: TicketCreate, user=Depends(current_user), session: Session = Depends(db)):
    count = session.query(Ticket).filter_by(organization_id=user.organization_id).count() + 100001
    now = datetime.now(timezone.utc); deadline = now + timedelta(hours={"Critical": 4, "High": 8, "Medium": 24, "Low": 48}.get(data.priority, 24))
    t = Ticket(id=str(uuid.uuid4()), organization_id=user.organization_id, number=f"TCK-{count}", title=data.title, description=data.description, requester=data.requester, requester_email=data.requester_email, priority=data.priority, team=data.team, category=data.category, tags=",".join(data.tags or ["support"]), sla_deadline=deadline)
    session.add(t); audit(session, user, "ticket.created", "ticket", t.id, t.number); session.commit(); return ticket_json(t, session)

@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: str, user=Depends(current_user), session: Session = Depends(db)):
    t = session.query(Ticket).filter_by(id=ticket_id).first() if user.role == "superadmin" else session.query(Ticket).filter_by(id=ticket_id, organization_id=user.organization_id).first()
    if user.role == "requester" and (not t or t.requester_email != user.email): t = None
    if not t: raise HTTPException(404, "Ticket not found")
    return ticket_json(t, session)

@app.patch("/api/tickets/{ticket_id}")
def update_ticket(ticket_id: str, data: TicketUpdate, user=Depends(current_user), session: Session = Depends(db)):
    t = session.query(Ticket).filter_by(id=ticket_id).first() if user.role == "superadmin" else session.query(Ticket).filter_by(id=ticket_id, organization_id=user.organization_id).first()
    if user.role == "requester" and (not t or t.requester_email != user.email): t = None
    if not t: raise HTTPException(404, "Ticket not found")
    changes = data.model_dump(exclude_none=True)
    for key, value in changes.items(): setattr(t, key, value)
    t.updated_at = datetime.now(timezone.utc); audit(session, user, "ticket.updated", "ticket", t.id, str(changes)); session.commit(); return ticket_json(t, session)

@app.post("/api/my/tickets/{ticket_id}/confirm-resolution")
def confirm_resolution(ticket_id: str, user=Depends(current_user), session: Session = Depends(db)):
    t = session.query(Ticket).filter_by(id=ticket_id, organization_id=user.organization_id, requester_email=user.email).first()
    if not t: raise HTTPException(404, "Ticket not found")
    t.status = "Closed"; t.updated_at = datetime.now(timezone.utc); audit(session, user, "ticket.confirmed_resolved", "ticket", t.id); session.commit(); return ticket_json(t, session)

@app.post("/api/my/tickets/{ticket_id}/reopen")
def reopen_ticket(ticket_id: str, user=Depends(current_user), session: Session = Depends(db)):
    t = session.query(Ticket).filter_by(id=ticket_id, organization_id=user.organization_id, requester_email=user.email).first()
    if not t: raise HTTPException(404, "Ticket not found")
    t.status = "Open"; t.updated_at = datetime.now(timezone.utc); audit(session, user, "ticket.reopened", "ticket", t.id); session.commit(); return ticket_json(t, session)

@app.post("/api/tickets/{ticket_id}/comments")
def comment(ticket_id: str, data: CommentCreate, user=Depends(current_user), session: Session = Depends(db)):
    t = session.query(Ticket).filter_by(id=ticket_id).first() if user.role == "superadmin" else session.query(Ticket).filter_by(id=ticket_id, organization_id=user.organization_id).first()
    if user.role == "requester" and (not t or t.requester_email != user.email): t = None
    if not t: raise HTTPException(404, "Ticket not found")
    c = Comment(id=str(uuid.uuid4()), organization_id=user.organization_id, ticket_id=t.id, author=user.name, content=data.content, comment_type=data.comment_type)
    session.add(c); audit(session, user, "comment.added", "ticket", t.id); session.commit(); return {"id": c.id, "author": c.author, "content": c.content, "comment_type": c.comment_type, "created_at": iso(c.created_at)}

@app.get("/api/teams")
def teams(user=Depends(current_user), session: Session = Depends(db)): return [{"id": x.id, "name": x.name, "color": x.color, "organization_id": x.organization_id} for x in (session.query(Team).all() if user.role == "superadmin" else session.query(Team).filter_by(organization_id=user.organization_id).all())]
@app.get("/api/users")
def users(user=Depends(require("superadmin", "admin")), session: Session = Depends(db)): return [public_user(x) for x in (session.query(User).all() if user.role == "superadmin" else session.query(User).filter_by(organization_id=user.organization_id).all())]
@app.get("/api/audit")
def audit_logs(user=Depends(require("superadmin", "admin")), session: Session = Depends(db)): return [{"id": x.id, "actor": x.actor, "action": x.action, "entity": x.entity, "detail": x.detail, "created_at": iso(x.created_at)} for x in (session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all() if user.role == "superadmin" else session.query(AuditLog).filter_by(organization_id=user.organization_id).order_by(AuditLog.created_at.desc()).limit(100).all())]

@app.get("/api/platform/organizations")
def organizations(user=Depends(require("superadmin")), session: Session = Depends(db)):
    return [{"id": x.id, "name": x.name, "slug": x.slug, "users": session.query(User).filter_by(organization_id=x.id).count(), "tickets": session.query(Ticket).filter_by(organization_id=x.id).count()} for x in session.query(Organization).all()]

@app.get("/api/integrations/teams/card/{ticket_id}")
def teams_card(ticket_id: str, user=Depends(require("admin", "manager", "agent")), session: Session = Depends(db)):
    """Credential-free card contract. Delivery requires Azure Bot credentials."""
    t = session.query(Ticket).filter_by(id=ticket_id, organization_id=user.organization_id).first()
    if not t: raise HTTPException(404, "Ticket not found")
    return {"integration": "microsoft_teams", "mode": "not_configured", "card": {"type": "AdaptiveCard", "version": "1.4", "body": [{"type": "TextBlock", "text": f"{t.number} · {t.title}", "weight": "Bolder"}, {"type": "FactSet", "facts": [{"title": "Priority", "value": t.priority}, {"title": "Status", "value": t.status}, {"title": "SLA", "value": t.sla_status}]}], "actions": [{"type": "Action.Execute", "title": action, "verb": "ticket_action", "data": {"ticket_id": t.id, "action": action}} for action in ["Acknowledge", "Working", "Waiting", "Resolved", "Add Update"]]}}

@app.post("/api/integrations/teams/action")
def teams_action(data: ActionRequest, user=Depends(require("admin", "manager", "agent"))):
    """Integration contract; real requests must arrive through verified Bot Framework JWT."""
    return {"ok": False, "integration": "microsoft_teams", "mode": "not_configured", "message": "Add Azure Bot credentials and enable /api/messages before accepting Teams actions."}

@app.post("/api/ai/analyze/{ticket_id}")
def ai_analyze(ticket_id: str, user=Depends(current_user), session: Session = Depends(db)):
    t = session.query(Ticket).filter_by(id=ticket_id, organization_id=user.organization_id).first()
    if not t: raise HTTPException(404, "Ticket not found")
    return {"enabled": False, "provider": os.getenv("AI_PROVIDER", "none"), "ticket_id": t.id, "message": "AI_PROVIDER=none. Configure an OpenAI-compatible provider to enable classification."}

@app.post("/api/ai/actions")
def ai_actions(data: ActionRequest, user=Depends(current_user)):
    return {"enabled": False, "authorized": False, "message": "AI action tools are defined but disabled until a provider and policy are configured."}

@app.get("/api/voice/status")
def voice_status():
    return {"enabled": False, "provider": os.getenv("VOICE_PROVIDER", "none"), "message": "Voice architecture is reserved for a verified Teams/ACS calling configuration."}
@app.post("/api/tickets/{ticket_id}/attachments")
async def upload(ticket_id: str, file: UploadFile = File(...), user=Depends(current_user), session: Session = Depends(db)):
    t = session.query(Ticket).filter_by(id=ticket_id, organization_id=user.organization_id).first()
    if not t: raise HTTPException(404, "Ticket not found")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024: raise HTTPException(413, "Attachment exceeds 10MB")
    folder = Path(os.getenv("STORAGE_PATH", "./uploads")); folder.mkdir(exist_ok=True); safe = f"{uuid.uuid4()}-{Path(file.filename or 'file').name}"; (folder / safe).write_bytes(data)
    a = Attachment(id=str(uuid.uuid4()), organization_id=user.organization_id, ticket_id=t.id, filename=file.filename, path=str(folder / safe), size=len(data)); session.add(a); audit(session, user, "attachment.uploaded", "ticket", t.id, file.filename); session.commit(); return {"id": a.id, "filename": a.filename, "size": a.size}

def seed():
    session = SessionLocal()
    existing_superadmin = session.query(User).filter_by(email="agent@acme.test").first()
    if existing_superadmin and existing_superadmin.role != "superadmin":
        existing_superadmin.role = "superadmin"; session.commit()
    if session.query(User).count(): session.close(); return
    org = Organization(id="org-acme", name="Acme Technologies", slug="acme-technologies"); session.add(org)
    for name, color in [("IT Support", "#2563eb"), ("DevOps", "#10b981"), ("HR", "#f59e0b"), ("Finance", "#ef4444")]: session.add(Team(id=str(uuid.uuid4()), organization_id=org.id, name=name, color=color))
    users = [("Olivia Chen", "admin@acme.test", "admin"), ("Marcus Reed", "agent@acme.test", "superadmin"), ("Jamie Patel", "requester@acme.test", "requester")]
    for name, email, role in users: session.add(User(id=str(uuid.uuid4()), organization_id=org.id, name=name, email=email, password_hash=hash_password("Synapse123!"), role=role))
    session.commit(); admin = session.query(User).filter_by(email="admin@acme.test").first()
    for i, (title, priority, status, team, sla) in enumerate([("Production API returning 503s", "Critical", "In Progress", "DevOps", "AT_RISK"), ("New starter laptop request", "Medium", "Open", "IT Support", "NORMAL"), ("Payroll export access", "High", "Waiting for Internal Team", "Finance", "BREACHED"), ("VPN access for contractor", "Low", "Resolved", "IT Support", "NORMAL")]):
        t = Ticket(id=str(uuid.uuid4()), organization_id=org.id, number=f"TCK-{100001+i}", title=title, description="Sample operational request for the Acme workspace.", requester="Jamie Patel", requester_email="requester@acme.test", priority=priority, status=status, team=team, sla_status=sla, sla_deadline=datetime.now(timezone.utc)+timedelta(hours=12)); session.add(t); audit(session, admin, "ticket.created", "ticket", t.id, t.number)
    session.commit(); session.close()
seed()