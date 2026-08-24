from flask import Blueprint, current_app, redirect, render_template, send_from_directory, url_for

pages_bp = Blueprint("pages", __name__)

# VS Code Live Server opens these disk paths; map them to real Flask routes.
_LIVE_SERVER_PAGES = {
    "login.html": "pages.login_page",
    "register.html": "pages.register_page",
    "index.html": "pages.home",
    "dashboard.html": "pages.dashboard",
    "about.html": "pages.about",
    "dataset.html": "pages.dataset",
    "prediction.html": "pages.prediction",
    "comparison.html": "pages.comparison",
    "research.html": "pages.research",
    "xai.html": "pages.xai_page",
    "contact.html": "pages.contact",
    "admin.html": "pages.admin",
    "base.html": "pages.home",
}


@pages_bp.get("/live-index.html")
def live_index():
    return redirect(url_for("pages.login_page"))


@pages_bp.get("/frontend/templates/<name>")
@pages_bp.get("/templates/<name>")
def live_server_template(name: str):
    endpoint = _LIVE_SERVER_PAGES.get(name)
    if endpoint:
        return redirect(url_for(endpoint))
    return redirect(url_for("pages.login_page"))


@pages_bp.get("/frontend/static/<path:filename>")
def live_server_static(filename: str):
    return send_from_directory(current_app.static_folder, filename)


@pages_bp.get("/")
def root():
    """First entry opens the login interface."""
    return redirect(url_for("pages.login_page"))


@pages_bp.get("/home")
def home():
    return render_template("index.html")


@pages_bp.get("/login")
def login_page():
    return render_template("login.html")


@pages_bp.get("/register")
def register_page():
    return render_template("register.html")


@pages_bp.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@pages_bp.get("/about")
def about():
    return render_template("about.html")


@pages_bp.get("/dataset")
def dataset():
    return render_template("dataset.html")


@pages_bp.get("/prediction")
def prediction():
    return render_template("prediction.html")


@pages_bp.get("/comparison")
def comparison():
    return render_template("comparison.html")


@pages_bp.get("/research")
def research():
    return redirect(url_for("pages.dataset") + "#research")


@pages_bp.get("/xai")
def xai_page():
    return render_template("xai.html")


@pages_bp.get("/contact")
def contact():
    return render_template("contact.html")


@pages_bp.get("/admin")
def admin():
    return render_template("admin.html")
