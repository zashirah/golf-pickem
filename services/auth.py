"""Authentication service - sessions, password hashing, invites."""
import hashlib
import secrets
from datetime import datetime, timedelta
from config import SESSION_DAYS


def hash_password(password: str) -> str:
    """Hash password with SHA-256 and random salt."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{pw_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    try:
        salt, pw_hash = stored_hash.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == pw_hash
    except ValueError:
        return False


def generate_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(32)


def generate_invite_secret() -> str:
    """Generate a new invite secret."""
    return secrets.token_urlsafe(16)


def get_session_expiry() -> str:
    """Get session expiry datetime string."""
    return (datetime.now() + timedelta(days=SESSION_DAYS)).isoformat()


def is_session_valid(expires_at: str) -> bool:
    """Check if session is still valid."""
    try:
        expiry = datetime.fromisoformat(expires_at)
        return datetime.now() < expiry
    except (ValueError, TypeError):
        return False


class AuthService:
    """Authentication service for user management."""

    def __init__(self, db_module):
        self.db = db_module

    def get_invite_secret(self) -> str:
        """Get current invite secret, create if doesn't exist."""
        settings = list(self.db.app_settings())
        for s in settings:
            if s.key == 'invite_secret':
                return s.value

        # Create new invite secret
        secret = generate_invite_secret()
        self.db.app_settings.insert(key='invite_secret', value=secret)
        return secret

    def reset_invite_secret(self) -> str:
        """Generate and save new invite secret."""
        new_secret = generate_invite_secret()
        settings = list(self.db.app_settings())
        for s in settings:
            if s.key == 'invite_secret':
                self.db.app_settings.update(id=s.id, value=new_secret)
                return new_secret

        # Create if doesn't exist
        self.db.app_settings.insert(key='invite_secret', value=new_secret)
        return new_secret

    def validate_invite(self, provided_secret: str) -> bool:
        """Check if provided invite secret is valid."""
        return provided_secret == self.get_invite_secret()

    def register_user(self, username: str, password: str, display_name: str = None) -> tuple:
        """Register a new user. Returns (user, error_message)."""
        # Check if username exists
        existing = [u for u in self.db.users() if u.username == username]
        if existing:
            return None, "Username already taken"

        # Check if first user (make admin)
        all_users = list(self.db.users())
        is_admin = len(all_users) == 0

        # Create user
        user = self.db.users.insert(
            username=username,
            password_hash=hash_password(password),
            display_name=display_name or username,
            is_admin=is_admin,
            created_at=datetime.now().isoformat()
        )

        return user, None

    def login(self, username: str, password: str) -> tuple:
        """Authenticate user. Returns (session_token, error_message)."""
        users = [u for u in self.db.users() if u.username == username]
        if not users:
            return None, "Invalid username or password"

        user = users[0]
        if not verify_password(password, user.password_hash):
            return None, "Invalid username or password"

        # Create session
        token = generate_session_token()
        self.db.sessions.insert(
            user_id=user.id,
            token=token,
            expires_at=get_session_expiry(),
            created_at=datetime.now().isoformat()
        )

        return token, None

    def get_user_from_token(self, token: str):
        """Get user from session token. Returns None if invalid."""
        if not token:
            return None

        sessions = [s for s in self.db.sessions() if s.token == token]
        if not sessions:
            return None

        session = sessions[0]
        if not is_session_valid(session.expires_at):
            # Clean up expired session
            self.db.sessions.delete(session.id)
            return None

        users = [u for u in self.db.users() if u.id == session.user_id]
        return users[0] if users else None

    def logout(self, token: str):
        """Delete session."""
        sessions = [s for s in self.db.sessions() if s.token == token]
        for session in sessions:
            self.db.sessions.delete(session.id)
