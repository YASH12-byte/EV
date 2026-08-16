from flask import Blueprint, redirect, render_template, url_for

pages_bp = Blueprint("pages", __name__)


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


@pages_bp.get("/contact")
def contact():
    return render_template("contact.html")


@pages_bp.get("/admin")
def admin():
    return render_template("admin.html")
