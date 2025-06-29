"""
Golf Pickem League - FastHTML Web Application
Simplified main application with inline imports to avoid module issues.
"""
from fasthtml.common import *
from starlette.responses import RedirectResponse
from pathlib import Path
import os
import hashlib
import secrets
import smtplib
import inspect
from datetime import datetime

# Configuration settings (inline instead of separate config module)
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "data" / "golf_pickem.db"
APP_NAME = "Golf Pickem League"
HOST = "localhost"
PORT = 5001
DEBUG = False
RELOAD = False

# Database setup (inline instead of separate backend module)
db = database(DATABASE_PATH)

tournaments = db.t.tournaments
picks = db.t.picks
golfers = db.t.golfers
tournament_golfers = db.t.tournament_golfers
tournament_leaderboard = db.t.tournament_leaderboard
pickem_leaderboard = db.t.pickem_leaderboard
users = db.t.users
sessions = db.t.sessions

# Create tables if they don't exist
if tournaments not in db.t:
    tournaments.create(id=int, name=str, current=bool, allow_submissions=bool, created_at=str, pk='id')
Tournament = tournaments.dataclass()

if picks not in db.t:
    picks.create(id=int, pickname=str, tier1_pick=str, tier2_pick=str, tier3_pick=str, tier4_pick=str, tournament_id=int, created_at=str, pk='id')
Pick = picks.dataclass()

if golfers not in db.t:
    golfers.create(id=int, name=str, created_at=str, pk='id')
Golfer = golfers.dataclass()

if tournament_golfers not in db.t:
    tournament_golfers.create(id=int, tournament=str, player_name=str, tier=str, created_at=str, pk='id')
TournamentGolfers = tournament_golfers.dataclass()

if tournament_leaderboard not in db.t:
    tournament_leaderboard.create(id=int, tournament=str, player_name=str, round=str, strokes=int, score=str, updated_at=str, pk='id')
TournamentLeaderboard = tournament_leaderboard.dataclass()

if pickem_leaderboard not in db.t:
    pickem_leaderboard.create(id=int, pickname=str, tier1_pick=str, tier1_score=str, tier1_strokes=int, tier2_pick=str, tier2_score=str, tier2_strokes=int, tier3_pick=str, tier3_score=str, tier3_strokes=int, tier4_pick=str, tier4_score=str, tier4_strokes=int, total_score=int, updated_at=str, pk='id')
PickemLeaderboard = pickem_leaderboard.dataclass()

# User authentication tables
users = db.t.users
sessions = db.t.sessions
password_resets = db.t.password_resets

if users not in db.t:
    users.create(id=int, username=str, email=str, password_hash=str, first_name=str, last_name=str, is_admin=bool, is_active=bool, created_at=str, updated_at=str, pk='id')
User = users.dataclass()

if sessions not in db.t:
    sessions.create(id=int, user_id=int, session_token=str, created_at=str, expires_at=str, pk='id')
Session = sessions.dataclass()

if password_resets not in db.t:
    password_resets.create(id=int, user_id=int, reset_token=str, created_at=str, expires_at=str, used=bool, pk='id')
PasswordReset = password_resets.dataclass()

# Authentication helpers
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = secrets.token_hex(16)
    return hashlib.sha256((password + salt).encode()).hexdigest() + ':' + salt

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    if ':' not in hashed:
        # Legacy hash without salt - for backward compatibility
        return hashlib.sha256(password.encode()).hexdigest() == hashed
    
    stored_hash, salt = hashed.split(':')
    return hashlib.sha256((password + salt).encode()).hexdigest() == stored_hash

def generate_session_token() -> str:
    """Generate secure session token"""
    return secrets.token_urlsafe(32)

def generate_reset_token() -> str:
    """Generate secure password reset token"""
    return secrets.token_urlsafe(32)

def create_session(user_id: int) -> str:
    """Create new session for user"""
    try:
        token = generate_session_token()
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        
        session_id = sessions.insert(
            user_id=user_id, 
            session_token=token, 
            created_at=datetime.now().isoformat(), 
            expires_at=expires_at
        )
        
        return token
    except Exception as e:
        # Log error but don't expose details to user
        raise e

def create_password_reset(user_id: int) -> str:
    """Create password reset token"""
    try:
        token = generate_reset_token()
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        
        # Invalidate any existing reset tokens for this user
        existing_resets = password_resets(where=f"user_id={user_id} AND used=0")
        for reset in existing_resets:
            password_resets.update(reset.id, used=True)
        
        reset_id = password_resets.insert(
            user_id=user_id,
            reset_token=token,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at,
            used=False
        )
        
        return token
    except Exception as e:
        raise e

def validate_reset_token(token: str) -> int:
    """Validate reset token and return user_id if valid"""
    try:
        reset_list = password_resets(where=f"reset_token='{token}' AND used=0")
        if not reset_list:
            return None
        
        reset = reset_list[0]
        if datetime.fromisoformat(reset.expires_at) < datetime.now():
            return None
        
        return reset.user_id
    except Exception as e:
        return None

def use_reset_token(token: str) -> bool:
    """Mark reset token as used"""
    try:
        reset_list = password_resets(where=f"reset_token='{token}' AND used=0")
        if not reset_list:
            return False
        
        reset = reset_list[0]
        password_resets.update(reset.id, used=True)
        return True
    except Exception as e:
        return False

def get_current_user(request):
    """Get current user from session"""
    session_token = request.cookies.get('session_token')
    if not session_token:
        return None
    
    # Find valid session
    try:
        session_list = sessions(where=f"session_token='{session_token}'")
        if not session_list:
            return None
        
        session = session_list[0]
        if datetime.fromisoformat(session.expires_at) < datetime.now():
            # Session expired, clean up
            sessions.delete(session.id)
            return None
        
        # Get user
        user = users[session.user_id]
        if not user.is_active:
            return None
        return user
    except Exception as e:
        return None

def require_auth(func):
    """Decorator to require authentication"""
    import inspect
    
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return RedirectResponse('/login')
        
        # Get function signature to determine how many parameters it expects
        sig = inspect.signature(func)
        param_count = len(sig.parameters)
        
        if param_count == 2:  # request, user
            return func(request, user)
        else:  # request, user, + additional parameters
            return func(request, user, *args, **kwargs)
    return wrapper

def require_admin(func):
    """Decorator to require admin privileges"""
    import inspect
    
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return RedirectResponse('/login')
        if not user.is_admin:
            return Titled("Access Denied",
                Div(
                    H1("Access Denied"),
                    P("You need administrator privileges to access this page."),
                    A("← Back to Home", href="/", class_="btn btn-primary"),
                    style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                )
            )
        
        # Get function signature to determine how many parameters it expects
        sig = inspect.signature(func)
        param_count = len(sig.parameters)
        
        if param_count == 2:  # request, user
            return func(request, user)
        else:  # request, user, + additional parameters
            return func(request, user, *args, **kwargs)
    return wrapper

# Utility functions (inline instead of separate utils module)
def get_current_tournament():
    """Get the currently active tournament."""
    try:
        return tournaments(where="current=1")[0]
    except IndexError:
        return None

def get_open_tournament():
    """Get the tournament currently accepting submissions."""
    try:
        return tournaments(where="allow_submissions=1")[0]
    except IndexError:
        return None

def validate_pick_data(pick: Pick):
    """Validate pick data and return list of errors."""
    errors = []
    if not pick.pickname or len(pick.pickname.strip()) < 1:
        errors.append('Pick name is required')
    if not pick.tier1_pick or 'Select' in pick.tier1_pick:
        errors.append('Tier 1 pick is required')
    if not pick.tier2_pick or 'Select' in pick.tier2_pick:
        errors.append('Tier 2 pick is required')
    if not pick.tier3_pick or 'Select' in pick.tier3_pick:
        errors.append('Tier 3 pick is required')
    if not pick.tier4_pick or 'Select' in pick.tier4_pick:
        errors.append('Tier 4 pick is required')
    return errors

def validate_tournament_data(tournament: Tournament):
    """Validate tournament data and return list of errors."""
    errors = []
    if not tournament.name or len(tournament.name.strip()) < 1:
        errors.append('Tournament name is required')
    return errors

def get_formatted_datetime():
    """Get current datetime as formatted string."""
    return datetime.now().isoformat()

def get_golfers_by_tier(tier: str):
    """Get all golfers for a specific tier."""
    return list(tournament_golfers(where=f"tier='{tier}'"))

# UI Components (inline instead of separate frontend module)
def page_header():
    """Create a consistent page header."""
    return Header(
        Grid(
            H1(APP_NAME, style="margin: 0; color: #2c3e50;"),
            Nav(
                Button("Pick'em", hx_get='/picks', hx_target="#main-content", hx_swap="innerHTML"),
                Button('Tournaments', hx_get='/tournaments', hx_target="#main-content", hx_swap="innerHTML"),
                Button('Field', hx_get='/tournament_golfers', hx_target="#main-content", hx_swap="innerHTML"), 
                Button('Pickem Leaderboard', hx_get='/pickem_leaderboard', hx_target="#main-content", hx_swap="innerHTML"),
                Button('Tournament Leaderboard', hx_get='/tournament_leaderboard', hx_target="#main-content", hx_swap="innerHTML"),
                style="display: flex; gap: 0.5rem; align-items: center;"
            ),
            style="align-items: center;"
        ),
        style="padding: 1rem; border-bottom: 2px solid #ecf0f1; margin-bottom: 2rem;"
    )

def error_message(message: str):
    """Create an error message component."""
    return Div(
        Strong("Error: "), message,
        style="background-color: #ffe6e6; color: #c62828; padding: 1rem; border-radius: 4px; margin: 1rem 0; border-left: 4px solid #c62828;"
    )

def success_message(message: str):
    """Create a success message component."""
    return Div(
        Strong("Success: "), message,
        style="background-color: #e8f5e8; color: #2e7d32; padding: 1rem; border-radius: 4px; margin: 1rem 0; border-left: 4px solid #2e7d32;"
    )

# Create FastHTML app
css_link = Link(rel="stylesheet", href="/static/enhanced-style.css")
app, rt = fast_app(live=RELOAD, hdrs=(css_link,))

# Static file serving
@rt("/{fname:path}.{ext:static}")
async def serve_static(fname: str, ext: str):
    return FileResponse(f'static/{fname}.{ext}')

# Patch methods for database models to render as HTML
@patch
def __ft__(self: Pick):
    pid = f'pick-{self.id}'
    return Tr(
        Td(self.pickname), 
        Td(self.tier1_pick), 
        Td(self.tier2_pick), 
        Td(self.tier3_pick), 
        Td(self.tier4_pick),
        Td(
            Button(
                'Delete', 
                hx_delete=f'/picks/{self.id}', 
                hx_swap='outerHTML',
                hx_target=f'#{pid}',
                hx_confirm='Are you sure you want to delete this pick?',
                style='background-color: #e74c3c; border-color: #e74c3c; color: white;'
            )
        ),
        id=pid
    )

@patch
def __ft__(self: Tournament):
    tid = f'tournament-{self.id}'
    return Tr(
        Td(self.name), 
        Td("✅ Yes" if self.current else "❌ No"), 
        Td("✅ Open" if self.allow_submissions else "❌ Closed"),
        Td(
            Button(
                'Delete', 
                hx_delete=f'/tournaments/{self.id}', 
                hx_swap='outerHTML',
                hx_target=f'#{tid}',
                hx_confirm='Are you sure you want to delete this tournament?',
                style='background-color: #e74c3c; border-color: #e74c3c; color: white;'
            )
        ), 
        Td(
            Button(
                'Set Not Current' if self.current else 'Set Current', 
                hx_patch=f'/tournaments/{self.id}/current', 
                hx_swap='outerHTML',
                hx_target=f'#{tid}',
                style='background-color: #27ae60; border-color: #27ae60; color: white;'
            )
        ),
        Td(
            Button(
                'Close Submissions' if self.allow_submissions else 'Open Submissions', 
                hx_patch=f'/tournaments/{self.id}/submissions', 
                hx_swap='outerHTML',
                hx_target=f'#{tid}',
                style='background-color: #f39c12; border-color: #f39c12; color: white;'
            )
        ),
        id=tid
    )

@patch
def __ft__(self: TournamentGolfers):
    tid = f'tournament_golfers-{self.id}'
    return Tr(
        Td(self.player_name), 
        Td(f"Tier {self.tier}"), 
        Td(
            Div(
                Button('T1', hx_patch=f'/tournament_golfers/{self.id}/tier1', hx_swap='outerHTML', hx_target=f'#{tid}', style='margin: 0.1rem; background-color: #3498db; border-color: #3498db; color: white;'),
                Button('T2', hx_patch=f'/tournament_golfers/{self.id}/tier2', hx_swap='outerHTML', hx_target=f'#{tid}', style='margin: 0.1rem; background-color: #3498db; border-color: #3498db; color: white;'),
                Button('T3', hx_patch=f'/tournament_golfers/{self.id}/tier3', hx_swap='outerHTML', hx_target=f'#{tid}', style='margin: 0.1rem; background-color: #3498db; border-color: #3498db; color: white;'),
                Button('T4', hx_patch=f'/tournament_golfers/{self.id}/tier4', hx_swap='outerHTML', hx_target=f'#{tid}', style='margin: 0.1rem; background-color: #3498db; border-color: #3498db; color: white;'),
                style="display: flex; gap: 0.25rem;"
            )
        ),
        id=tid
    )

@patch
def __ft__(self: TournamentLeaderboard):
    return Tr(Td(self.player_name), Td(self.round), Td(self.score))

@patch
def __ft__(self: PickemLeaderboard):
    return Tr(
        Td(self.pickname), 
        Td(f"{self.tier1_pick} ({self.tier1_score})"), 
        Td(f"{self.tier2_pick} ({self.tier2_score})"),
        Td(f"{self.tier3_pick} ({self.tier3_score})"), 
        Td(f"{self.tier4_pick} ({self.tier4_score})"),
        Td(Strong(str(self.total_score)))
    )

# Routes
@app.get("/")
def home(request):
    user = get_current_user(request)
    
    if user:
        # Logged in user view
        welcome_name = f"{user.first_name} {user.last_name}" if user.first_name else user.username
        
        return Titled("Golf Pickem League",
            Div(
                # Header with user info and logout
                Div(
                    Div(
                        H1("🏌️ Golf Pickem League", style="margin: 0; color: #2c5282;"),
                        Div(
                            Span(f"Logged in as: ", style="color: #666; font-size: 14px;"),
                            Strong(f"{welcome_name}", style="color: #2c5282; margin-right: 10px;"),
                            Span(f"({'Admin' if user.is_admin else 'User'})", 
                                 style=f"color: {'#d69e2e' if user.is_admin else '#666'}; font-size: 12px; background: {'#fef5e7' if user.is_admin else '#f8f9fa'}; padding: 2px 6px; border-radius: 12px; margin-right: 15px;"),
                            A("Profile", href="/profile", class_="btn btn-sm btn-outline", style="margin-right: 8px; font-size: 12px; padding: 4px 12px;"),
                            A("Logout", href="/logout", class_="btn btn-sm btn-danger", style="font-size: 12px; padding: 4px 12px;"),
                            style="display: flex; align-items: center; flex-wrap: wrap;"
                        ),
                        style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;"
                    ),
                    style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
                ),
                
                # Welcome section
                Div(
                    P(f"Welcome back, {welcome_name}! 👋", style="font-size: 20px; color: #2c5282; margin: 0 0 10px 0; font-weight: 600;"),
                    P("Make your tournament picks and compete with friends.", style="color: #666; margin: 0;"),
                    style="margin-bottom: 25px;"
                ),
                
                # Main actions
                Div(
                    H3("⛳ Golf Actions", style="color: #2c5282; margin-bottom: 15px;"),
                    Div(
                        A("🎯 Make Your Picks", href="/picks", class_="btn btn-primary", style="margin-right: 10px; margin-bottom: 10px;"),
                        A("🏆 View Tournaments", href="/tournaments", class_="btn btn-secondary", style="margin-right: 10px; margin-bottom: 10px;"),
                        A("👥 Tournament Field", href="/field", class_="btn btn-secondary", style="margin-right: 10px; margin-bottom: 10px;"),
                        A("📊 Leaderboards", href="/leaderboards", class_="btn btn-secondary", style="margin-bottom: 10px;"),
                        style="display: flex; flex-wrap: wrap; gap: 5px;"
                    ),
                    style="margin-bottom: 30px;"
                ),
                
                # Admin panel (only show if user is admin)
                Div(
                    H3("⚙️ Admin Panel", style="color: #d69e2e; margin-bottom: 15px;"),
                    Div(
                        A("👤 User Management", href="/admin/users", class_="btn btn-warning", style="margin-right: 10px; margin-bottom: 10px;"),
                        A("🏌️ Tournament Admin", href="/admin/tournaments", class_="btn btn-warning", style="margin-bottom: 10px;"),
                        style="display: flex; flex-wrap: wrap; gap: 5px;"
                    ),
                    P("🔐 Administrator privileges enabled", style="color: #d69e2e; font-size: 14px; margin-top: 10px;"),
                    style="background: #fef5e7; padding: 20px; border-radius: 8px; border-left: 4px solid #d69e2e;"
                ) if user.is_admin else "",
                
                # Quick tips
                Div(
                    P("💡 Start by checking out the current tournaments and making your picks!", style="color: #666; font-style: italic;")
                )
            )
        )
    else:
        # Guest user view (not logged in)
        return Titled("Golf Pickem League",
            Div(
                # Header for guests
                Div(
                    H1("🏌️ Golf Pickem League", style="text-align: center; color: #2c5282; margin-bottom: 10px;"),
                    P("Welcome to the Golf Pickem League! Make your tournament picks and compete with friends.", 
                      style="text-align: center; color: #666; font-size: 18px;"),
                    style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 30px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
                ),
                
                # Login/Register section
                Div(
                    H3("🔐 Get Started", style="color: #2c5282; margin-bottom: 15px; text-align: center;"),
                    Div(
                        A("🚀 Login", href="/login", class_="btn btn-primary", style="margin-right: 15px; padding: 12px 24px; font-size: 16px;"),
                        A("📝 Register", href="/register", class_="btn btn-success", style="padding: 12px 24px; font-size: 16px;"),
                        style="text-align: center; margin-bottom: 20px;"
                    ),
                    P("New here? Register to create your account and start picking!", 
                      style="text-align: center; color: #666; font-size: 14px;"),
                    style="margin-bottom: 30px;"
                ),
                
                Hr(style="margin: 30px 0; border-color: #e9ecef;"),
                
                # Guest browsing section
                Div(
                    H3("👁️ Browse as Guest", style="color: #6c757d; margin-bottom: 15px; text-align: center;"),
                    Div(
                        A("🏆 View Tournaments", href="/tournaments", class_="btn btn-outline", style="margin-right: 10px; margin-bottom: 10px;"),
                        A("👥 Tournament Field", href="/field", class_="btn btn-outline", style="margin-right: 10px; margin-bottom: 10px;"),
                        A("📊 Leaderboards", href="/leaderboards", class_="btn btn-outline", style="margin-bottom: 10px;"),
                        style="text-align: center; display: flex; flex-wrap: wrap; justify-content: center; gap: 5px;"
                    ),
                    P("⚠️ To make picks and participate fully, please login or register above.", 
                      style="text-align: center; color: #dc3545; font-size: 14px; margin-top: 15px; font-weight: 500;")
                )
            )
        )

# Authentication Routes
@app.get("/login")
def login_page():
    return Titled("Login - Golf Pickem League",
        Div(
            H1("Login"),
            Form(
                Div(
                    Label("Username:", for_="username"),
                    Input(id="username", name="username", type="text", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Password:", for_="password"),
                    Input(id="password", name="password", type="password", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Button("Login", type="submit", class_="btn btn-primary", style="margin-right: 10px;"),
                A("Register", href="/register", class_="btn btn-secondary"),
                action="/auth/login", method="post",
                style="max-width: 400px; margin: 0 auto;"
            ),
            Div(
                A("Forgot Password?", href="/forgot-password", style="color: #007bff; text-decoration: none;"),
                style="text-align: center; margin-top: 15px;"
            ),
            A("← Back to Home", href="/", style="display: block; margin-top: 20px; text-align: center;"),
            style="max-width: 500px; margin: 0 auto; padding: 20px;"
        )
    )

@app.get("/register")
def register_page():
    return Titled("Register - Golf Pickem League",
        Div(
            H1("Register"),
            Form(
                Div(
                    Label("First Name:", for_="first_name"),
                    Input(id="first_name", name="first_name", type="text", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Last Name:", for_="last_name"),
                    Input(id="last_name", name="last_name", type="text", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Username:", for_="username"),
                    Input(id="username", name="username", type="text", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Email:", for_="email"),
                    Input(id="email", name="email", type="email", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Password:", for_="password"),
                    Input(id="password", name="password", type="password", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Confirm Password:", for_="confirm_password"),
                    Input(id="confirm_password", name="confirm_password", type="password", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Button("Register", type="submit", class_="btn btn-primary", style="margin-right: 10px;"),
                A("Login", href="/login", class_="btn btn-secondary"),
                action="/auth/register", method="post",
                style="max-width: 400px; margin: 0 auto;"
            ),
            A("← Back to Home", href="/", style="display: block; margin-top: 20px; text-align: center;"),
            style="max-width: 500px; margin: 0 auto; padding: 20px;"
        )
    )

@app.post("/auth/register")
def register(first_name: str, last_name: str, username: str, email: str, password: str, confirm_password: str):
    # Validation
    if password != confirm_password:
        return Titled("Registration Error",
            Div(
                H1("Registration Failed"),
                P("Passwords do not match.", style="color: red;"),
                A("← Try Again", href="/register", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )
    
    if len(password) < 8:
        return Titled("Registration Error",
            Div(
                H1("Registration Failed"),
                P("Password must be at least 8 characters long.", style="color: red;"),
                A("← Try Again", href="/register", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )
    
    # Check if username or email already exists
    try:
        existing_user = users(where=f"username='{username}'")
        if existing_user:
            return Titled("Registration Error",
                Div(
                    H1("Registration Failed"),
                    P("Username already exists.", style="color: red;"),
                    A("← Try Again", href="/register", class_="btn btn-secondary"),
                    style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                )
            )
    except Exception as e:
        pass  # Username doesn't exist, which is good
    
    try:
        existing_email = users(where=f"email='{email}'")
        if existing_email:
            return Titled("Registration Error",
                Div(
                    H1("Registration Failed"),
                    P("Email already exists.", style="color: red;"),
                    A("← Try Again", href="/register", class_="btn btn-secondary"),
                    style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                )
            )
    except Exception as e:
        pass  # Email doesn't exist, which is good
    
    try:
        # Create user
        password_hash = hash_password(password)
        current_time = datetime.now().isoformat()
        
        # Check if this is the first user (make them admin)
        existing_users = users()
        is_first_user = len(existing_users) == 0
        
        new_user = users.insert(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            password_hash=password_hash,
            is_admin=is_first_user,  # First user becomes admin
            is_active=True,
            created_at=current_time,
            updated_at=current_time
        )
        
        # Extract the user ID from the returned User object
        user_id = new_user.id
        
        # Create session and set cookie
        session_token = create_session(user_id)
        
        response = RedirectResponse('/', status_code=302)
        response.set_cookie('session_token', session_token, max_age=30*24*60*60)  # 30 days
        return response
        
    except Exception as e:
        return Titled("Registration Error",
            Div(
                H1("Registration Failed"),
                P("Error creating account. Please try again.", style="color: red;"),
                A("← Try Again", href="/register", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )

@app.post("/auth/login")
def login(username: str, password: str):
    try:
        user_list = users(where=f"username='{username}'")
        if user_list:
            user = user_list[0]
            if verify_password(password, user.password_hash):
                # Create session and set cookie
                session_token = create_session(user.id)
                response = RedirectResponse('/', status_code=302)
                response.set_cookie('session_token', session_token, max_age=30*24*60*60)  # 30 days
                return response
            else:
                return Titled("Login Error",
                    Div(
                        H1("Login Failed"),
                        P("Invalid username or password.", style="color: red;"),
                        A("← Try Again", href="/login", class_="btn btn-secondary"),
                        style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                    )
                )
        else:
            return Titled("Login Error",
                Div(
                    H1("Login Failed"),
                    P("Invalid username or password.", style="color: red;"),
                    A("← Try Again", href="/login", class_="btn btn-secondary"),
                    style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                )
            )
    except Exception as e:
        return Titled("Login Error",
            Div(
                H1("Login Failed"),
                P(f"Error: {str(e)}", style="color: red;"),
                A("← Try Again", href="/login", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )

@app.get("/logout")
def logout(request):
    session_token = request.cookies.get('session_token')
    if session_token:
        # Delete session from database
        try:
            session_list = sessions(where=f"session_token='{session_token}'")
            if session_list:
                sessions.delete(session_list[0].id)
        except Exception as e:
            pass
    
    # Clear cookie and redirect
    response = RedirectResponse('/', status_code=302)
    response.delete_cookie('session_token')
    return response

# Protected application routes
@app.get("/picks")
def picks_page(request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login')
    
    all_picks = picks()
    welcome_name = f"{user.first_name} {user.last_name}" if user.first_name else user.username
    
    return Titled("Tournament Picks",
        Div(
            # User info header
            Div(
                Span(f"Logged in as: ", style="color: #666; font-size: 14px;"),
                Strong(f"{welcome_name}", style="color: #2c5282; margin-right: 10px;"),
                A("Logout", href="/logout", class_="btn btn-sm btn-outline", style="font-size: 12px; padding: 4px 12px;"),
                style="text-align: right; margin-bottom: 20px; padding: 10px; background: #f8f9fa; border-radius: 4px;"
            ),
            
            H1("🎯 Tournament Picks"),
            P(f"Manage your tournament picks, {user.first_name or user.username}!"),
            
            # Navigation
            Div(
                A("← Back to Home", href="/", class_="btn btn-outline", style="margin-right: 10px;"),
                A("➕ Add New Pick", href="/picks/new", class_="btn btn-primary")
            ),
            
            # Picks display
            Div(
                *[Div(
                    H3(pick.pickname),
                    P(f"Tier 1: {pick.tier1_pick}"),
                    P(f"Tier 2: {pick.tier2_pick}"),
                    P(f"Tier 3: {pick.tier3_pick}"),
                    P(f"Tier 4: {pick.tier4_pick}"),
                    P(f"Tournament: {pick.tournament_id}"),
                    P(f"Created: {pick.created_at}"),
                    Div(
                        A("Edit", href=f"/picks/{pick.id}/edit", class_="btn btn-secondary btn-sm", style="margin-right: 5px;"),
                        A("Delete", href=f"/picks/{pick.id}/delete", class_="btn btn-danger btn-sm")
                    ),
                    style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;"
                ) for pick in all_picks] if all_picks else [
                    Div(
                        P("🎯 No picks yet. Create your first pick!", style="text-align: center; color: #666; font-size: 18px; margin: 40px 0;"),
                        style="border: 2px dashed #ddd; padding: 40px; border-radius: 8px; text-align: center;"
                    )
                ],
                style="margin-top: 20px;"
            )
        )
    )

@app.get("/picks/new")
def new_pick_page(request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login')
    
    return Titled("New Pick",
        Div(
            H1("Create New Pick"),
            Form(
                Div(
                    Label("Pick Name:", for_="pickname"),
                    Input(id="pickname", name="pickname", type="text", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Tier 1 Pick:", for_="tier1_pick"),
                    Input(id="tier1_pick", name="tier1_pick", type="text", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Tier 2 Pick:", for_="tier2_pick"),
                    Input(id="tier2_pick", name="tier2_pick", type="text", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Tier 3 Pick:", for_="tier3_pick"),
                    Input(id="tier3_pick", name="tier3_pick", type="text", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Tier 4 Pick:", for_="tier4_pick"),
                    Input(id="tier4_pick", name="tier4_pick", type="text", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Tournament ID:", for_="tournament_id"),
                    Input(id="tournament_id", name="tournament_id", type="number", value="1", style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Button("Create Pick", type="submit", class_="btn btn-primary", style="margin-right: 10px;"),
                A("Cancel", href="/picks", class_="btn btn-secondary"),
                action="/picks", method="post"
            ),
            A("← Back to Picks", href="/picks", style="display: block; margin-top: 20px;")
        )
    )

@app.post("/picks")
def create_pick(request, pickname: str, tier1_pick: str, tier2_pick: str, tier3_pick: str, tier4_pick: str, tournament_id: int = 1):
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login')
    
    picks.insert(
        pickname=pickname,
        tier1_pick=tier1_pick,
        tier2_pick=tier2_pick,
        tier3_pick=tier3_pick,
        tier4_pick=tier4_pick,
        tournament_id=tournament_id,
        created_at=datetime.now().isoformat()
    )
    return RedirectResponse('/picks', status_code=302)

# Public routes (no authentication required)
@app.get("/tournaments")
def tournaments_page():
    all_tournaments = tournaments()
    return Titled("Tournaments",
        Div(
            H1("Tournaments"),
            Div(
                A("← Back to Home", href="/", class_="btn btn-outline")
            ),
            Div(
                *[Div(
                    H3(tournament.name),
                    P(f"Current: {'Yes' if tournament.current else 'No'}"),
                    P(f"Allow Submissions: {'Yes' if tournament.allow_submissions else 'No'}"),
                    P(f"Created: {tournament.created_at}"),
                    style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;"
                ) for tournament in all_tournaments] if all_tournaments else [P("No tournaments available.")],
                style="margin-top: 20px;"
            )
        )
    )

@app.get("/field")
def field_page():
    field_data = tournament_golfers()
    return Titled("Tournament Field",
        Div(
            H1("Tournament Field"),
            Div(
                A("← Back to Home", href="/", class_="btn btn-outline")
            ),
            Div(
                *[Div(
                    H4(f"{golfer.player_name} (Tier {golfer.tier})"),
                    P(f"Tournament: {golfer.tournament}"),
                    style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 5px;"
                ) for golfer in field_data] if field_data else [P("No field data available.")],
                style="margin-top: 20px;"
            )
        )
    )

@app.get("/leaderboards")
def leaderboards_page():
    tournament_lb = tournament_leaderboard()
    pickem_lb = pickem_leaderboard()
    
    return Titled("Leaderboards",
        Div(
            H1("Leaderboards"),
            Div(
                A("← Back to Home", href="/", class_="btn btn-outline")
            ),
            Div(
                H2("Tournament Leaderboard"),
                Div(
                    *[Div(
                        H4(f"{entry.player_name} - {entry.score} ({entry.strokes} strokes)"),
                        P(f"Tournament: {entry.tournament} | Round: {entry.round}"),
                        style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 5px;"
                    ) for entry in tournament_lb] if tournament_lb else [P("No tournament leaderboard data.")],
                    style="margin-bottom: 30px;"
                ),
                H2("Pickem Leaderboard"),
                Div(
                    *[Div(
                        H4(f"{entry.pickname} - Total: {entry.total_score}"),
                        P(f"T1: {entry.tier1_pick} ({entry.tier1_score}) | T2: {entry.tier2_pick} ({entry.tier2_score})"),
                        P(f"T3: {entry.tier3_pick} ({entry.tier3_score}) | T4: {entry.tier4_pick} ({entry.tier4_score})"),
                        style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 5px;"
                    ) for entry in pickem_lb] if pickem_lb else [P("No pickem leaderboard data.")],
                ),
                style="margin-top: 20px;"
            )
        )
    )

# Password reset routes
@app.get("/forgot-password")
def forgot_password_page():
    return Titled("Forgot Password - Golf Pickem League",
        Div(
            H1("Forgot Password"),
            P("Enter your email address and we'll send you a link to reset your password."),
            Form(
                Div(
                    Label("Email:", for_="email"),
                    Input(id="email", name="email", type="email", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Button("Send Reset Link", type="submit", class_="btn btn-primary", style="margin-right: 10px;"),
                A("Back to Login", href="/login", class_="btn btn-secondary"),
                action="/auth/forgot-password", method="post",
                style="max-width: 400px; margin: 0 auto;"
            ),
            A("← Back to Home", href="/", style="display: block; margin-top: 20px; text-align: center;"),
            style="max-width: 500px; margin: 0 auto; padding: 20px;"
        )
    )

@app.post("/auth/forgot-password")
def forgot_password(email: str):
    try:
        user_list = users(where=f"email='{email}' AND is_active=1")
        if user_list:
            user = user_list[0]
            reset_token = create_password_reset(user.id)
            
            # In a real app, you'd send an email here
            # For now, we'll just show the reset link
            return Titled("Reset Link Generated",
                Div(
                    H1("Password Reset"),
                    P("A password reset link has been generated for your account.", style="color: green;"),
                    P("In a production app, this would be sent to your email. For now, use this link:"),
                    A(f"Reset Password", href=f"/reset-password?token={reset_token}", class_="btn btn-primary", style="display: block; margin: 20px 0;"),
                    A("← Back to Login", href="/login", class_="btn btn-secondary"),
                    style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                )
            )
        else:
            # Don't reveal if email exists or not for security
            return Titled("Reset Link Sent",
                Div(
                    H1("Password Reset"),
                    P("If an account with that email exists, a reset link has been sent.", style="color: green;"),
                    A("← Back to Login", href="/login", class_="btn btn-secondary"),
                    style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                )
            )
    except Exception as e:
        return Titled("Error",
            Div(
                H1("Error"),
                P("There was an error processing your request.", style="color: red;"),
                A("← Try Again", href="/forgot-password", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )

@app.get("/reset-password")
def reset_password_page(token: str = None):
    if not token:
        return RedirectResponse('/forgot-password')
    
    user_id = validate_reset_token(token)
    if not user_id:
        return Titled("Invalid Reset Link",
            Div(
                H1("Invalid Reset Link"),
                P("This reset link is invalid or has expired.", style="color: red;"),
                A("Request New Reset Link", href="/forgot-password", class_="btn btn-primary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )
    
    return Titled("Reset Password - Golf Pickem League",
        Div(
            H1("Reset Password"),
            Form(
                Input(name="token", type="hidden", value=token),
                Div(
                    Label("New Password:", for_="password"),
                    Input(id="password", name="password", type="password", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Confirm New Password:", for_="confirm_password"),
                    Input(id="confirm_password", name="confirm_password", type="password", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Button("Reset Password", type="submit", class_="btn btn-primary"),
                action="/auth/reset-password", method="post",
                style="max-width: 400px; margin: 0 auto;"
            ),
            style="max-width: 500px; margin: 0 auto; padding: 20px;"
        )
    )

@app.post("/auth/reset-password")
def reset_password(token: str, password: str, confirm_password: str):
    if password != confirm_password:
        return Titled("Error",
            Div(
                H1("Password Reset Failed"),
                P("Passwords do not match.", style="color: red;"),
                A("← Try Again", href=f"/reset-password?token={token}", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )
    
    if len(password) < 8:
        return Titled("Error",
            Div(
                H1("Password Reset Failed"),
                P("Password must be at least 8 characters long.", style="color: red;"),
                A("← Try Again", href=f"/reset-password?token={token}", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )
    
    user_id = validate_reset_token(token)
    if not user_id:
        return Titled("Invalid Reset Link",
            Div(
                H1("Invalid Reset Link"),
                P("This reset link is invalid or has expired.", style="color: red;"),
                A("Request New Reset Link", href="/forgot-password", class_="btn btn-primary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )
    
    try:
        # Update password
        password_hash = hash_password(password)
        current_time = datetime.now().isoformat()
        users.update(user_id, password_hash=password_hash, updated_at=current_time)
        
        # Mark reset token as used
        use_reset_token(token)
        
        return Titled("Password Reset Successful",
            Div(
                H1("Password Reset Successful"),
                P("Your password has been reset successfully.", style="color: green;"),
                A("Login Now", href="/login", class_="btn btn-primary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )
    except Exception as e:
        return Titled("Error",
            Div(
                H1("Password Reset Failed"),
                P("There was an error resetting your password.", style="color: red;"),
                A("← Try Again", href=f"/reset-password?token={token}", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )

# Profile management routes
@app.get("/profile")
@require_auth
def profile_page(request, user):
    welcome_name = f"{user.first_name} {user.last_name}" if user.first_name else user.username
    
    return Titled("Profile - Golf Pickem League",
        Div(
            # User info header
            Div(
                Span(f"Logged in as: ", style="color: #666; font-size: 14px;"),
                Strong(f"{welcome_name}", style="color: #2c5282; margin-right: 10px;"),
                Span(f"({'Admin' if user.is_admin else 'User'})", 
                     style=f"color: {'#d69e2e' if user.is_admin else '#666'}; font-size: 12px; background: {'#fef5e7' if user.is_admin else '#f8f9fa'}; padding: 2px 6px; border-radius: 12px; margin-right: 15px;"),
                A("🏠 Home", href="/", class_="btn btn-sm btn-outline", style="margin-right: 8px; font-size: 12px; padding: 4px 12px;"),
                A("🚪 Logout", href="/logout", class_="btn btn-sm btn-danger", style="font-size: 12px; padding: 4px 12px;"),
                style="text-align: right; margin-bottom: 20px; padding: 12px; background: #f8f9fa; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;"
            ),
            
            H1("👤 My Profile"),
            
            # Profile card
            Div(
                Div(
                    H3("📋 Profile Information", style="color: #2c5282; margin-bottom: 20px;"),
                    Div(
                        Div(
                            Strong("First Name: "), 
                            Span(user.first_name or "Not set", style="color: #666;"),
                            style="margin-bottom: 12px;"
                        ),
                        Div(
                            Strong("Last Name: "), 
                            Span(user.last_name or "Not set", style="color: #666;"),
                            style="margin-bottom: 12px;"
                        ),
                        Div(
                            Strong("Username: "), 
                            Span(user.username, style="color: #666;"),
                            style="margin-bottom: 12px;"
                        ),
                        Div(
                            Strong("Email: "), 
                            Span(user.email, style="color: #666;"),
                            style="margin-bottom: 12px;"
                        ),
                        Div(
                            Strong("Account Type: "), 
                            Span('🔐 Administrator' if user.is_admin else '👤 Standard User', 
                                 style=f"color: {'#d69e2e' if user.is_admin else '#666'}; font-weight: 500;"),
                            style="margin-bottom: 12px;"
                        ),
                        Div(
                            Strong("Member Since: "), 
                            Span(user.created_at[:10] if user.created_at else "Unknown", style="color: #666;"),
                            style="margin-bottom: 20px;"
                        ),
                    ),
                    
                    # Action buttons
                    Div(
                        A("✏️ Edit Profile", href="/profile/edit", class_="btn btn-primary", style="margin-right: 10px;"),
                        Span("🔒 Change Password (Coming Soon)", class_="btn", style="cursor: not-allowed; background-color: #e9ecef; color: #6c757d; border-color: #e9ecef;"),
                    ),
                    style="background: white; border: 1px solid #e9ecef; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
                ),
                A("← Back to Home", href="/", class_="btn btn-outline", style="margin-top: 20px;")
            ),
            style="max-width: 600px; margin: 0 auto; padding: 20px;"
        )
    )

@app.get("/profile/edit")
@require_auth
def edit_profile_page(request, user):
    return Titled("Edit Profile - Golf Pickem League",
        Div(
            H1("Edit Profile"),
            Form(
                Div(
                    Label("First Name:", for_="first_name"),
                    Input(id="first_name", name="first_name", type="text", value=user.first_name or "", style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Last Name:", for_="last_name"),
                    Input(id="last_name", name="last_name", type="text", value=user.last_name or "", style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Username:", for_="username"),
                    Input(id="username", name="username", type="text", value=user.username, required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Email:", for_="email"),
                    Input(id="email", name="email", type="email", value=user.email, required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Button("Update Profile", type="submit", class_="btn btn-primary", style="margin-right: 10px;"),
                A("Cancel", href="/profile", class_="btn btn-secondary"),
                action="/profile/update", method="post",
                style="max-width: 400px; margin: 0 auto;"
            ),
            A("← Back to Profile", href="/profile", style="display: block; margin-top: 20px; text-align: center;"),
            style="max-width: 500px; margin: 0 auto; padding: 20px;"
        )
    )

@app.post("/profile/update")
@require_auth
def update_profile(request, user, first_name: str, last_name: str, username: str, email: str):
    # Validation
    if username != user.username:
        # Check if new username is taken
        try:
            existing_user = users(where=f"username='{username}' AND id!={user.id}")
            if existing_user:
                return Titled("Update Error",
                    Div(
                        H1("Profile Update Failed"),
                        P("Username already exists.", style="color: red;"),
                        A("← Try Again", href="/profile/edit", class_="btn btn-secondary"),
                        style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                    )
                )
        except Exception as e:
            pass
    
    if email != user.email:
        # Check if new email is taken
        try:
            existing_email = users(where=f"email='{email}' AND id!={user.id}")
            if existing_email:
                return Titled("Update Error",
                    Div(
                        H1("Profile Update Failed"),
                        P("Email already exists.", style="color: red;"),
                        A("← Try Again", href="/profile/edit", class_="btn btn-secondary"),
                        style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                    )
                )
        except Exception as e:
            pass
    
    try:
        # Update user
        current_time = datetime.now().isoformat()
        users.update(
            user.id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            updated_at=current_time
        )
        
        return RedirectResponse('/profile', status_code=302)
        
    except Exception as e:
        return Titled("Update Error",
            Div(
                H1("Profile Update Failed"),
                P("Error updating profile. Please try again.", style="color: red;"),
                A("← Try Again", href="/profile/edit", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )

@app.get("/profile/change-password")
@require_auth
def change_password_page(request, user):
    return Titled("Feature Coming Soon - Golf Pickem League",
        Div(
            H1("🔧 Feature Coming Soon"),
            P("The password change functionality is currently being developed and will be available soon.", style="color: #666; margin-bottom: 20px;"),
            P("We apologize for the inconvenience.", style="color: #666; margin-bottom: 30px;"),
            A("← Back to Profile", href="/profile", class_="btn btn-primary"),
            style="max-width: 500px; margin: 0 auto; padding: 40px 20px; text-align: center;"
        )
    )

@app.post("/profile/change-password")
def change_password_handler(request):
    # Temporary disabled route
    return Titled("Feature Coming Soon - Golf Pickem League",
        Div(
            H1("🔧 Feature Coming Soon"),
            P("The password change functionality is currently being developed and will be available soon.", style="color: #666; margin-bottom: 20px;"),
            P("We apologize for the inconvenience.", style="color: #666; margin-bottom: 30px;"),
            A("← Back to Profile", href="/profile", class_="btn btn-primary"),
            style="max-width: 500px; margin: 0 auto; padding: 40px 20px; text-align: center;"
        )
    )

# Admin routes
@app.get("/admin/users")
@require_admin
def admin_users_page(request, user):
    all_users = users()
    welcome_name = f"{user.first_name} {user.last_name}" if user.first_name else user.username
    
    return Titled("User Management - Golf Pickem League",
        Div(
            # Admin header
            Div(
                Span(f"👤 Admin: ", style="color: #d69e2e; font-size: 14px; font-weight: 600;"),
                Strong(f"{welcome_name}", style="color: #d69e2e; margin-right: 15px;"),
                A("🏠 Home", href="/", class_="btn btn-sm btn-outline", style="margin-right: 8px; font-size: 12px; padding: 4px 12px;"),
                A("🚪 Logout", href="/logout", class_="btn btn-sm btn-danger", style="font-size: 12px; padding: 4px 12px;"),
                style="text-align: right; margin-bottom: 20px; padding: 12px; background: linear-gradient(135deg, #fef5e7 0%, #f6e05e 20%); border-radius: 6px; border-left: 4px solid #d69e2e;"
            ),
            
            H1("👥 User Management"),
            P("Manage all registered users in the system"),
            
            # Action buttons
            Div(
                A("← Back to Home", href="/", class_="btn btn-outline", style="margin-right: 10px;"),
                A("➕ Add New User", href="/admin/users/new", class_="btn btn-primary")
            ),
            
            # Users table
            Div(
                Table(
                    Thead(
                        Tr(
                            Th("ID", style="width: 60px;"),
                            Th("Name"),
                            Th("Username"),
                            Th("Email"),
                            Th("Admin", style="width: 80px;"),
                            Th("Active", style="width: 80px;"),
                            Th("Created", style="width: 100px;"),
                            Th("Actions", style="width: 200px;")
                        )
                    ),
                    Tbody(
                        *[Tr(
                            Td(str(u.id)),
                            Td(f"{u.first_name or ''} {u.last_name or ''}".strip() or "Not set"),
                            Td(u.username),
                            Td(u.email),
                            Td("✅ Yes" if u.is_admin else "❌ No"),
                            Td("✅ Active" if u.is_active else "❌ Inactive"),
                            Td(u.created_at[:10] if u.created_at else "Unknown"),
                            Td(
                                Div(
                                    A("✏️", href=f"/admin/users/{u.id}/edit", class_="btn btn-sm btn-secondary", style="margin-right: 3px; padding: 4px 8px;", title="Edit User"),
                                    A("🔧" if not u.is_admin else "🔽", href=f"/admin/users/{u.id}/toggle-admin", class_="btn btn-sm btn-warning", style="margin-right: 3px; padding: 4px 8px;", title="Toggle Admin"),
                                    A("🔄" if u.is_active else "✅", href=f"/admin/users/{u.id}/toggle-active", class_="btn btn-sm btn-info", style="padding: 4px 8px;", title="Toggle Active"),
                                    style="display: flex; gap: 2px;"
                                )
                            ),
                            id=f"user-{u.id}"
                        ) for u in all_users],
                        style="font-size: 14px;"
                    )
                ),
                style="margin-top: 20px; overflow-x: auto;"
            ),
            style="max-width: 1200px; margin: 0 auto; padding: 20px;"
        )
    )

@app.get("/admin/users/new")
@require_admin
def admin_new_user_page(request, user):
    return Titled("Add New User - Golf Pickem League",
        Div(
            H1("Add New User"),
            Form(
                Div(
                    Label("First Name:", for_="first_name"),
                    Input(id="first_name", name="first_name", type="text", style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Last Name:", for_="last_name"),
                    Input(id="last_name", name="last_name", type="text", style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Username:", for_="username"),
                    Input(id="username", name="username", type="text", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Email:", for_="email"),
                    Input(id="email", name="email", type="email", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Password:", for_="password"),
                    Input(id="password", name="password", type="password", required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label(
                        Input(name="is_admin", type="checkbox", style="margin-right: 5px;"),
                        "Administrator"
                    ),
                    style="margin-bottom: 10px;"
                ),
                Button("Create User", type="submit", class_="btn btn-primary", style="margin-right: 10px;"),
                A("Cancel", href="/admin/users", class_="btn btn-secondary"),
                action="/admin/users/create", method="post",
                style="max-width: 400px; margin: 0 auto;"
            ),
            A("← Back to User Management", href="/admin/users", style="display: block; margin-top: 20px; text-align: center;"),
            style="max-width: 500px; margin: 0 auto; padding: 20px;"
        )
    )

@app.post("/admin/users/create")
@require_admin
def admin_create_user(request, user, first_name: str = "", last_name: str = "", username: str = "", email: str = "", password: str = "", is_admin: bool = False):
    # Validation
    if len(password) < 8:
        return Titled("User Creation Error",
            Div(
                H1("User Creation Failed"),
                P("Password must be at least 8 characters long.", style="color: red;"),
                A("← Try Again", href="/admin/users/new", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )
    
    # Check if username or email already exists
    try:
        existing_user = users(where=f"username='{username}'")
        if existing_user:
            return Titled("User Creation Error",
                Div(
                    H1("User Creation Failed"),
                    P("Username already exists.", style="color: red;"),
                    A("← Try Again", href="/admin/users/new", class_="btn btn-secondary"),
                    style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                )
            )
    except Exception as e:
        pass
    
    try:
        existing_email = users(where=f"email='{email}'")
        if existing_email:
            return Titled("User Creation Error",
                Div(
                    H1("User Creation Failed"),
                    P("Email already exists.", style="color: red;"),
                    A("← Try Again", href="/admin/users/new", class_="btn btn-secondary"),
                    style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                )
            )
    except Exception as e:
        pass
    
    try:
        # Create user
        password_hash = hash_password(password)
        current_time = datetime.now().isoformat()
        
        new_user = users.insert(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            password_hash=password_hash,
            is_admin=is_admin,
            is_active=True,
            created_at=current_time,
            updated_at=current_time
        )
        
        return RedirectResponse('/admin/users', status_code=302)
        
    except Exception as e:
        return Titled("User Creation Error",
            Div(
                H1("User Creation Failed"),
                P("Error creating user. Please try again.", style="color: red;"),
                A("← Try Again", href="/admin/users/new", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )

@app.get("/admin/users/{user_id}/edit")
@require_admin
def admin_edit_user_page(request, user, user_id: int):
    try:
        edit_user = users[user_id]
    except:
        return Titled("User Not Found",
            Div(
                H1("User Not Found"),
                P("The requested user could not be found.", style="color: red;"),
                A("← Back to User Management", href="/admin/users", class_="btn btn-primary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )
    
    return Titled("Edit User - Golf Pickem League",
        Div(
            H1(f"Edit User: {edit_user.username}"),
            Form(
                Div(
                    Label("First Name:", for_="first_name"),
                    Input(id="first_name", name="first_name", type="text", value=edit_user.first_name or "", style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Last Name:", for_="last_name"),
                    Input(id="last_name", name="last_name", type="text", value=edit_user.last_name or "", style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Username:", for_="username"),
                    Input(id="username", name="username", type="text", value=edit_user.username, required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label("Email:", for_="email"),
                    Input(id="email", name="email", type="email", value=edit_user.email, required=True, style="width: 100%; padding: 8px; margin-bottom: 10px;")
                ),
                Div(
                    Label(
                        Input(name="is_admin", type="checkbox", checked=edit_user.is_admin, style="margin-right: 5px;"),
                        "Administrator"
                    ),
                    style="margin-bottom: 10px;"
                ),
                Div(
                    Label(
                        Input(name="is_active", type="checkbox", checked=edit_user.is_active, style="margin-right: 5px;"),
                        "Active"
                    ),
                    style="margin-bottom: 10px;"
                ),
                Button("Update User", type="submit", class_="btn btn-primary", style="margin-right: 10px;"),
                A("Cancel", href="/admin/users", class_="btn btn-secondary"),
                action=f"/admin/users/{user_id}/update", method="post",
                style="max-width: 400px; margin: 0 auto;"
            ),
            A("← Back to User Management", href="/admin/users", style="display: block; margin-top: 20px; text-align: center;"),
            style="max-width: 500px; margin: 0 auto; padding: 20px;"
        )
    )

@app.post("/admin/users/{user_id}/update")
@require_admin
def admin_update_user(request, user, user_id: int, first_name: str = "", last_name: str = "", username: str = "", email: str = "", is_admin: bool = False, is_active: bool = False):
    try:
        edit_user = users[user_id]
    except:
        return Titled("User Not Found",
            Div(
                H1("User Not Found"),
                P("The requested user could not be found.", style="color: red;"),
                A("← Back to User Management", href="/admin/users", class_="btn btn-primary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )
    
    # Validation
    if username != edit_user.username:
        try:
            existing_user = users(where=f"username='{username}' AND id!={user_id}")
            if existing_user:
                return Titled("Update Error",
                    Div(
                        H1("User Update Failed"),
                        P("Username already exists.", style="color: red;"),
                        A("← Try Again", href=f"/admin/users/{user_id}/edit", class_="btn btn-secondary"),
                        style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                    )
                )
        except Exception as e:
            pass
    
    if email != edit_user.email:
        try:
            existing_email = users(where=f"email='{email}' AND id!={user_id}")
            if existing_email:
                return Titled("Update Error",
                    Div(
                        H1("User Update Failed"),
                        P("Email already exists.", style="color: red;"),
                        A("← Try Again", href=f"/admin/users/{user_id}/edit", class_="btn btn-secondary"),
                        style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                    )
                )
        except Exception as e:
            pass
    
    try:
        # Update user
        current_time = datetime.now().isoformat()
        users.update(
            user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            is_admin=is_admin,
            is_active=is_active,
            updated_at=current_time
        )
        
        return RedirectResponse('/admin/users', status_code=302)
        
    except Exception as e:
        return Titled("Update Error",
            Div(
                H1("User Update Failed"),
                P("Error updating user. Please try again.", style="color: red;"),
                A("← Try Again", href=f"/admin/users/{user_id}/edit", class_="btn btn-secondary"),
                style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
            )
        )

@app.get("/admin/users/{user_id}/toggle-admin")
@require_admin
def admin_toggle_admin(request, user, user_id: int):
    try:
        edit_user = users[user_id]
        
        # Prevent removing admin from last admin
        if edit_user.is_admin:
            admin_count = len([u for u in users() if u.is_admin])
            if admin_count <= 1:
                return Titled("Cannot Remove Admin",
                    Div(
                        H1("Cannot Remove Admin"),
                        P("Cannot remove admin privileges from the last administrator.", style="color: red;"),
                        A("← Back to User Management", href="/admin/users", class_="btn btn-primary"),
                        style="max-width: 500px; margin: 0 auto; padding: 20px; text-align: center;"
                    )
                )
        
        # Toggle admin status
        users.update(user_id, is_admin=not edit_user.is_admin, updated_at=datetime.now().isoformat())
        return RedirectResponse('/admin/users', status_code=302)
        
    except Exception as e:
        return RedirectResponse('/admin/users', status_code=302)

@app.get("/admin/users/{user_id}/toggle-active")
@require_admin
def admin_toggle_active(request, user, user_id: int):
    try:
        edit_user = users[user_id]
        
        # Toggle active status
        users.update(user_id, is_active=not edit_user.is_active, updated_at=datetime.now().isoformat())
        return RedirectResponse('/admin/users', status_code=302)
        
    except Exception as e:
        return RedirectResponse('/admin/users', status_code=302)

@app.get("/admin/tournaments")
@require_admin
def admin_tournaments_page(request, user):
    all_tournaments = tournaments()
    return Titled("Tournament Management - Golf Pickem League",
        Div(
            H1("Tournament Management"),
            P("Manage tournaments (Admin Only)"),
            Div(
                A("← Back to Home", href="/", class_="btn btn-outline", style="margin-right: 10px;"),
                A("Add New Tournament", href="#", class_="btn btn-primary")
            ),
            Div(
                *[Div(
                    H3(tournament.name),
                    P(f"Current: {'Yes' if tournament.current else 'No'}"),
                    P(f"Allow Submissions: {'Yes' if tournament.allow_submissions else 'No'}"),
                    P(f"Created: {tournament.created_at}"),
                    Div(
                        A("Edit", href="#", class_="btn btn-secondary btn-sm", style="margin-right: 5px;"),
                        A("Delete", href="#", class_="btn btn-danger btn-sm")
                    ),
                    style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;"
                ) for tournament in all_tournaments] if all_tournaments else [P("No tournaments available. Admin functionality for tournaments coming soon.")],
                style="margin-top: 20px;"
            ),
            style="max-width: 800px; margin: 0 auto; padding: 20px;"
        )
    )

# Start the server
if __name__ == "__main__":
    print(f"🏌️  Starting {APP_NAME}")
    print(f"📍 Access the application at: http://{HOST}:{PORT}")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    serve(host=HOST, port=PORT, reload=RELOAD)
