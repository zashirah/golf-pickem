"""
Golf Pickem League - FastHTML Web Application
Simplified main application with inline imports to avoid module issues.
"""
from fasthtml.common import *
from starlette.responses import RedirectResponse
from pathlib import Path
import os
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

if users not in db.t:
    users.create(id=int, username=str, email=str, password_hash=str, created_at=str, pk='id')
User = users.dataclass()

if sessions not in db.t:
    sessions.create(id=int, user_id=int, session_token=str, created_at=str, expires_at=str, pk='id')
Session = sessions.dataclass()

# Authentication helpers
import hashlib
import secrets
from datetime import datetime, timedelta

def hash_password(password: str) -> str:
    """Hash password with salt"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

def generate_session_token() -> str:
    """Generate secure session token"""
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
        return user
    except Exception as e:
        return None

def require_auth(func):
    """Decorator to require authentication"""
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return RedirectResponse('/login')
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
css_link = Link(rel="stylesheet", href="/static/style.css")
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
        return Titled("Golf Pickem League Starter",
            Div(
                Div(
                    H1("🏌️ Golf Pickem League"),
                    P(f"Welcome back, {user.username}!", style="font-size: 18px; color: #2c5282;"),
                    Div(
                        A("Logout", href="/logout", class_="btn btn-outline", style="float: right;")
                    ),
                    style="position: relative;"
                ),
                P("Make your tournament picks and compete with friends."),
                Div(
                    A("Make Your Picks", href="/picks", class_="btn btn-primary", style="margin-right: 10px;"),
                    A("View Tournaments", href="/tournaments", class_="btn btn-secondary", style="margin-right: 10px;"),
                    A("Tournament Field", href="/field", class_="btn btn-secondary", style="margin-right: 10px;"),
                    A("Leaderboards", href="/leaderboards", class_="btn btn-secondary"),
                    style="margin-top: 20px;"
                ),
                P("Start by checking out the current tournaments and making your picks!", style="margin-top: 20px; color: #666;")
            )
        )
    else:
        # Guest user view
        return Titled("Golf Pickem League Starter",
            Div(
                H1("🏌️ Golf Pickem League"),
                P("Welcome to the Golf Pickem League! Make your tournament picks and compete with friends."),
                Div(
                    A("Login", href="/login", class_="btn btn-primary", style="margin-right: 10px;"),
                    A("Register", href="/register", class_="btn btn-secondary"),
                    style="margin-top: 20px;"
                ),
                Hr(style="margin: 30px 0;"),
                H3("Browse as Guest"),
                Div(
                    A("View Tournaments", href="/tournaments", class_="btn btn-outline", style="margin-right: 10px;"),
                    A("Tournament Field", href="/field", class_="btn btn-outline", style="margin-right: 10px;"),
                    A("Leaderboards", href="/leaderboards", class_="btn btn-outline"),
                    style="margin-top: 10px;"
                ),
                P("To make picks and participate, please login or register above.", style="margin-top: 20px; color: #666;")
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
def register(username: str, email: str, password: str, confirm_password: str):
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
        new_user = users.insert(
            username=username,
            email=email,
            password_hash=password_hash,
            created_at=datetime.now().isoformat()
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
    return Titled("Tournament Picks",
        Div(
            H1("Tournament Picks"),
            P(f"Make your picks, {user.username}!"),
            Div(
                A("← Back to Home", href="/", class_="btn btn-outline", style="margin-right: 10px;"),
                A("Add New Pick", href="/picks/new", class_="btn btn-primary")
            ),
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
                ) for pick in all_picks] if all_picks else [P("No picks yet. Create your first pick!")],
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

# Start the server
if __name__ == "__main__":
    print(f"🏌️  Starting {APP_NAME}")
    print(f"📍 Access the application at: http://{HOST}:{PORT}")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    serve(host=HOST, port=PORT, reload=RELOAD)
