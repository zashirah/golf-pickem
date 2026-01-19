"""Authentication routes."""
from fasthtml.common import *
from components.layout import page_shell, alert, card


def setup_auth_routes(app, auth_service):
    """Register authentication routes."""

    @app.get("/login")
    def login_page(request, error: str = None):
        user = auth_service.get_user_from_token(request.cookies.get('session'))
        if user:
            return RedirectResponse("/", status_code=303)

        content = card(
            "Login",
            Form(
                alert(error, "error") if error else None,
                Div(
                    Label("Username", fr="username"),
                    Input(type="text", name="username", id="username", required=True),
                    cls="form-group"
                ),
                Div(
                    Label("Password", fr="password"),
                    Input(type="password", name="password", id="password", required=True),
                    cls="form-group"
                ),
                Button("Login", type="submit", cls="btn btn-primary btn-block"),
                action="/login",
                method="post"
            ),
            cls="auth-card"
        )

        return page_shell("Login", content)

    @app.post("/login")
    def login_submit(request, username: str, password: str):
        token, error = auth_service.login(username, password)

        if error:
            return RedirectResponse(f"/login?error={error}", status_code=303)

        response = RedirectResponse("/", status_code=303)
        response.set_cookie("session", token, max_age=60*60*24*30, httponly=True)
        return response

    @app.get("/register")
    def register_page(request, invite: str = None, error: str = None):
        user = auth_service.get_user_from_token(request.cookies.get('session'))
        if user:
            return RedirectResponse("/", status_code=303)

        if not invite or not auth_service.validate_invite(invite):
            return page_shell(
                "Registration",
                card(
                    "Invalid Invite",
                    P("You need a valid invite link to register."),
                    P("Contact the league administrator for access."),
                    cls="auth-card"
                )
            )

        content = card(
            "Create Account",
            Form(
                alert(error, "error") if error else None,
                Input(type="hidden", name="invite", value=invite),
                Div(
                    Label("Username", fr="username"),
                    Input(type="text", name="username", id="username", required=True),
                    cls="form-group"
                ),
                Div(
                    Label("Display Name", fr="display_name"),
                    Input(type="text", name="display_name", id="display_name",
                          placeholder="How your name appears on leaderboard"),
                    cls="form-group"
                ),
                Div(
                    Label("Password", fr="password"),
                    Input(type="password", name="password", id="password", required=True, minlength="6"),
                    cls="form-group"
                ),
                Div(
                    Label("Confirm Password", fr="password2"),
                    Input(type="password", name="password2", id="password2", required=True),
                    cls="form-group"
                ),
                Button("Create Account", type="submit", cls="btn btn-primary btn-block"),
                action="/register",
                method="post"
            ),
            cls="auth-card"
        )

        return page_shell("Register", content)

    @app.post("/register")
    def register_submit(request, invite: str, username: str, password: str, password2: str, display_name: str = None):
        if not auth_service.validate_invite(invite):
            return RedirectResponse("/register", status_code=303)

        if password != password2:
            return RedirectResponse(f"/register?invite={invite}&error=Passwords do not match", status_code=303)

        if len(password) < 6:
            return RedirectResponse(f"/register?invite={invite}&error=Password must be at least 6 characters", status_code=303)

        user, error = auth_service.register_user(username, password, display_name)

        if error:
            return RedirectResponse(f"/register?invite={invite}&error={error}", status_code=303)

        # Auto-login after registration
        token, _ = auth_service.login(username, password)
        response = RedirectResponse("/", status_code=303)
        response.set_cookie("session", token, max_age=60*60*24*30, httponly=True)
        return response

    @app.get("/logout")
    def logout(request):
        token = request.cookies.get('session')
        if token:
            auth_service.logout(token)

        response = RedirectResponse("/", status_code=303)
        response.delete_cookie("session")
        return response
