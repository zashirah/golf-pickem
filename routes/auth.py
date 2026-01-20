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
                    Label("GroupMe Name", fr="groupme_name"),
                    Input(type="text", name="groupme_name", id="groupme_name", required=True),
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
    def login_submit(request, groupme_name: str, password: str):
        token, error = auth_service.login(groupme_name, password)

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
                    Label("GroupMe Name", fr="groupme_name"),
                    Input(type="text", name="groupme_name", id="groupme_name", required=True,
                          placeholder="Your GroupMe display name"),
                    Small("This is how your name will appear and how you'll log in", style="color: #666;"),
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
    def register_submit(request, invite: str, groupme_name: str, password: str, password2: str):
        if not auth_service.validate_invite(invite):
            return RedirectResponse("/register", status_code=303)

        if password != password2:
            return RedirectResponse(f"/register?invite={invite}&error=Passwords do not match", status_code=303)

        if len(password) < 6:
            return RedirectResponse(f"/register?invite={invite}&error=Password must be at least 6 characters", status_code=303)

        if not groupme_name or not groupme_name.strip():
            return RedirectResponse(f"/register?invite={invite}&error=GroupMe name is required", status_code=303)

        # Verify GroupMe membership
        from services.groupme import GroupMeClient
        from config import GROUPME_ACCESS_TOKEN, GROUPME_GROUP_ID

        if GROUPME_ACCESS_TOKEN and GROUPME_GROUP_ID:
            client = GroupMeClient()
            is_member = client.verify_member(groupme_name, GROUPME_GROUP_ID, GROUPME_ACCESS_TOKEN)
            if not is_member:
                return RedirectResponse(f"/register?invite={invite}&error=GroupMe name not found in group. Please check spelling.", status_code=303)

        user, error = auth_service.register_user(groupme_name, password)

        if error:
            return RedirectResponse(f"/register?invite={invite}&error={error}", status_code=303)

        # Auto-login after registration
        token, _ = auth_service.login(groupme_name, password)
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
