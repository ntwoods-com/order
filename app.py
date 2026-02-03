from flask import Flask, render_template_string, send_file, request, flash, redirect, url_for, session, current_app, get_flashed_messages, jsonify
from werkzeug.utils import secure_filename
from generate_sale_order import prepare_data, write_report
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import pandas as pd
import uuid
from functools import wraps
from dotenv import load_dotenv
import time
import sqlite3
import math
from flask_bcrypt import Bcrypt
import re # Import re for filename sanitization
from werkzeug.middleware.proxy_fix import ProxyFix
from db_utils import connect as db_connect, init_schema

# Import Blueprints
from api import api_bp
from admin import admin_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- Load environment variables ----------------
_dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(_dotenv_path):
    load_dotenv(_dotenv_path, override=False)

def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}

def _configure_logging() -> None:
    if getattr(_configure_logging, "_configured", False):
        return

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_file = os.getenv("LOG_FILE", os.path.join(BASE_DIR, "app.log"))
    max_bytes = int(os.getenv("LOG_MAX_BYTES", "5000000"))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "3"))

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # Avoid duplicate handlers under WSGI reloads.
    logger.handlers = []
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    _configure_logging._configured = True

_configure_logging()

# 🔒 Track active user sessions (for single-login restriction)
ACTIVE_SESSIONS = {}

app = Flask(__name__)
# Respect PythonAnywhere/other reverse proxies (needed for correct scheme/host)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- SECURE: Load secret key from environment variables ---
app.secret_key = os.getenv('SECRET_KEY')
if not app.secret_key:
    raise ValueError("SECRET_KEY environment variable is not set!")

# Session configuration for better security
app.config['SESSION_COOKIE_HTTPONLY'] = True

_app_env = os.getenv("APP_ENV", "development").strip().lower()
_default_secure_cookie = _app_env in {"production", "prod"}
app.config['SESSION_COOKIE_SECURE'] = _env_bool("SESSION_COOKIE_SECURE", default=_default_secure_cookie)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 7800  # 1 hour session timeout

# Initialize Bcrypt for password hashing
bcrypt = Bcrypt(app)

# Session validation middleware
@app.before_request
def validate_session():
    # Skip validation for static files and login/logout routes
    if request.endpoint is None:
        return

    if request.endpoint in ['static', 'login', 'logout', 'favicon']:
        return
    
    # Skip for non-authenticated routes (add more if needed)
    public_routes = ['login']
    if request.endpoint in public_routes:
        return
    
    # Check if user session exists and is valid
    if 'user' in session:
        username = session.get('user')
        session_id = session.get('session_id')
        if not username or not session_id:
            session.clear()
            flash("Your session is invalid. Please login again.", "error")
            return redirect(url_for('login'))

        if username not in USERS:
            app.logger.error(f"User {username} not found in USERS")
            session.clear()
            flash("User account not found. Please contact administrator.", "error")
            return redirect(url_for('login'))

        try:
            expected = get_active_session_id(username)
        except Exception as e:
            app.logger.error(f"Session validation DB error for user {username}: {e}")
            session.clear()
            flash("Session check failed. Please login again.", "error")
            return redirect(url_for('login'))

        if not expected or expected != session_id:
            app.logger.info(f"Session rotated for user {username}; forcing re-login")
            session.clear()
            flash("You have been logged out because you logged in on another device.", "error")
            return redirect(url_for('login'))

# Load users from .env (format: USER1=username:hashed_password)
USERS = {}
for key, value in os.environ.items():
    if key.startswith("USER") and key not in ("USERNAME","USERDOMAIN","USERDOMAIN_ROAMINGPROFILE"):
        try:
            uname, hashed_pwd = value.split(":", 1)
            USERS[uname] = hashed_pwd
        except ValueError:
            app.logger.warning(f"Invalid user format in {key} (expected USERX=username:hashed_password)")

# Configuration
class Config:
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
    REPORT_FOLDER = os.getenv('REPORT_FOLDER', os.path.join(BASE_DIR, 'reports'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024)))  # bytes
    ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
    CLEANUP_INTERVAL_HOURS = int(os.getenv('CLEANUP_INTERVAL_HOURS', 8))
    DATABASE_FILE = os.getenv('DATABASE_FILE', os.path.join(BASE_DIR, 'order_counter.db'))

app.config.from_object(Config)

# Store USERS dict in app config for admin panel
app.config['USERS_DICT'] = USERS

# Register Blueprints
app.register_blueprint(api_bp)
app.register_blueprint(admin_bp)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)

# ---------------- Enhanced HTML Templates with Modern UI/UX ----------------
THEME_CSS_AND_JS = """
<style>
    /* Modern CSS Reset & Base */
    *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
    
    /* THEME-SWITCHER STYLES */
    .header-controls {
        position: absolute; top: 1rem; right: 1.5rem; display: flex; align-items: center; gap: 1rem; z-index: 100;
    }
    .theme-selector select {
        background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); color: var(--text-light, #fff);
        border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; padding: 0.5rem 0.75rem;
        font-size: 0.85rem; cursor: pointer; transition: all 0.3s ease;
        -webkit-appearance: none; -moz-appearance: none; appearance: none; padding-right: 2.5rem;
        background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
        background-repeat: no-repeat; background-position: right 0.75rem center; background-size: 1em;
    }
    .theme-selector select:hover { background: rgba(255, 255, 255, 0.2); transform: translateY(-1px); }
    .theme-selector select:focus { outline: 2px solid var(--secondary-color); outline-offset: 2px; }
    .theme-selector option { background-color: #1e293b; color: #f1f5f9; }
    .login-container .theme-selector, .card .theme-selector {
        position: absolute; top: 1.5rem; right: 1.5rem;
    }
    .login-container .theme-selector select, .card .theme-selector select {
        background-color: var(--bg-main); color: var(--text-dark); border-color: var(--border-color);
        background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23334155' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
    }

    /* ENHANCED THEME DEFINITIONS */
    :root, [data-theme='default'] {
        --primary-color: #6366f1; --secondary-color: #8b5cf6; 
        --header-bg: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
        --bg-main: #fafbfc; --bg-card: #ffffff; --text-dark: #0f172a; --text-light: #ffffff;
        --text-muted: #64748b; --border-color: #e2e8f0; --shadow-color: rgba(99, 102, 241, 0.15);
        --success-bg: #dcfce7; --success-text: #166534; --error-bg: #fee2e2; --error-text: #dc2626;
        --gradient-accent: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
    }
    [data-theme='dark'] {
        --primary-color: #818cf8; --secondary-color: #a78bfa;
        --header-bg: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #581c87 100%);
        --bg-main: #0f0f23; --bg-card: #1e1b4b; --text-dark: #f1f5f9; --text-light: #f8fafc;
        --text-muted: #94a3b8; --border-color: #334155; --shadow-color: rgba(129, 140, 248, 0.2);
        --gradient-accent: linear-gradient(135deg, rgba(129, 140, 248, 0.1), rgba(167, 139, 250, 0.1));
    }
    [data-theme='ocean'] {
        --primary-color: #0ea5e9; --secondary-color: #06b6d4;
        --header-bg: linear-gradient(135deg, #0c4a6e 0%, #0e7490 50%, #155e75 100%);
        --bg-main: #f0f9ff; --bg-card: #ffffff; --text-dark: #0c4a6e; --text-muted: #475569;
        --border-color: #bae6fd; --shadow-color: rgba(14, 165, 233, 0.15);
        --gradient-accent: linear-gradient(135deg, rgba(14, 165, 233, 0.1), rgba(6, 182, 212, 0.1));
    }
    [data-theme='forest'] {
        --primary-color: #22c55e; --secondary-color: #16a34a;
        --header-bg: linear-gradient(135deg, #14532d 0%, #166534 50%, #15803d 100%);
        --bg-main: #f0fdf4; --bg-card: #ffffff; --text-dark: #14532d; --text-muted: #4d7c0f;
        --border-color: #bbf7d0; --shadow-color: rgba(34, 197, 94, 0.15);
        --gradient-accent: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(22, 163, 74, 0.1));
    }
    [data-theme='sunset'] {
        --primary-color: #f97316; --secondary-color: #ea580c;
        --header-bg: linear-gradient(135deg, #9a3412 0%, #c2410c 50%, #dc2626 100%);
        --bg-main: #fffbeb; --bg-card: #ffffff; --text-dark: #9a3412; --text-muted: #a16207;
        --border-color: #fed7aa; --shadow-color: rgba(249, 115, 22, 0.15);
        --gradient-accent: linear-gradient(135deg, rgba(249, 115, 22, 0.1), rgba(234, 88, 12, 0.1));
    }
    [data-theme='rose'] {
        --primary-color: #f43f5e; --secondary-color: #ec4899;
        --header-bg: linear-gradient(135deg, #881337 0%, #9d174d 50%, #be185d 100%);
        --bg-main: #fff1f2; --bg-card: #ffffff; --text-dark: #881337; --text-muted: #9f1239;
        --border-color: #fbb6ce; --shadow-color: rgba(244, 63, 94, 0.15);
        --gradient-accent: linear-gradient(135deg, rgba(244, 63, 94, 0.1), rgba(236, 72, 153, 0.1));
    }
    [data-theme='slate'] {
        --primary-color: #64748b; --secondary-color: #475569;
        --header-bg: linear-gradient(135deg, #1e293b 0%, #334155 50%, #475569 100%);
        --bg-main: #f8fafc; --bg-card: #ffffff; --text-dark: #0f172a; --text-muted: #334155;
        --border-color: #cbd5e1; --shadow-color: rgba(100, 116, 139, 0.15);
        --gradient-accent: linear-gradient(135deg, rgba(100, 116, 139, 0.1), rgba(71, 85, 105, 0.1));
    }
    [data-theme='nebula'] {
        --primary-color: #8b5cf6; --secondary-color: #d946ef;
        --header-bg: linear-gradient(135deg, #581c87 0%, #7c3aed 50%, #a855f7 100%);
        --bg-main: #faf5ff; --bg-card: #ffffff; --text-dark: #581c87; --text-muted: #7c2d12;
        --border-color: #e9d5ff; --shadow-color: rgba(139, 92, 246, 0.15);
        --gradient-accent: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(217, 70, 239, 0.1));
    }
    [data-theme='lime'] {
        --primary-color: #84cc16; --secondary-color: #a3e635;
        --header-bg: linear-gradient(135deg, #365314 0%, #4d7c0f 50%, #65a30d 100%);
        --bg-main: #f7fee7; --bg-card: #ffffff; --text-dark: #365314; --text-muted: #4d7c0f;
        --border-color: #d9f99d; --shadow-color: rgba(132, 204, 22, 0.15);
        --gradient-accent: linear-gradient(135deg, rgba(132, 204, 22, 0.1), rgba(163, 230, 53, 0.1));
    }
    [data-theme='copper'] {
        --primary-color: #d97706; --secondary-color: #b45309;
        --header-bg: linear-gradient(135deg, #78350f 0%, #92400e 50%, #a16207 100%);
        --bg-main: #fefce8; --bg-card: #ffffff; --text-dark: #78350f; --text-muted: #92400e;
        --border-color: #fde68a; --shadow-color: rgba(217, 119, 6, 0.15);
        --gradient-accent: linear-gradient(135deg, rgba(217, 119, 6, 0.1), rgba(180, 83, 9, 0.1));
    }

    /* Enhanced Base Styles - Optimized for fast loading */
    html { 
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
        scroll-behavior: smooth;
    }
    body {
        background: var(--bg-main); min-height: 100vh; color: var(--text-dark);
        transition: background-color 0.2s ease, color 0.2s ease;
        /* Removed heavy background animations for faster loading */
        display: flex; align-items: center; justify-content: center; padding: 1.5rem;
    }

    /* Enhanced Container Styles - Faster loading */
    .container, .card {
        background: var(--bg-card); border-radius: 24px; width: 100%;
        box-shadow: 0 20px 40px -12px var(--shadow-color);
        border: 1px solid var(--border-color); overflow: hidden; position: relative;
        transition: transform 0.2s ease;
    }
    .container:hover, .card:hover {
        transform: translateY(-2px);
    }
    .container { max-width: 950px; }
    .card { 
        max-width: 480px; text-align: center; padding: 3rem; position: relative;
        background: linear-gradient(135deg, var(--bg-card) 0%, var(--gradient-accent) 100%);
    }

    /* Typography Enhancements */
    h1, h2, h3, h4 { 
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; font-weight: 700; line-height: 1.2;
    }
    h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
    h2 { font-size: 2rem; margin-bottom: 0.75rem; }
    p { color: var(--text-muted); line-height: 1.6; }
    .tagline { font-size: 1.1rem; opacity: 0.9; margin-top: 0.5rem; }

    /* Enhanced Header - Simplified for faster loading */
    .header {
        background: var(--header-bg); color: var(--text-light); padding: 3rem 2rem;
        text-align: center; position: relative; border-radius: 24px 24px 0 0;
        overflow: hidden;
    }

    .main { padding: 3rem; }

    /* Enhanced Form Elements */
    label { 
        font-weight: 600; font-size: 0.9rem; display: block; margin-bottom: 0.75rem; 
        text-align: left; color: var(--text-dark);
    }
    input, textarea, select {
        width: 100%; padding: 1rem 1.25rem; border: 2px solid var(--border-color);
        background: var(--bg-main); color: var(--text-dark); border-radius: 16px;
        font-size: 1rem; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-family: inherit;
    }
    input:focus, textarea:focus, select:focus { 
        outline: none; border-color: var(--primary-color); 
        box-shadow: 0 0 0 4px var(--shadow-color), 0 8px 25px -8px var(--shadow-color);
        transform: translateY(-2px);
    }
    input:hover, textarea:hover, select:hover {
        border-color: var(--primary-color);
    }

    /* Enhanced Buttons */
    .btn {
        padding: 1rem 2rem; border: none; border-radius: 16px; font-weight: 600;
        cursor: pointer; text-decoration: none; display: inline-flex;
        align-items: center; justify-content: center; gap: 0.75rem; 
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative; overflow: hidden; font-family: inherit;
        box-shadow: 0 4px 15px 0 var(--shadow-color);
    }
    .btn::before {
        content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    .btn:hover::before { left: 100%; }
    .btn:hover { 
        transform: translateY(-3px) scale(1.02); 
        box-shadow: 0 12px 35px -8px var(--shadow-color);
    }
    .btn:active { transform: translateY(-1px) scale(0.98); }
    .btn-primary { 
        background: var(--header-bg); color: var(--text-light);
    }
    .btn-secondary { 
        background: var(--bg-main); color: var(--text-dark); 
        border: 2px solid var(--border-color);
    }

    /* Enhanced Upload Area */
    .upload-area {
        border: 3px dashed var(--border-color); border-radius: 20px; padding: 3rem;
        cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        background: var(--gradient-accent); position: relative; overflow: hidden;
    }
    .upload-area::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.05) 50%, transparent 70%);
        opacity: 0; transition: opacity 0.3s;
    }
    .upload-area:hover::before { opacity: 1; }
    .upload-area:hover {
        border-color: var(--primary-color); transform: translateY(-4px);
        box-shadow: 0 20px 40px -8px var(--shadow-color);
    }
    .upload-area.dragover {
        border-color: var(--primary-color); background: var(--gradient-accent);
        transform: scale(1.02);
    }

    /* Enhanced Alerts */
    .alert { 
        padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; border-radius: 16px; 
        font-weight: 500; border: 2px solid transparent; position: relative;
        animation: slideIn 0.3s ease-out;
    }
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .alert-error { 
        background: linear-gradient(135deg, var(--error-bg), rgba(220, 38, 38, 0.1));
        color: var(--error-text); border-color: #fca5a5;
    }
    .alert-success { 
        background: linear-gradient(135deg, var(--success-bg), rgba(34, 197, 94, 0.1));
        color: var(--success-text); border-color: #86efac;
    }

    /* Enhanced File Info */
    .file-info {
        border-left: 5px solid var(--primary-color); padding: 1.25rem 1.75rem;
        background: var(--gradient-accent); border-radius: 0 16px 16px 0;
        margin: 1.5rem 0; animation: fadeIn 0.5s ease-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    /* Enhanced Navigation */
    .nav-links {
        display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center; 
        margin-top: 1.5rem;
    }
    .nav-links .btn {
        padding: 0.75rem 1.5rem; font-size: 0.9rem;
        background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* User Info Styling */
    .user-info {
        margin-top: 2rem; padding-top: 1.5rem; 
        border-top: 1px solid rgba(255, 255, 255, 0.2);
        animation: slideUp 0.5s ease-out 0.3s both;
    }
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Login Header */
    .login-header {
        margin-bottom: 2rem; animation: fadeInScale 0.6s ease-out;
    }
    @keyframes fadeInScale {
        from { opacity: 0; transform: scale(0.9); }
        to { opacity: 1; transform: scale(1); }
    }

    /* Form Groups */
    .form-group {
        margin-bottom: 1.5rem; text-align: left;
        animation: slideInLeft 0.4s ease-out;
    }
    .form-group:nth-child(2) { animation-delay: 0.1s; }
    .form-group:nth-child(3) { animation-delay: 0.2s; }
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    /* Grid Layout Enhancement */
    .grid-form {
        display: grid; 
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
        gap: 1.5rem;
    }

    /* Loading States */
    .btn:disabled {
        opacity: 0.6; cursor: not-allowed; transform: none !important;
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        body { padding: 1rem; }
        .container, .card { border-radius: 20px; }
        .header { padding: 2rem 1.5rem; }
        .main { padding: 2rem; }
        h1 { font-size: 2rem; }
        h2 { font-size: 1.5rem; }
        .grid-form { grid-template-columns: 1fr; }
        .nav-links { flex-direction: column; align-items: center; }
        .theme-selector { position: static; margin-bottom: 1rem; }
        .header-controls { position: static; justify-content: center; margin-bottom: 1rem; }
    }

    /* Micro-interactions */
    * { animation-fill-mode: both; }
    .container, .card { animation: containerFadeIn 0.6s ease-out; }
    @keyframes containerFadeIn {
        from { opacity: 0; transform: translateY(30px) scale(0.95); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* Enhanced scrollbar for webkit browsers */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: var(--bg-main); }
    ::-webkit-scrollbar-thumb { 
        background: var(--border-color); border-radius: 4px;
        transition: background 0.3s;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--primary-color); }
    
    /* ========== ADVANCED UI ENHANCEMENTS ========== */
    
    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 16px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
    }
    
    /* Floating Animation */
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    .float-animation { animation: float 3s ease-in-out infinite; }
    
    /* Pulse Animation */
    @keyframes pulse-soft {
        0%, 100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
        50% { box-shadow: 0 0 0 15px rgba(99, 102, 241, 0); }
    }
    
    .pulse-animation { animation: pulse-soft 2s infinite; }
    
    /* Gradient Text */
    .gradient-text {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Shimmer Effect for Loading */
    @keyframes shimmer {
        0% { background-position: -1000px 0; }
        100% { background-position: 1000px 0; }
    }
    
    .shimmer {
        background: linear-gradient(90deg, var(--bg-card) 0%, var(--gradient-accent) 50%, var(--bg-card) 100%);
        background-size: 1000px 100%;
        animation: shimmer 2s infinite linear;
    }
    
    /* Toast Notifications */
    .toast-container {
        position: fixed;
        top: 1.5rem;
        right: 1.5rem;
        z-index: 10000;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    
    .toast {
        padding: 1rem 1.5rem;
        border-radius: 12px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        animation: slideInRight 0.3s ease-out;
        box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        max-width: 350px;
    }
    
    .toast-success { background: var(--success-bg); color: var(--success-text); }
    .toast-error { background: var(--error-bg); color: var(--error-text); }
    .toast-info { background: var(--gradient-accent); color: var(--primary-color); }
    
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    /* Loading Spinner */
    .spinner {
        width: 40px;
        height: 40px;
        border: 4px solid var(--border-color);
        border-top: 4px solid var(--primary-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Skeleton Loading */
    .skeleton {
        background: linear-gradient(90deg, var(--bg-main) 25%, var(--border-color) 50%, var(--bg-main) 75%);
        background-size: 200% 100%;
        animation: skeleton-loading 1.5s infinite;
        border-radius: 8px;
    }
    
    @keyframes skeleton-loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    
    /* Hover Lift Effect */
    .hover-lift {
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .hover-lift:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 40px -12px var(--shadow-color);
    }
    
    /* Progress Bar */
    .progress-bar {
        height: 8px;
        background: var(--border-color);
        border-radius: 4px;
        overflow: hidden;
    }
    
    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
        border-radius: 4px;
        transition: width 0.5s ease;
    }
    
    /* Badge Styles */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        gap: 0.25rem;
    }
    
    .badge-primary { background: var(--primary-color); color: white; }
    .badge-success { background: var(--success-bg); color: var(--success-text); }
    .badge-warning { background: #fef3c7; color: #d97706; }
    .badge-danger { background: var(--error-bg); color: var(--error-text); }
    
    /* Tooltip */
    .tooltip {
        position: relative;
    }
    
    .tooltip::after {
        content: attr(data-tooltip);
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        padding: 0.5rem 0.75rem;
        background: var(--text-dark);
        color: var(--bg-card);
        font-size: 0.75rem;
        border-radius: 6px;
        white-space: nowrap;
        opacity: 0;
        visibility: hidden;
        transition: all 0.2s ease;
        z-index: 1000;
    }
    
    .tooltip:hover::after {
        opacity: 1;
        visibility: visible;
        transform: translateX(-50%) translateY(-5px);
    }
    
    /* Animated Gradient Border */
    .gradient-border {
        position: relative;
        background: var(--bg-card);
        border-radius: 16px;
    }
    
    .gradient-border::before {
        content: '';
        position: absolute;
        inset: -2px;
        background: linear-gradient(45deg, var(--primary-color), var(--secondary-color), #ec4899, var(--primary-color));
        background-size: 400% 400%;
        border-radius: 18px;
        z-index: -1;
        animation: gradient-rotate 5s linear infinite;
    }
    
    @keyframes gradient-rotate {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Stats Counter Animation */
    .counter {
        font-variant-numeric: tabular-nums;
    }
    
    /* Keyboard Shortcut Badge */
    .kbd {
        display: inline-block;
        padding: 0.15rem 0.4rem;
        font-size: 0.7rem;
        font-family: monospace;
        background: var(--bg-main);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 2px 0 var(--border-color);
    }
    
    /* Empty State */
    .empty-state {
        text-align: center;
        padding: 3rem;
        color: var(--text-muted);
    }
    
    .empty-state-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }
    
    /* Page Transition */
    .page-enter {
        animation: pageEnter 0.4s ease-out;
    }
    
    @keyframes pageEnter {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* ========== SUPER ADVANCED UI/UX ========== */
    
    /* Animated Background Particles */
    .particles-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
        overflow: hidden;
    }
    
    .particle {
        position: absolute;
        width: 6px;
        height: 6px;
        background: var(--primary-color);
        border-radius: 50%;
        opacity: 0.3;
        animation: particleFloat 15s infinite ease-in-out;
    }
    
    @keyframes particleFloat {
        0%, 100% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
        10% { opacity: 0.3; }
        90% { opacity: 0.3; }
        100% { transform: translateY(-10vh) rotate(720deg); opacity: 0; }
    }
    
    /* 3D Card Tilt Effect */
    .tilt-card {
        transform-style: preserve-3d;
        perspective: 1000px;
        transition: transform 0.5s ease;
    }
    
    .tilt-card:hover {
        transform: rotateX(5deg) rotateY(5deg) scale(1.02);
    }
    
    /* Morphing Button */
    .btn-morph {
        position: relative;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
    }
    
    .btn-morph:hover {
        border-radius: 50px;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
    }
    
    .btn-morph::after {
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
        left: -100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        transition: left 0.5s;
    }
    
    .btn-morph:hover::after {
        left: 100%;
    }
    
    /* Neon Glow Effect */
    .neon-glow {
        text-shadow: 0 0 10px var(--primary-color),
                     0 0 20px var(--primary-color),
                     0 0 40px var(--primary-color);
    }
    
    .neon-box {
        box-shadow: 0 0 10px var(--primary-color),
                    0 0 20px var(--primary-color),
                    inset 0 0 10px rgba(255,255,255,0.1);
    }
    
    /* Command Palette Styles */
    .command-palette-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(8px);
        z-index: 99999;
        display: none;
        align-items: flex-start;
        justify-content: center;
        padding-top: 15vh;
        animation: fadeIn 0.2s ease;
    }
    
    .command-palette-overlay.active {
        display: flex;
    }
    
    .command-palette {
        background: var(--bg-card);
        border-radius: 16px;
        width: 100%;
        max-width: 600px;
        box-shadow: 0 25px 80px rgba(0,0,0,0.35);
        border: 1px solid var(--border-color);
        overflow: hidden;
        animation: slideDown 0.25s ease;
    }
    
    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-20px) scale(0.95); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    
    .command-input-wrapper {
        display: flex;
        align-items: center;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--border-color);
        gap: 0.75rem;
    }
    
    .command-input-wrapper input {
        border: none;
        background: transparent;
        font-size: 1.1rem;
        flex: 1;
        padding: 0.5rem;
    }
    
    .command-input-wrapper input:focus {
        outline: none;
        box-shadow: none;
        transform: none;
    }
    
    .command-results {
        max-height: 400px;
        overflow-y: auto;
    }
    
    .command-item {
        display: flex;
        align-items: center;
        padding: 1rem 1.25rem;
        cursor: pointer;
        transition: all 0.15s ease;
        gap: 1rem;
        border-bottom: 1px solid var(--border-color);
    }
    
    .command-item:hover, .command-item.active {
        background: var(--gradient-accent);
    }
    
    .command-item-icon {
        font-size: 1.25rem;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--bg-main);
        border-radius: 10px;
    }
    
    .command-item-content {
        flex: 1;
    }
    
    .command-item-title {
        font-weight: 600;
        color: var(--text-dark);
    }
    
    .command-item-desc {
        font-size: 0.85rem;
        color: var(--text-muted);
    }
    
    .command-shortcut {
        display: flex;
        gap: 0.25rem;
    }
    
    /* Animated Stats Counter */
    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Ripple Click Effect */
    .ripple {
        position: relative;
        overflow: hidden;
    }
    
    .ripple-effect {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.4);
        transform: scale(0);
        animation: rippleAnim 0.6s linear;
        pointer-events: none;
    }
    
    @keyframes rippleAnim {
        to { transform: scale(4); opacity: 0; }
    }
    
    /* Smooth Scroll Progress Bar */
    .scroll-progress {
        position: fixed;
        top: 0;
        left: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
        z-index: 99999;
        transition: width 0.1s;
    }
    
    /* Animated Underline Links */
    .fancy-link {
        position: relative;
        text-decoration: none;
        color: var(--primary-color);
    }
    
    .fancy-link::after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
        transition: width 0.3s ease;
    }
    
    .fancy-link:hover::after {
        width: 100%;
    }
    
    /* Spotlight Effect on Cards */
    .spotlight-card {
        position: relative;
        overflow: hidden;
    }
    
    .spotlight-card::before {
        content: '';
        position: absolute;
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.3s;
        transform: translate(-50%, -50%);
    }
    
    .spotlight-card:hover::before {
        opacity: 1;
    }
    
    /* Staggered Animation for Lists */
    .stagger-item {
        opacity: 0;
        transform: translateY(20px);
        animation: staggerIn 0.5s ease forwards;
    }
    
    @keyframes staggerIn {
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Confetti Animation */
    .confetti {
        position: fixed;
        width: 10px;
        height: 10px;
        z-index: 99999;
        pointer-events: none;
    }
    
    @keyframes confettiFall {
        0% { transform: translateY(-100vh) rotate(0deg); opacity: 1; }
        100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
    }
    
    /* Blur Loading Overlay */
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255,255,255,0.8);
        backdrop-filter: blur(5px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 99998;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.3s;
    }
    
    .loading-overlay.active {
        opacity: 1;
        pointer-events: auto;
    }
    
    /* Fancy Input with Floating Label */
    .floating-label-group {
        position: relative;
        margin-bottom: 1.5rem;
    }
    
    .floating-label-group input {
        padding-top: 1.5rem;
    }
    
    .floating-label {
        position: absolute;
        top: 50%;
        left: 1.25rem;
        transform: translateY(-50%);
        transition: all 0.2s ease;
        pointer-events: none;
        color: var(--text-muted);
        font-size: 1rem;
    }
    
    .floating-label-group input:focus + .floating-label,
    .floating-label-group input:not(:placeholder-shown) + .floating-label {
        top: 0.75rem;
        font-size: 0.75rem;
        color: var(--primary-color);
        transform: translateY(0);
    }
    
    /* Animated Checkbox */
    .fancy-checkbox {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        cursor: pointer;
    }
    
    .fancy-checkbox input {
        display: none;
    }
    
    .fancy-checkbox-box {
        width: 24px;
        height: 24px;
        border: 2px solid var(--border-color);
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
    }
    
    .fancy-checkbox input:checked + .fancy-checkbox-box {
        background: var(--primary-color);
        border-color: var(--primary-color);
    }
    
    .fancy-checkbox-box::after {
        content: '✓';
        color: white;
        font-size: 14px;
        opacity: 0;
        transform: scale(0);
        transition: all 0.2s ease;
    }
    
    .fancy-checkbox input:checked + .fancy-checkbox-box::after {
        opacity: 1;
        transform: scale(1);
    }
    
    /* Typing Animation */
    .typing-text {
        overflow: hidden;
        border-right: 3px solid var(--primary-color);
        white-space: nowrap;
        animation: typing 3s steps(30, end), blink 0.75s step-end infinite;
    }
    
    @keyframes typing {
        from { width: 0; }
        to { width: 100%; }
    }
    
    @keyframes blink {
        50% { border-color: transparent; }
    }
    
    /* Draggable Cards */
    .draggable {
        cursor: grab;
        user-select: none;
    }
    
    .draggable:active {
        cursor: grabbing;
    }
    
    .draggable.dragging {
        opacity: 0.5;
        transform: rotate(3deg);
    }
    
    /* Quick Action Floating Button */
    .fab {
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        cursor: pointer;
        box-shadow: 0 6px 20px var(--shadow-color);
        transition: all 0.3s ease;
        z-index: 1000;
        border: none;
    }
    
    .fab:hover {
        transform: scale(1.1) rotate(90deg);
        box-shadow: 0 10px 30px var(--shadow-color);
    }
    
    .fab-menu {
        position: fixed;
        bottom: 7rem;
        right: 2rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        opacity: 0;
        visibility: hidden;
        transform: translateY(20px);
        transition: all 0.3s ease;
        z-index: 999;
    }
    
    .fab-menu.active {
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
    }
    
    .fab-menu-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: var(--bg-card);
        padding: 0.75rem 1rem;
        border-radius: 30px;
        box-shadow: 0 4px 15px var(--shadow-color);
        text-decoration: none;
        color: var(--text-dark);
        font-weight: 500;
        transition: all 0.2s ease;
        white-space: nowrap;
    }
    
    .fab-menu-item:hover {
        transform: translateX(-5px);
        background: var(--gradient-accent);
    }
    
    /* Mobile Bottom Navigation */
    @media (max-width: 768px) {
        .mobile-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--bg-card);
            border-top: 1px solid var(--border-color);
            display: flex;
            justify-content: space-around;
            padding: 0.75rem 0;
            z-index: 1000;
            box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
        }
        
        .mobile-nav a {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.25rem;
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.7rem;
            transition: color 0.2s;
        }
        
        .mobile-nav a.active {
            color: var(--primary-color);
        }
        
        .mobile-nav a span {
            font-size: 1.25rem;
        }
        
        body {
            padding-bottom: 5rem;
        }
        
        .fab {
            bottom: 5rem;
        }
    }
    
    /* Smooth Number Counter */
    .count-up {
        transition: all 0.5s ease;
    }
    
    /* Card Flip Animation */
    .flip-card {
        perspective: 1000px;
        height: 200px;
    }
    
    .flip-card-inner {
        position: relative;
        width: 100%;
        height: 100%;
        transition: transform 0.8s;
        transform-style: preserve-3d;
    }
    
    .flip-card:hover .flip-card-inner {
        transform: rotateY(180deg);
    }
    
    .flip-card-front, .flip-card-back {
        position: absolute;
        width: 100%;
        height: 100%;
        backface-visibility: hidden;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1.5rem;
    }
    
    .flip-card-front {
        background: var(--gradient-accent);
    }
    
    .flip-card-back {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        color: white;
        transform: rotateY(180deg);
    }
</style>
<script>
    document.addEventListener('DOMContentLoaded', () => {
        const themeSwitch = document.getElementById('theme-switch');
        const currentTheme = localStorage.getItem('theme') || 'default';

        const applyTheme = (theme) => {
            document.documentElement.setAttribute('data-theme', theme);
            // Add smooth transition effect
            document.documentElement.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            setTimeout(() => {
                document.documentElement.style.transition = '';
            }, 300);
        };

        applyTheme(currentTheme);
        if (themeSwitch) {
            themeSwitch.value = currentTheme;
            themeSwitch.addEventListener('change', (e) => {
                const selectedTheme = e.target.value;
                localStorage.setItem('theme', selectedTheme);
                applyTheme(selectedTheme);
                
                // Show toast notification
                showToast('Theme changed to ' + selectedTheme, 'success');
                
                // Add ripple effect
                const ripple = document.createElement('div');
                ripple.style.cssText = `
                    position: fixed; top: 50%; left: 50%; width: 100px; height: 100px;
                    background: var(--primary-color); border-radius: 50%; 
                    transform: translate(-50%, -50%) scale(0); opacity: 0.3;
                    animation: rippleEffect 0.6s ease-out; pointer-events: none; z-index: 9999;
                `;
                document.body.appendChild(ripple);
                setTimeout(() => ripple.remove(), 600);
            });
        }
        
        // Add page enter animation
        document.body.classList.add('page-enter');
        
        // Initialize particles background
        createParticles();
        
        // Initialize scroll progress bar
        createScrollProgress();
        
        // Initialize FAB menu
        initFAB();
        
        // Initialize command palette
        initCommandPalette();
        
        // Add ripple effect to buttons
        addRippleEffect();
        
        // Animate counters
        animateCounters();
        
        // Stagger animation for lists
        animateStaggerItems();
    });
    
    // Create floating particles
    function createParticles() {
        const container = document.createElement('div');
        container.className = 'particles-bg';
        document.body.appendChild(container);
        
        for (let i = 0; i < 15; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 15 + 's';
            particle.style.animationDuration = (15 + Math.random() * 10) + 's';
            container.appendChild(particle);
        }
    }
    
    // Scroll progress bar
    function createScrollProgress() {
        const progress = document.createElement('div');
        progress.className = 'scroll-progress';
        document.body.appendChild(progress);
        
        window.addEventListener('scroll', () => {
            const scrollTop = document.documentElement.scrollTop;
            const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            const scrollPercent = (scrollTop / scrollHeight) * 100;
            progress.style.width = scrollPercent + '%';
        });
    }
    
    // Floating Action Button
    function initFAB() {
        const fabHTML = `
            <button class="fab" id="fabBtn">➕</button>
            <div class="fab-menu" id="fabMenu">
                <a href="/" class="fab-menu-item"><span>🏠</span> Home</a>
                <a href="/dashboard" class="fab-menu-item"><span>📈</span> Dashboard</a>
                <a href="/search" class="fab-menu-item"><span>🔍</span> Search</a>
                <a href="/orders" class="fab-menu-item"><span>📋</span> Orders</a>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', fabHTML);
        
        const fab = document.getElementById('fabBtn');
        const menu = document.getElementById('fabMenu');
        
        fab.addEventListener('click', () => {
            menu.classList.toggle('active');
            fab.textContent = menu.classList.contains('active') ? '✕' : '➕';
        });
    }
    
    // Command Palette (Ctrl+K)
    function initCommandPalette() {
        const paletteHTML = `
            <div class="command-palette-overlay" id="commandPalette">
                <div class="command-palette">
                    <div class="command-input-wrapper">
                        <span>🔍</span>
                        <input type="text" id="commandInput" placeholder="Type a command or search..." autocomplete="off">
                        <span class="kbd">ESC</span>
                    </div>
                    <div class="command-results" id="commandResults">
                        <div class="command-item" data-href="/">
                            <div class="command-item-icon">🏠</div>
                            <div class="command-item-content">
                                <div class="command-item-title">Go to Home</div>
                                <div class="command-item-desc">Upload files and create orders</div>
                            </div>
                            <div class="command-shortcut"><span class="kbd">Ctrl</span><span class="kbd">H</span></div>
                        </div>
                        <div class="command-item" data-href="/dashboard">
                            <div class="command-item-icon">📈</div>
                            <div class="command-item-content">
                                <div class="command-item-title">Go to Dashboard</div>
                                <div class="command-item-desc">View analytics and insights</div>
                            </div>
                            <div class="command-shortcut"><span class="kbd">Ctrl</span><span class="kbd">D</span></div>
                        </div>
                        <div class="command-item" data-href="/search">
                            <div class="command-item-icon">🔍</div>
                            <div class="command-item-content">
                                <div class="command-item-title">Search Orders</div>
                                <div class="command-item-desc">Find orders with advanced filters</div>
                            </div>
                            <div class="command-shortcut"><span class="kbd">Ctrl</span><span class="kbd">K</span></div>
                        </div>
                        <div class="command-item" data-href="/orders">
                            <div class="command-item-icon">📋</div>
                            <div class="command-item-content">
                                <div class="command-item-title">My Orders</div>
                                <div class="command-item-desc">View your generated orders</div>
                            </div>
                        </div>
                        <div class="command-item" data-href="/last-id">
                            <div class="command-item-icon">🔢</div>
                            <div class="command-item-content">
                                <div class="command-item-title">Last Order ID</div>
                                <div class="command-item-desc">Check latest order ID status</div>
                            </div>
                        </div>
                        <div class="command-item" data-href="/issue-order-id">
                            <div class="command-item-icon">🎯</div>
                            <div class="command-item-content">
                                <div class="command-item-title">Issue Order ID</div>
                                <div class="command-item-desc">Assign IDs to team members</div>
                            </div>
                        </div>
                        <div class="command-item" data-href="/logout">
                            <div class="command-item-icon">🚪</div>
                            <div class="command-item-content">
                                <div class="command-item-title">Logout</div>
                                <div class="command-item-desc">Sign out of your account</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', paletteHTML);
        
        const overlay = document.getElementById('commandPalette');
        const input = document.getElementById('commandInput');
        const results = document.getElementById('commandResults');
        const items = results.querySelectorAll('.command-item');
        let activeIndex = 0;
        
        // Filter commands
        input.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            items.forEach(item => {
                const title = item.querySelector('.command-item-title').textContent.toLowerCase();
                const desc = item.querySelector('.command-item-desc').textContent.toLowerCase();
                item.style.display = (title.includes(query) || desc.includes(query)) ? 'flex' : 'none';
            });
        });
        
        // Navigate with keyboard
        input.addEventListener('keydown', (e) => {
            const visibleItems = [...items].filter(i => i.style.display !== 'none');
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeIndex = Math.min(activeIndex + 1, visibleItems.length - 1);
                updateActiveItem(visibleItems, activeIndex);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIndex = Math.max(activeIndex - 1, 0);
                updateActiveItem(visibleItems, activeIndex);
            } else if (e.key === 'Enter' && visibleItems[activeIndex]) {
                window.location.href = visibleItems[activeIndex].dataset.href;
            }
        });
        
        function updateActiveItem(visibleItems, index) {
            items.forEach(i => i.classList.remove('active'));
            if (visibleItems[index]) {
                visibleItems[index].classList.add('active');
                visibleItems[index].scrollIntoView({ block: 'nearest' });
            }
        }
        
        // Click on items
        items.forEach(item => {
            item.addEventListener('click', () => {
                window.location.href = item.dataset.href;
            });
        });
        
        // Close on overlay click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    }
    
    // Add ripple effect to buttons
    function addRippleEffect() {
        document.querySelectorAll('.btn').forEach(btn => {
            btn.classList.add('ripple');
            btn.addEventListener('click', function(e) {
                const rect = this.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                const ripple = document.createElement('span');
                ripple.className = 'ripple-effect';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';
                
                this.appendChild(ripple);
                setTimeout(() => ripple.remove(), 600);
            });
        });
    }
    
    // Animate counters
    function animateCounters() {
        document.querySelectorAll('[data-count]').forEach(el => {
            const target = parseInt(el.dataset.count);
            const duration = 2000;
            const step = target / (duration / 16);
            let current = 0;
            
            const timer = setInterval(() => {
                current += step;
                if (current >= target) {
                    el.textContent = target;
                    clearInterval(timer);
                } else {
                    el.textContent = Math.floor(current);
                }
            }, 16);
        });
    }
    
    // Stagger animation
    function animateStaggerItems() {
        document.querySelectorAll('.stagger-item').forEach((item, index) => {
            item.style.animationDelay = (index * 0.1) + 's';
        });
    }

    // Toast notification system
    function showToast(message, type = 'info') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icons = { success: '✅', error: '❌', info: 'ℹ️' };
        toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-out forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // Confetti celebration
    function showConfetti() {
        const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#22c55e', '#f97316'];
        for (let i = 0; i < 50; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.cssText = `
                left: ${Math.random() * 100}vw;
                background: ${colors[Math.floor(Math.random() * colors.length)]};
                animation: confettiFall ${2 + Math.random() * 2}s linear forwards;
                animation-delay: ${Math.random() * 0.5}s;
            `;
            document.body.appendChild(confetti);
            setTimeout(() => confetti.remove(), 4000);
        }
    }
    
    // Make functions globally available
    window.showToast = showToast;
    window.showConfetti = showConfetti;

    // Add ripple animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes rippleEffect {
            to { transform: translate(-50%, -50%) scale(20); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K for command palette
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const palette = document.getElementById('commandPalette');
            palette.classList.toggle('active');
            if (palette.classList.contains('active')) {
                document.getElementById('commandInput').focus();
            }
        }
        // Escape to close command palette
        if (e.key === 'Escape') {
            document.getElementById('commandPalette').classList.remove('active');
            document.getElementById('fabMenu').classList.remove('active');
        }
        // Ctrl/Cmd + D for dashboard
        if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
            e.preventDefault();
            window.location.href = '/dashboard';
        }
        // Ctrl/Cmd + H for home
        if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
            e.preventDefault();
            window.location.href = '/';
        }
    });
</script>
"""

THEME_SELECTOR_HTML = """
<div class="theme-selector">
    <select id="theme-switch" title="Change Theme">
        <option value="default">✨ Default</option>
        <option value="dark">🌙 Dark Slate</option>
        <option value="ocean">🌊 Ocean Blue</option>
        <option value="forest">🌲 Forest Green</option>
        <option value="sunset">🌅 Sunset Orange</option>
        <option value="rose">🌹 Rose Pink</option>
        <option value="slate">⚡ Cool Slate</option>
        <option value="nebula">🌌 Nebula Purple</option>
        <option value="lime">🍃 Lime Green</option>
        <option value="copper">🔥 Copper</option>
    </select>
</div>
"""

# Base HTML structure for reuse
def create_page_template(title, body_content, is_card=False, is_container=False):
    container_class = ""
    if is_card:
        container_class = "card"
    elif is_container:
        container_class = "container"

    return f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{title} - Sale Order System</title>
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
      {THEME_CSS_AND_JS}
    </head>
    <body><div class="{container_class}">{body_content}</div></body>
    </html>
    """

# ---------------- Helpers (unchanged) ----------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def cleanup_old_files():
    try:
        current_time = time.time()
        cleanup_threshold = app.config['CLEANUP_INTERVAL_HOURS'] * 3600
        for folder in [app.config['UPLOAD_FOLDER'], app.config['REPORT_FOLDER']]:
            if not os.path.exists(folder):
                continue
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path) and current_time - os.path.getctime(file_path) > cleanup_threshold:
                    try: os.remove(file_path)
                    except OSError as e: app.logger.error(f"Cleanup error: {e}")
    except Exception as e:
        app.logger.error(f"Error during cleanup: {e}")

def format_file_size(size_bytes):
    if size_bytes == 0: return "0 Bytes"
    k = 1024; sizes = ["Bytes","KB","MB","GB"]
    i = int(math.floor(math.log(size_bytes) / math.log(k)))
    return f"{round(size_bytes / pow(k, i), 2)} {sizes[i]}"

def get_db_connection():
    return db_connect(default_sqlite_db_file=app.config['DATABASE_FILE'])

def init_db():
    try:
        init_schema(default_sqlite_db_file=app.config['DATABASE_FILE'])
    except Exception as e:
        app.logger.error(f"DB init error: {e}")

# Ensure DB schema exists when imported under WSGI (PythonAnywhere).
init_db()


def get_client_ip() -> str:
    forwarded = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
    return forwarded or (request.remote_addr or '')


def _date_prefix_days_ago(days: int) -> str:
    """Return YYYY-MM-DD date string for simple TEXT comparisons across SQLite/Postgres."""
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def get_active_session_id(username: str):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT session_id FROM active_sessions WHERE username = ?",
            (username,),
        ).fetchone()
        return row['session_id'] if row else None
    finally:
        conn.close()


def upsert_active_session(username: str, session_id: str) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO active_sessions (username, session_id, issued_at, ip, user_agent)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                session_id = excluded.session_id,
                issued_at = excluded.issued_at,
                ip = excluded.ip,
                user_agent = excluded.user_agent
            """,
            (
                username,
                session_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                get_client_ip(),
                (request.headers.get('User-Agent') or '')[:512],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_active_session_if_match(username: str, session_id: str) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            "DELETE FROM active_sessions WHERE username = ? AND session_id = ?",
            (username, session_id),
        )
        conn.commit()
    finally:
        conn.close()

def get_latest_order_id_global():
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT order_id FROM (SELECT order_id, generated_at as ts FROM sale_orders UNION ALL SELECT order_id, given_at as ts FROM issued_order_ids) q ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row['order_id'] if row else None
    except Exception as e:
        app.logger.error(f"get_latest_order_id_global error: {e}")
        return None

def get_next_suggested_order_id():
    last_id = get_latest_order_id_global()
    if not last_id:
        return datetime.now().strftime("%m-%y-") + "00001"
    try:
        parts = last_id.split('-')
        if len(parts) == 3:
            month_year, num_part = f"{parts[0]}-{parts[1]}", parts[2]
            current_month_year = datetime.now().strftime("%m-%y")
            next_num = int(num_part) + 1 if month_year == current_month_year else 1
            return f"{current_month_year}-{next_num:05d}"
    except (ValueError, IndexError):
        pass
    return datetime.now().strftime("%m-%y-") + "00001"

# ---------------- Authentication ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        uname = request.form.get("username", "").strip()
        pwd = request.form.get("password", "")

        if not uname or not pwd:
            flash("Please enter both username and password.", 'error')
        elif uname in USERS and bcrypt.check_password_hash(USERS[uname], pwd):
            # Clear any existing session data
            session.clear()

            # Rotate session id: new login invalidates old devices automatically.
            new_session_id = uuid.uuid4().hex
            try:
                upsert_active_session(uname, new_session_id)
            except Exception as e:
                app.logger.error(f"Failed to set active session for user {uname}: {e}")
                flash("Login failed due to a server error. Please try again.", "error")
                return redirect(url_for("login"))

            # Set new session
            session['user'] = uname
            session['session_id'] = new_session_id
            session.permanent = True  # Make session permanent with timeout

            app.logger.info(f"User {uname} logged in successfully")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials. Please try again.", 'error')

    messages = get_flashed_messages(with_categories=True)
    message_html = "".join(f'<div class="alert alert-{"error" if cat == "error" else "success"}">{msg}</div>' for cat, msg in messages)
    
    body = f"""
        {THEME_SELECTOR_HTML}
        <div class="login-header">
            <h2>📊 Sale Order System</h2>
            <h5>Designed & Developed by Rajesh Jadoun</h5>
            <p>Please login to continue</p>
        </div>
        {message_html}
        <form method="POST" id="loginForm">
            <div class="form-group">
                <label for="username">👤 Username</label>
                <input type="text" id="username" name="username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label for="password">🔒 Password</label>
                <input type="password" id="password" name="password" required autocomplete="current-password">
            </div>
            <button type="submit" class="btn btn-primary" id="loginButton" style="width: 100%;">
                ✨ Login
            </button>
        </form>
        <script>
            document.getElementById('loginForm').addEventListener('submit', function(e) {{
                const button = document.getElementById('loginButton');
                button.disabled = true;
                button.innerHTML = '⏳ Logging in...';
                setTimeout(() => {{
                    button.disabled = false;
                    button.innerHTML = '✨ Login';
                }}, 2000);
            }});
        </script>
    """
    return create_page_template("Login", body, is_card=True)

@app.route("/logout")
def logout():
    uname = session.get("user")
    session_id = session.get('session_id')
    if uname and session_id:
        try:
            # Only delete if this browser is the currently active session.
            delete_active_session_if_match(uname, session_id)
        except Exception as e:
            app.logger.error(f"Logout DB error for user {uname}: {e}")
        app.logger.info(f"User {uname} logged out")
    
    session.clear()
    flash("You have been logged out successfully.", 'success')
    return redirect(url_for("login"))

# ---------------- Decorators (STRENGTHENED) ----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is in session
        if "user" not in session:
            # If validate_session didn't catch it (e.g. session missing entirely), redirect here.
            # (validate_session handles invalid sessions, but if no session at all, it might just return)
            # Actually validate_session skips if endpoint is login, but for others it checks.
            # But if session is empty, validate_session returns (line 110 'if user in session').
            # So we MUST redirect here if user not in session.
            flash("Please login to access this page.", "error")
            return redirect(url_for("login"))
            
        return f(*args, **kwargs)
    return decorated_function

# ---------------- Routes ----------------
@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        try:
            cleanup_old_files()
            if 'file' not in request.files or request.files['file'].filename == '':
                flash("No file was selected. Please choose a file to upload.", 'error')
                return redirect(url_for('home'))
            file = request.files['file']
            if not allowed_file(file.filename):
                flash("Invalid file type. Please upload Excel files only (.xls or .xlsx).", 'error')
                return redirect(url_for('home'))
            
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            temp_input_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(temp_input_path)
            
            session['temp_file_path'] = temp_input_path
            session['uploaded_filename'] = filename
            session['uploaded_filesize'] = format_file_size(os.path.getsize(temp_input_path))
            session['upload_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return redirect(url_for('order_form'))
        except Exception as e:
            current_app.logger.error(f"Upload error: {e}")
            flash("There was an error processing your file.", "error")
            return redirect(url_for('home'))

    # Check if user is admin
    admin_users = os.getenv('ADMIN_USERS', 'admin').split(',')
    is_admin = session['user'] in admin_users

    body = f"""
    <div class="header">
        <div class="header-controls">{THEME_SELECTOR_HTML}</div>
        <h1><b>📊 Sale Order System</b></h1>
        <p class="tagline"><b>Accurate Orders, Better Business ✨</b></p>
       <h5><strong>Designed & Developed by Rajesh Jadoun ✨</strong></h5>
        <div class="user-info">
            <span>Welcome back, <strong>{session['user']}</strong>! 👋</span>
            <div class="nav-links">
                <a href="/" class="btn btn-secondary">🏠 Home</a>
                <a href="/dashboard" class="btn btn-secondary">📈 Dashboard</a>
                <a href="/orders" class="btn btn-secondary">📋 My Orders</a>
                <a href="/search" class="btn btn-secondary">🔍 Search</a>
                <a href="/additional-order" class="btn btn-secondary">📋 Report</a>
                <a href="/last-id" class="btn btn-secondary">🔢 Last Order ID</a>
                <a href="/issue-order-id" class="btn btn-secondary">🎯 Give Order ID</a>
                {'<a href="/admin" class="btn btn-secondary">⚙️ Admin</a>' if is_admin else ''}
                <a href="/logout" class="btn btn-secondary">🚪 Logout</a>
            </div>
        </div>
    </div>
    <div class="main">
        <form method="POST" enctype="multipart/form-data" id="uploadForm">
            <div class="upload-area" id="uploadArea">
                <div style="font-size: 4rem; margin-bottom: 1rem;">📄</div>
                <div style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--primary-color);">
                    Drag & Drop or Click to Upload
                </div>
                <div style="color: var(--text-muted); font-size: 1rem;">
                    Supports .xls and .xlsx files • Maximum 16MB
                </div>
                <input type="file" name="file" id="fileInput" class="file-input" style="display: none;" accept=".xls,.xlsx" required>
            </div>
            <div class="file-info" id="fileInfo" style="display: none; text-align: left;">
                <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;">
                    <div style="font-size: 2rem;">📊</div>
                    <div style="flex: 1; min-width: 200px;">
                        <div style="font-weight: 700; color: var(--primary-color); margin-bottom: 0.25rem;">
                            <span id="fileName"></span>
                        </div>
                        <div style="color: var(--text-muted); font-size: 0.9rem;">
                            Size: <span id="fileSize"></span> • Ready to process
                        </div>
                    </div>
                    <div style="color: var(--success-text); font-size: 1.5rem;">✅</div>
                </div>
            </div>
            <div style="text-align: center; margin-top: 2rem;">
                <button type="submit" class="upload-button btn btn-primary" id="uploadButton" style="display: none;">
                    🚀 Upload & Continue
                </button>
            </div>
        </form>
    </div>
    
    <script>
        // Page loading optimization - remove heavy animations on load
        document.addEventListener('DOMContentLoaded', function() {{{{
            // Fast file handling without heavy animations
            const uploadArea=document.getElementById('uploadArea'),
                  fileInput=document.getElementById('fileInput'),
                  fileInfo=document.getElementById('fileInfo'),
                  fileName=document.getElementById('fileName'),
                  fileSize=document.getElementById('fileSize'),
                  uploadButton=document.getElementById('uploadButton');
            
            function formatFileSize(bytes) {{{{
                if(bytes === 0) return '0 Bytes';
                const k = 1024, sizes = ['Bytes','KB','MB','GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            }}}}
            
            function handleFile(file) {{{{
                const allowedTypes = ['application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
                const maxSize = 16 * 1024 * 1024;
                
                if (!allowedTypes.includes(file.type) && !file.name.match(/\\.(xls|xlsx)$/i)) {{{{
                    alert('📋 Please select a valid Excel file (.xls or .xlsx)');
                    return false;
                }}}}
                if (file.size > maxSize) {{{{
                    alert('⚠️ File size must be less than 16MB');
                    return false;
                }}}}
                
                fileName.textContent = file.name;
                fileSize.textContent = formatFileSize(file.size);
                fileInfo.style.display = 'block';
                uploadButton.style.display = 'inline-flex';
                uploadArea.style.borderColor = 'var(--primary-color)';
                return true;
            }}}}
            
            uploadArea.onclick = () => fileInput.click();
            fileInput.onchange = e => {{{{
                const file = e.target.files[0];
                if(file) handleFile(file);
            }}}};
            
            uploadArea.ondragover = e => {{{{
                e.preventDefault();
                uploadArea.style.borderColor = 'var(--primary-color)';
            }}}};
            uploadArea.ondragleave = e => {{{{
                e.preventDefault();
                uploadArea.style.borderColor = 'var(--border-color)';
            }}}};
            uploadArea.ondrop = e => {{{{
                e.preventDefault();
                uploadArea.style.borderColor = 'var(--border-color)';
                const file = e.dataTransfer.files[0];
                if(file) {{{{
                    fileInput.files = e.dataTransfer.files;
                    handleFile(file);
                }}}}
            }}}};
            
            document.getElementById('uploadForm').onsubmit = function(e) {{{{
                const button = document.getElementById('uploadButton');
                button.disabled = true;
                button.innerHTML = '⏳ Processing...';
            }}}};
        }}}});
    </script>
    """
    return create_page_template("Dashboard", body, is_container=True)

@app.route('/form', methods=['GET','POST'])
@login_required
def order_form():
    if 'temp_file_path' not in session or not os.path.exists(session['temp_file_path']):
        flash("Please upload an Excel file first.", "error")
        return redirect(url_for('home'))

    if request.method == 'POST':
        try:
            dealer_name = request.form.get('dealer_name','').strip()
            city = request.form.get('city','').strip()
            order_date_raw = request.form.get('order_date','')
            order_date = datetime.strptime(order_date_raw, '%Y-%m-%d').strftime('%d-%m-%Y') if order_date_raw else ""
            freight_condition = request.form.get('freight_condition','').strip()

            df, _, weight_map, hdmr_map, mdf_map, ply_map, pvc_map, wpc_map = prepare_data(session['temp_file_path'])
            
            safe_dealer_name = re.sub(r'[^a-zA-Z0-9_.-]+', '_', dealer_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"{safe_dealer_name}_{timestamp}_SALE_ORDER.xlsx"
            output_path = os.path.join(app.config['REPORT_FOLDER'], report_name)

            write_report(df, output_path, weight_map, hdmr_map, mdf_map, ply_map, pvc_map, wpc_map, 
                         session['user'], dealer_name, city, order_date, freight_condition)

            os.remove(session['temp_file_path'])
            session.pop('temp_file_path', None)
            
            return redirect(url_for('download_report', report_name=report_name))
        except Exception as e:
            current_app.logger.error(f"Generate error: {e}")
            flash("Failed to generate the report. An unexpected error occurred.", "error")
    
    body = f"""
    <div class="header">
        <div class="header-controls">{THEME_SELECTOR_HTML}</div>
        <h1>📝 Order Details</h1>
        <p>Fill in the information to generate your professional sale order</p>
    </div>
    <div class="main">
        <div class="file-info" style="margin-bottom: 2.5rem;">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 2rem;">📊</div>
                <div>
                    <div style="font-weight: 700; color: var(--primary-color);">
                        {session.get('uploaded_filename','N/A')}
                    </div>
                    <div style="color: var(--text-muted); font-size: 0.9rem;">
                        Size: {session.get('uploaded_filesize','N/A')} • Uploaded: {session.get('upload_time','N/A')}
                    </div>
                </div>
            </div>
        </div>
        
        <form method="POST" id="orderForm">
            <div class="grid-form">
                <div class="form-group">
                    <label for="dealer_name">🏢 Dealer Name *</label>
                    <input id="dealer_name" name="dealer_name" required placeholder="Enter dealer name">
                </div>
                <div class="form-group">
                    <label for="city">🌍 City *</label>
                    <input id="city" name="city" required placeholder="Enter city name">
                </div>
                <div class="form-group">
                    <label for="order_date">📅 Order Date *</label>
                    <input type="date" id="order_date" name="order_date" required>
                </div>
                <div class="form-group">
                    <label for="freight_condition">🚚 Freight Condition</label>
                    <input id="freight_condition" name="freight_condition" placeholder="e.g., FOB, CIF, Ex-Works">
                </div>
            </div>
            
            <div class="form-group">
                <label for="additional_notes">📋 Additional Notes</label>
                <textarea id="additional_notes" name="additional_notes" rows="3" 
                    placeholder="Any special instructions or notes for this order..."></textarea>
            </div>
            
            <div style="display: flex; gap: 1.5rem; justify-content: center; margin-top: 2.5rem; flex-wrap: wrap;">
                <a class="btn btn-secondary" href="/">
                    ← Back to Home
                </a>
                <button class="btn btn-primary" type="submit" id="generateButton">
                    🚀 Generate Report
                </button>
            </div>
        </form>
    </div>
    
    <script>
        // Set today's date as default
        document.getElementById('order_date').valueAsDate = new Date();
        
        // Form submission handling
        document.getElementById('orderForm').addEventListener('submit', function(e) {{{{
            const button = document.getElementById('generateButton');
            const dealerName = document.getElementById('dealer_name').value.trim();
            const city = document.getElementById('city').value.trim();
            
            if (!dealerName || !city) {{{{
                e.preventDefault();
                alert('⚠️ Please fill in all required fields');
                return;
            }}}}
            
            button.disabled = true;
            button.innerHTML = '⏳ Generating Report...';
            
            // Add loading animation
            setTimeout(() => {{{{
                if (!button.disabled) return;
                button.innerHTML = '📊 Processing Data...';
            }}}}, 1000);
        }}}});
        
        // Enhanced form validation with real-time feedback
        const inputs = document.querySelectorAll('input[required]');
        inputs.forEach(input => {{{{
            input.addEventListener('blur', function() {{{{
                if (this.value.trim()) {{{{
                    this.style.borderColor = 'var(--success-text)';
                }}}} else {{{{
                    this.style.borderColor = 'var(--error-text)';
                }}}}
            }}}});
            input.addEventListener('focus', function() {{{{
                this.style.borderColor = 'var(--primary-color)';
            }}}});
        }}}});
    </script>
    """
    return create_page_template("Order Details", body, is_container=True)

# ===== ADDITIONAL ORDER ROUTES (Uses existing Order ID) =====
@app.route('/additional-order', methods=['GET', 'POST'])
@login_required
def additional_order():
    """Upload file for additional order that uses existing order ID"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file selected.", "error")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("No file selected.", "error")
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash("Invalid file type. Please upload an Excel file.", "error")
            return redirect(request.url)

        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(temp_path)
        session['additional_temp_file_path'] = temp_path
        session['additional_uploaded_filename'] = file.filename
        session['additional_uploaded_filesize'] = f"{os.path.getsize(temp_path) / 1024:.2f} KB"
        session['additional_upload_time'] = datetime.now().strftime("%d-%m-%Y %H:%M")
        return redirect(url_for('additional_order_form'))
    
    body = f"""
    <div class="header">
        <div class="header-controls">{THEME_SELECTOR_HTML}</div>
        <h1>📋 Report</h1>
        <p>Generate order with existing Order ID</p>
        <div class="nav-links">
            <a href="/" class="btn btn-secondary">🏠 Home</a>
            <a href="/orders" class="btn btn-secondary">📋 My Orders</a>
        </div>
    </div>
    <div class="main">
        <div class="info-card" style="background: linear-gradient(135deg, var(--warning-bg) 0%, var(--accent-bg) 100%); padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem; border-left: 4px solid var(--warning-text);">
            <h3 style="margin-bottom: 0.5rem; color: var(--warning-text);">ℹ️ Additional Order</h3>
            <p style="margin: 0; color: var(--text-color);">This feature allows you to generate a new report using an <strong>existing Order ID</strong> instead of creating a new one. Useful for:</p>
            <ul style="margin: 0.5rem 0 0 1.5rem; color: var(--text-color);">
                <li>Adding more items to an existing order</li>
                <li>Reprinting orders with modifications</li>
                <li>Creating supplementary orders</li>
            </ul>
        </div>
        
        <form method="POST" enctype="multipart/form-data" id="additionalUploadForm">
            <div class="drop-zone" id="dropZone">
                <div class="drop-zone-content">
                    <div style="font-size: 4rem; margin-bottom: 1rem; animation: bounce 2s infinite;">📊</div>
                    <h3 style="margin-bottom: 0.5rem;">Drop your Excel file here</h3>
                    <p style="color: var(--text-muted); margin-bottom: 1.5rem;">or click to browse</p>
                    <input type="file" name="file" id="fileInput" accept=".xlsx,.xls" required style="display: none;">
                    <button type="button" class="btn btn-primary" onclick="document.getElementById('fileInput').click()">
                        📁 Choose File
                    </button>
                </div>
            </div>
            <div id="fileInfo" style="display: none; margin-top: 1rem; padding: 1rem; background: var(--success-bg); border-radius: 8px; border: 1px solid var(--success-text);">
                <span id="fileName" style="font-weight: 600; color: var(--success-text);"></span>
            </div>
            <div style="text-align: center; margin-top: 2rem;">
                <button type="submit" class="btn btn-primary" id="continueBtn" disabled>
                    ➡️ Continue to Order Details
                </button>
            </div>
        </form>
    </div>
    
    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const continueBtn = document.getElementById('continueBtn');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {{{{
            dropZone.addEventListener(event, e => {{{{ e.preventDefault(); e.stopPropagation(); }}}});
        }}}});
        
        ['dragenter', 'dragover'].forEach(event => {{{{
            dropZone.addEventListener(event, () => dropZone.classList.add('drag-over'));
        }}}});
        
        ['dragleave', 'drop'].forEach(event => {{{{
            dropZone.addEventListener(event, () => dropZone.classList.remove('drag-over'));
        }}}});
        
        dropZone.addEventListener('drop', e => {{{{
            fileInput.files = e.dataTransfer.files;
            updateFileInfo();
        }}}});
        
        dropZone.addEventListener('click', () => fileInput.click());
        
        fileInput.addEventListener('change', updateFileInfo);
        
        function updateFileInfo() {{{{
            if (fileInput.files.length > 0) {{{{
                fileName.textContent = '📄 ' + fileInput.files[0].name;
                fileInfo.style.display = 'block';
                continueBtn.disabled = false;
            }}}}
        }}}}
    </script>
    """
    return create_page_template("Additional Order", body, is_container=True)

@app.route('/additional-form', methods=['GET', 'POST'])
@login_required
def additional_order_form():
    """Form for additional order with order ID input"""
    if 'additional_temp_file_path' not in session or not os.path.exists(session['additional_temp_file_path']):
        flash("Please upload an Excel file first.", "error")
        return redirect(url_for('additional_order'))

    if request.method == 'POST':
        try:
            dealer_name = request.form.get('dealer_name', '').strip()
            city = request.form.get('city', '').strip()
            order_date_raw = request.form.get('order_date', '')
            order_date = datetime.strptime(order_date_raw, '%Y-%m-%d').strftime('%d-%m-%Y') if order_date_raw else ""
            freight_condition = request.form.get('freight_condition', '').strip()
            existing_order_id = request.form.get('existing_order_id', '').strip()
            
            if not existing_order_id:
                flash("Please enter an existing Order ID.", "error")
                return redirect(request.url)

            df, _, weight_map, hdmr_map, mdf_map, ply_map, pvc_map, wpc_map = prepare_data(session['additional_temp_file_path'])
            
            safe_dealer_name = re.sub(r'[^a-zA-Z0-9_.-]+', '_', dealer_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"{safe_dealer_name}_{timestamp}_ADDITIONAL_ORDER.xlsx"
            output_path = os.path.join(app.config['REPORT_FOLDER'], report_name)

            write_report(df, output_path, weight_map, hdmr_map, mdf_map, ply_map, pvc_map, wpc_map, 
                         session['user'], dealer_name, city, order_date, freight_condition,
                         custom_order_id=existing_order_id, is_additional_order=True)

            os.remove(session['additional_temp_file_path'])
            session.pop('additional_temp_file_path', None)
            session.pop('additional_uploaded_filename', None)
            session.pop('additional_uploaded_filesize', None)
            session.pop('additional_upload_time', None)
            
            flash(f"✅ Additional order generated with Order ID: {existing_order_id}", "success")
            return redirect(url_for('download_report', report_name=report_name))
        except Exception as e:
            current_app.logger.error(f"Additional order error: {e}")
            flash("Failed to generate the additional order. An unexpected error occurred.", "error")
    
    body = f"""
    <div class="header">
        <div class="header-controls">{THEME_SELECTOR_HTML}</div>
        <h1>📝 Report Details</h1>
        <p>Enter existing Order ID and order details</p>
    </div>
    <div class="main">
        <div class="file-info" style="margin-bottom: 2.5rem;">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 2rem;">📊</div>
                <div>
                    <div style="font-weight: 700; color: var(--primary-color);">
                        {session.get('additional_uploaded_filename','N/A')}
                    </div>
                    <div style="color: var(--text-muted); font-size: 0.9rem;">
                        Size: {session.get('additional_uploaded_filesize','N/A')} • Uploaded: {session.get('additional_upload_time','N/A')}
                    </div>
                </div>
            </div>
        </div>
        
        <form method="POST" id="additionalOrderForm">
            <div class="form-group" style="margin-bottom: 2rem; padding: 1.5rem; background: linear-gradient(135deg, var(--warning-bg) 0%, var(--accent-bg) 100%); border-radius: 12px; border: 2px solid var(--warning-text);">
                <label for="existing_order_id" style="font-size: 1.1rem; font-weight: 700; color: var(--warning-text);">🔢 Existing Order ID *</label>
                <input id="existing_order_id" name="existing_order_id" required 
                    placeholder="e.g., NTWS/2025/0523/01" 
                    style="font-size: 1.1rem; font-weight: 600; text-transform: uppercase;"
                    pattern="[A-Za-z0-9/.-]+"
                    title="Enter the existing order ID (letters, numbers, /, ., - allowed)">
                <small style="color: var(--text-muted); display: block; margin-top: 0.5rem;">
                    💡 Enter the Order ID from the original order you want to add to
                </small>
            </div>
            
            <div class="grid-form">
                <div class="form-group">
                    <label for="dealer_name">🏢 Dealer Name *</label>
                    <input id="dealer_name" name="dealer_name" required placeholder="Enter dealer name">
                </div>
                <div class="form-group">
                    <label for="city">🌍 City *</label>
                    <input id="city" name="city" required placeholder="Enter city name">
                </div>
                <div class="form-group">
                    <label for="order_date">📅 Order Date *</label>
                    <input type="date" id="order_date" name="order_date" required>
                </div>
                <div class="form-group">
                    <label for="freight_condition">🚚 Freight Condition</label>
                    <input id="freight_condition" name="freight_condition" placeholder="e.g., FOB, CIF, Ex-Works">
                </div>
            </div>
            
            <div style="display: flex; gap: 1.5rem; justify-content: center; margin-top: 2.5rem; flex-wrap: wrap;">
                <a class="btn btn-secondary" href="/additional-order">
                    ← Back
                </a>
                <button class="btn btn-primary" type="submit" id="generateButton">
                    📋 Generate Report
                </button>
            </div>
        </form>
    </div>
    
    <script>
        document.getElementById('order_date').valueAsDate = new Date();
        
        document.getElementById('additionalOrderForm').addEventListener('submit', function(e) {{{{
            const button = document.getElementById('generateButton');
            const orderId = document.getElementById('existing_order_id').value.trim();
            const dealerName = document.getElementById('dealer_name').value.trim();
            const city = document.getElementById('city').value.trim();
            
            if (!orderId || !dealerName || !city) {{{{
                e.preventDefault();
                alert('⚠️ Please fill in all required fields including the existing Order ID');
                return;
            }}}}
            
            button.disabled = true;
            button.innerHTML = '⏳ Generating Additional Order...';
        }}}});
        
        // Auto uppercase for order ID
        document.getElementById('existing_order_id').addEventListener('input', function() {{{{
            this.value = this.value.toUpperCase();
        }}}});
    </script>
    """
    return create_page_template("Additional Order Details", body, is_container=True)

@app.route('/download/<path:report_name>')
@login_required
def download_report(report_name):
    path = os.path.join(app.config['REPORT_FOLDER'], report_name)
    if not os.path.exists(path):
        flash("Report not found.", "error")
        return redirect(url_for('home'))
    return send_file(path, as_attachment=True)

@app.route('/orders')
@login_required
def orders():
    try:
        conn = get_db_connection()
        orders = conn.execute(
            "SELECT * FROM sale_orders WHERE username = ? ORDER BY generated_at DESC LIMIT 50",
            (session['user'],)
        ).fetchall()
        conn.close()
    except Exception as e:
        current_app.logger.error(f"Orders fetch error: {e}")
        orders = []

    orders_html = ""
    if orders:
        for order in orders:
            orders_html += f"""
            <div class="order-card" style="background: var(--gradient-accent); border-radius: 16px; padding: 1.5rem; margin-bottom: 1rem; border: 1px solid var(--border-color); transition: all 0.3s ease;">
                <div style="display: flex; justify-content: between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                    <div style="flex: 1; min-width: 200px;">
                        <h3 style="color: var(--primary-color); margin-bottom: 0.5rem;">📋 {order['dealer_name']}</h3>
                        <p style="margin-bottom: 0.25rem;"><strong>🌍 City:</strong> {order['city']}</p>
                        <p style="margin-bottom: 0.25rem;"><strong>🔢 Order ID:</strong> {order['order_id']}</p>
                        <p style="color: var(--text-muted); font-size: 0.9rem;">📅 Generated: {order['generated_at']}</p>
                    </div>
                    <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                        <a href="/download/{order['report_name']}" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.9rem;">
                            📥 Download
                        </a>
                    </div>
                </div>
            </div>
            """
    else:
        orders_html = """
        <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
            <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.5;">📋</div>
            <h3 style="margin-bottom: 0.5rem;">No Orders Yet</h3>
            <p>Your generated orders will appear here</p>
            <a href="/" class="btn btn-primary" style="margin-top: 1.5rem;">🚀 Create First Order</a>
        </div>
        """

    body = f"""
    <div class="header">
        <div class="header-controls">{THEME_SELECTOR_HTML}</div>
        <h1>📋 My Orders</h1>
        <p>View and download your generated sale orders</p>
        <div class="nav-links">
            <a href="/" class="btn btn-secondary">🏠 Home</a>
            <a href="/last-id" class="btn btn-secondary">🔢 Last Order ID</a>
            <a href="/logout" class="btn btn-secondary">🚪 Logout</a>
        </div>
    </div>
    <div class="main">
        {orders_html}
    </div>
    <style>
        .order-card:hover {{{{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px -8px var(--shadow-color);
        }}}}
    </style>
    """
    return create_page_template("My Orders", body, is_container=True)

@app.route('/last-id')
@login_required
def last_id():
    try:
        latest_id = get_latest_order_id_global()
        suggested_id = get_next_suggested_order_id()
        
        conn = get_db_connection()
        recent_orders = conn.execute(
            "SELECT order_id, dealer_name, city, generated_at FROM sale_orders ORDER BY generated_at DESC LIMIT 10"
        ).fetchall()
        conn.close()
    except Exception as e:
        current_app.logger.error(f"Last ID fetch error: {e}")
        latest_id = None
        suggested_id = get_next_suggested_order_id()
        recent_orders = []

    recent_html = ""
    if recent_orders:
        for order in recent_orders:
            recent_html += f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-bottom: 1px solid var(--border-color); transition: all 0.2s ease;">
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: var(--primary-color); margin-bottom: 0.25rem;">
                        {order['order_id']}
                    </div>
                    <div style="font-size: 0.9rem; color: var(--text-muted);">
                        {order['dealer_name']} • {order['city']}
                    </div>
                </div>
                <div style="text-align: right; color: var(--text-muted); font-size: 0.85rem;">
                    {order['generated_at']}
                </div>
            </div>
            """
    else:
        recent_html = """
        <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem; opacity: 0.5;">🔢</div>
            <p>No recent orders found</p>
        </div>
        """

    body = f"""
    <div class="header">
        <div class="header-controls">{THEME_SELECTOR_HTML}</div>
        <h1>🔢 Order ID Status</h1>
        <p>Track your order numbering system</p>
        <div class="nav-links">
            <a href="/" class="btn btn-secondary">🏠 Home</a>
            <a href="/orders" class="btn btn-secondary">📋 My Orders</a>
            <a href="/issue-order-id" class="btn btn-secondary">🎯 Give Order ID</a>
            <a href="/logout" class="btn btn-secondary">🚪 Logout</a>
        </div>
    </div>
    <div class="main">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem; margin-bottom: 2.5rem;">
            <div style="background: var(--gradient-accent); border-radius: 20px; padding: 2rem; border: 1px solid var(--border-color); text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🏷️</div>
                <h3 style="margin-bottom: 0.5rem; color: var(--primary-color);">Latest Order ID</h3>
                <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-dark); margin-bottom: 0.5rem;">
                    {latest_id or "None yet"}
                </div>
                <p style="color: var(--text-muted); font-size: 0.9rem;">Most recently used</p>
            </div>
            
            <div style="background: var(--gradient-accent); border-radius: 20px; padding: 2rem; border: 1px solid var(--border-color); text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🎯</div>
                <h3 style="margin-bottom: 0.5rem; color: var(--primary-color);">Next Suggested ID</h3>
                <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-dark); margin-bottom: 0.5rem;">
                    {suggested_id}
                </div>
                <p style="color: var(--text-muted); font-size: 0.9rem;">Auto-generated sequence</p>
            </div>
        </div>
        
        <div style="background: var(--bg-card); border-radius: 20px; border: 1px solid var(--border-color); overflow: hidden;">
            <div style="padding: 1.5rem; border-bottom: 1px solid var(--border-color); background: var(--gradient-accent);">
                <h3 style="color: var(--primary-color); margin-bottom: 0.5rem;">📊 Recent Order IDs</h3>
                <p style="color: var(--text-muted); margin: 0;">Latest 10 generated orders</p>
            </div>
            <div style="max-height: 400px; overflow-y: auto;">
                {recent_html}
            </div>
        </div>
    </div>
    """
    return create_page_template("Order ID Status", body, is_container=True)

@app.route('/issue-order-id', methods=['GET', 'POST'])
@login_required
def issue_order_id():
    if request.method == 'POST':
        try:
            order_id = request.form.get('order_id', '').strip()
            given_to_name = request.form.get('given_to_name', '').strip()
            dealer_name = request.form.get('dealer_name', '').strip()
            city = request.form.get('city', '').strip()
            
            if not all([order_id, given_to_name]):
                flash("Please fill in all required fields.", "error")
                return redirect(url_for('issue_order_id'))
            
            conn = get_db_connection()
            # Check if order ID already exists
            existing = conn.execute("SELECT * FROM issued_order_ids WHERE order_id = ?", (order_id,)).fetchone()
            if existing:
                flash(f"Order ID {order_id} has already been issued.", "error")
                conn.close()
                return redirect(url_for('issue_order_id'))
            
            # Insert new issued order ID
            conn.execute(
                "INSERT INTO issued_order_ids (order_id, given_to_name, dealer_name, city, given_by_user, given_at) VALUES (?, ?, ?, ?, ?, ?)",
                (order_id, given_to_name, dealer_name, city, session['user'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            conn.close()
            
            flash(f"Order ID {order_id} has been successfully issued to {given_to_name}.", "success")
            return redirect(url_for('issue_order_id_success', order_id=order_id, given_to=given_to_name))
            
        except Exception as e:
            current_app.logger.error(f"Issue order ID error: {e}")
            flash("An error occurred while issuing the order ID.", "error")

    # Get suggested next ID and recent issued IDs
    try:
        suggested_id = get_next_suggested_order_id()
        conn = get_db_connection()
        recent_issued = conn.execute(
            "SELECT * FROM issued_order_ids ORDER BY given_at DESC LIMIT 10"
        ).fetchall()
        conn.close()
    except Exception as e:
        current_app.logger.error(f"Fetch issued IDs error: {e}")
        suggested_id = get_next_suggested_order_id()
        recent_issued = []

    messages = get_flashed_messages(with_categories=True)
    message_html = "".join(f'<div class="alert alert-{"error" if cat == "error" else "success"}">{msg}</div>' for cat, msg in messages)

    recent_html = ""
    if recent_issued:
        for issued in recent_issued:
            recent_html += f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-bottom: 1px solid var(--border-color);">
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: var(--primary-color); margin-bottom: 0.25rem;">
                        {issued['order_id']}
                    </div>
                    <div style="font-size: 0.9rem; color: var(--text-muted);">
                        Given to: {issued['given_to_name']} • {issued['dealer_name'] or 'N/A'}
                    </div>
                </div>
                <div style="text-align: right; color: var(--text-muted); font-size: 0.85rem;">
                    {issued['given_at']}<br>
                    <small>by {issued['given_by_user']}</small>
                </div>
            </div>
            """

    body = f"""
    <div class="header">
        <div class="header-controls">{THEME_SELECTOR_HTML}</div>
        <h1>🎯 Issue Order ID</h1>
        <p>Assign order IDs to team members or dealers</p>
        <div class="nav-links">
            <a href="/" class="btn btn-secondary">🏠 Home</a>
            <a href="/orders" class="btn btn-secondary">📋 My Orders</a>
            <a href="/last-id" class="btn btn-secondary">🔢 Last Order ID</a>
            <a href="/logout" class="btn btn-secondary">🚪 Logout</a>
        </div>
    </div>
    <div class="main">
        {message_html}
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 2rem;">
            <div style="background: var(--gradient-accent); border-radius: 20px; padding: 2rem; border: 1px solid var(--border-color);">
                <h3 style="color: var(--primary-color); margin-bottom: 1rem;">📝 Issue New Order ID</h3>
                <form method="POST" id="issueForm">
                    <div class="form-group">
                        <label for="order_id">🔢 Order ID *</label>
                        <input type="text" id="order_id" name="order_id" value="{suggested_id}" required>
                    </div>
                    <div class="form-group">
                        <label for="given_to_name">👤 Given To *</label>
                        <input type="text" id="given_to_name" name="given_to_name" placeholder="Person's name" required>
                    </div>
                    <div class="form-group">
                        <label for="dealer_name">🏢 Dealer Name</label>
                        <input type="text" id="dealer_name" name="dealer_name" placeholder="Optional dealer name">
                    </div>
                    <div class="form-group">
                        <label for="city">🌍 City</label>
                        <input type="text" id="city" name="city" placeholder="Optional city">
                    </div>
                    <button type="submit" class="btn btn-primary" style="width: 100%;">
                        🎯 Issue Order ID
                    </button>
                </form>
            </div>
            
            <div style="background: var(--bg-card); border-radius: 20px; border: 1px solid var(--border-color); overflow: hidden;">
                <div style="padding: 1.5rem; border-bottom: 1px solid var(--border-color); background: var(--gradient-accent);">
                    <h3 style="color: var(--primary-color); margin-bottom: 0.5rem;">📊 Recently Issued</h3>
                    <p style="color: var(--text-muted); margin: 0;">Last 10 issued order IDs</p>
                </div>
                <div style="max-height: 400px; overflow-y: auto;">
                    {recent_html if recent_html else '<div style="text-align: center; padding: 2rem; color: var(--text-muted);">No issued order IDs yet</div>'}
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('issueForm').addEventListener('submit', function(e) {{{{
            const orderId = document.getElementById('order_id').value.trim();
            const givenTo = document.getElementById('given_to_name').value.trim();
            
            if (!orderId || !givenTo) {{{{
                e.preventDefault();
                alert('⚠️ Please fill in all required fields');
                return;
            }}}}
        }}}});
    </script>
    """
    return create_page_template("Issue Order ID", body, is_container=True)

@app.route('/issue-success')
@login_required
def issue_order_id_success():
    order_id = request.args.get('order_id', '')
    given_to = request.args.get('given_to', '')
    
    if not order_id or not given_to:
        return redirect(url_for('home'))

    body = f"""
    <div style="text-align: center; padding: 3rem; background: var(--gradient-accent); border-radius: 24px; border: 1px solid var(--border-color);">
        <div style="font-size: 5rem; margin-bottom: 1.5rem; animation: checkmark 0.6s ease-in-out;">✅</div>
        <h1 style="color: var(--primary-color); margin-bottom: 1rem;">Order ID Issued Successfully!</h1>
        <div style="background: var(--bg-card); padding: 2rem; border-radius: 16px; margin: 2rem 0; border: 1px solid var(--border-color);">
            <h3 style="color: var(--secondary-color); margin-bottom: 1rem;">📋 Details</h3>
            <p style="font-size: 1.2rem; font-weight: 600; color: var(--primary-color); margin-bottom: 0.5rem;">
                Order ID: <span style="background: var(--gradient-accent); padding: 0.5rem 1rem; border-radius: 8px;">{order_id}</span>
            </p>
            <p style="font-size: 1.1rem; color: var(--text-dark);">
                Given to: <strong>{given_to}</strong>
            </p>
        </div>
        
        <div style="margin: 2rem 0; padding: 1.5rem; background: var(--success-bg); border-radius: 12px; border: 1px solid var(--success-text);">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">⏰</div>
            <p style="color: var(--success-text); font-weight: 600;">
                Redirecting to Home in <span id="countdown" style="font-size: 1.2rem; font-weight: 700;">20</span> seconds...
            </p>
            <div style="width: 100%; height: 6px; background: rgba(0,0,0,0.1); border-radius: 3px; margin: 1rem 0; overflow: hidden;">
                <div id="progress-bar" style="height: 100%; background: var(--success-text); border-radius: 3px; width: 100%; transition: width 20s linear;"></div>
            </div>
        </div>
        
        <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
            <a href="/" class="btn btn-primary">🏠 Go to Home Now</a>
            <a href="/issue-order-id" class="btn btn-secondary">🎯 Issue Another ID</a>
            <button id="cancelTimer" class="btn btn-secondary">⏸️ Cancel Timer</button>
        </div>
    </div>
    
    <style>
        @keyframes checkmark {{{{
            0% {{{{ transform: scale(0) rotate(0deg); opacity: 0; }}}}
            50% {{{{ transform: scale(1.2) rotate(180deg); opacity: 0.8; }}}}
            100% {{{{ transform: scale(1) rotate(360deg); opacity: 1; }}}}
        }}}}
        
        @keyframes pulse {{{{
            0%, 100% {{{{ transform: scale(1); }}}}
            50% {{{{ transform: scale(1.05); }}}}
        }}}}
        
        #countdown {{{{ 
            animation: pulse 1s infinite; 
            color: var(--error-text); 
        }}}}
    </style>
    
    <script>
        let timeLeft = 20;
        let timerId;
        let cancelled = false;
        
        function updateCountdown() {{{{
            if (cancelled) return;
            
            const countdownEl = document.getElementById('countdown');
            const progressBar = document.getElementById('progress-bar');
            
            if (timeLeft > 0) {{{{
                countdownEl.textContent = timeLeft;
                const progressWidth = (timeLeft / 20) * 100;
                progressBar.style.width = progressWidth + '%';
                timeLeft--;
            }}}} else {{{{
                window.location.href = '/';
            }}}}
        }}}}
        
        // Start countdown
        document.addEventListener('DOMContentLoaded', function() {{{{
            // Start progress bar animation
            setTimeout(() => {{{{
                document.getElementById('progress-bar').style.width = '0%';
            }}}}, 100);
            
            // Update countdown every second
            updateCountdown();
            timerId = setInterval(updateCountdown, 1000);
        }}}});
        
        // Cancel timer button
        document.getElementById('cancelTimer').addEventListener('click', function() {{{{
            cancelled = true;
            clearInterval(timerId);
            document.getElementById('progress-bar').style.width = '100%';
            document.getElementById('countdown').textContent = '∞';
            this.style.display = 'none';
            
            // Show success message
            const successMsg = document.createElement('div');
            successMsg.innerHTML = '⏸️ <strong>Timer Cancelled!</strong> Stay on this page as long as you want.';
            successMsg.style.cssText = 'margin-top: 1rem; padding: 1rem; background: var(--gradient-accent); border-radius: 8px; color: var(--primary-color); font-weight: 600;';
            this.parentNode.appendChild(successMsg);
        }}}});
        
        // Keyboard shortcut - ESC to cancel timer
        document.addEventListener('keydown', function(e) {{{{
            if (e.key === 'Escape' && !cancelled) {{{{
                document.getElementById('cancelTimer').click();
            }}}}
        }}}});
    </script>
    """
    
    return create_page_template("Order ID Issued Successfully", body, is_card=True)


# ==================== Advanced Dashboard ====================
@app.route('/dashboard')
@login_required
def dashboard():
    try:
        conn = get_db_connection()
        
        # Stats
        total_orders = conn.execute("SELECT COUNT(*) as c FROM sale_orders").fetchone()['c']
        user_orders = conn.execute(
            "SELECT COUNT(*) as c FROM sale_orders WHERE username = ?", 
            (session['user'],)
        ).fetchone()['c']
        
        today = datetime.now().strftime('%Y-%m-%d')
        today_orders = conn.execute(
            "SELECT COUNT(*) as c FROM sale_orders WHERE generated_at LIKE ?",
            (f"{today}%",)
        ).fetchone()['c']
        
        current_month = datetime.now().strftime('%Y-%m')
        month_orders = conn.execute(
            "SELECT COUNT(*) as c FROM sale_orders WHERE generated_at LIKE ?",
            (f"{current_month}%",)
        ).fetchone()['c']
        
        # Top dealers
        top_dealers = conn.execute("""
            SELECT dealer_name, city, COUNT(*) as cnt 
            FROM sale_orders GROUP BY dealer_name, city 
            ORDER BY cnt DESC LIMIT 5
        """).fetchall()
        
        # Top cities
        top_cities = conn.execute("""
            SELECT city, COUNT(*) as cnt FROM sale_orders 
            GROUP BY city ORDER BY cnt DESC LIMIT 5
        """).fetchall()
        
        # Monthly trend (last 6 months)
        since_6m = _date_prefix_days_ago(183)
        monthly_data = conn.execute("""
            SELECT substr(generated_at, 1, 7) as month, COUNT(*) as cnt 
            FROM sale_orders 
            WHERE generated_at >= ?
            GROUP BY month ORDER BY month ASC
        """, (since_6m,)).fetchall()
        
        # Recent orders
        recent_orders = conn.execute("""
            SELECT order_id, dealer_name, city, generated_at 
            FROM sale_orders ORDER BY generated_at DESC LIMIT 10
        """).fetchall()
        
        conn.close()
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {e}")
        total_orders = user_orders = today_orders = month_orders = 0
        top_dealers = top_cities = monthly_data = recent_orders = []
    
    # Chart data
    chart_labels = [m['month'] for m in monthly_data] if monthly_data else []
    chart_values = [m['cnt'] for m in monthly_data] if monthly_data else []
    
    city_labels = [c['city'] for c in top_cities] if top_cities else []
    city_values = [c['cnt'] for c in top_cities] if top_cities else []
    
    # Build HTML for top dealers
    dealers_html = ""
    for d in top_dealers:
        dealers_html += f"""
        <div style="display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px solid var(--border-color);">
            <div>
                <strong>{d['dealer_name']}</strong>
                <span style="color: var(--text-muted); font-size: 0.85rem;"> • {d['city']}</span>
            </div>
            <span style="background: var(--primary-color); color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                {d['cnt']} orders
            </span>
        </div>
        """
    
    # Recent orders HTML
    recent_html = ""
    for o in recent_orders:
        recent_html += f"""
        <div style="display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px solid var(--border-color);">
            <div>
                <strong style="color: var(--primary-color);">{o['order_id']}</strong>
                <span style="color: var(--text-muted); font-size: 0.85rem;"> - {o['dealer_name']}</span>
            </div>
            <span style="color: var(--text-muted); font-size: 0.85rem;">{o['generated_at'][:10]}</span>
        </div>
        """
    
    # Check admin
    admin_users = os.getenv('ADMIN_USERS', 'admin').split(',')
    is_admin = session['user'] in admin_users

    body = f"""
    <div class="header">
        <div class="header-controls">{THEME_SELECTOR_HTML}</div>
        <h1>📈 Analytics Dashboard</h1>
        <p class="tagline">Real-time insights into your order data</p>
        <div class="nav-links">
            <a href="/" class="btn btn-secondary">🏠 Home</a>
            <a href="/dashboard" class="btn btn-secondary" style="background: rgba(255,255,255,0.2);">📈 Dashboard</a>
            <a href="/orders" class="btn btn-secondary">📋 My Orders</a>
            <a href="/search" class="btn btn-secondary">🔍 Search</a>
            {'<a href="/admin" class="btn btn-secondary">⚙️ Admin</a>' if is_admin else ''}
            <a href="/logout" class="btn btn-secondary">🚪 Logout</a>
        </div>
    </div>
    <div class="main">
        <!-- Stats Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
            <div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 1.5rem; border-radius: 16px; text-align: center;">
                <div style="font-size: 2.5rem; font-weight: 700;">{total_orders}</div>
                <div style="opacity: 0.9;">Total Orders</div>
            </div>
            <div style="background: linear-gradient(135deg, #22c55e, #16a34a); color: white; padding: 1.5rem; border-radius: 16px; text-align: center;">
                <div style="font-size: 2.5rem; font-weight: 700;">{user_orders}</div>
                <div style="opacity: 0.9;">My Orders</div>
            </div>
            <div style="background: linear-gradient(135deg, #f97316, #ea580c); color: white; padding: 1.5rem; border-radius: 16px; text-align: center;">
                <div style="font-size: 2.5rem; font-weight: 700;">{today_orders}</div>
                <div style="opacity: 0.9;">Today's Orders</div>
            </div>
            <div style="background: linear-gradient(135deg, #0ea5e9, #0284c7); color: white; padding: 1.5rem; border-radius: 16px; text-align: center;">
                <div style="font-size: 2.5rem; font-weight: 700;">{month_orders}</div>
                <div style="opacity: 0.9;">This Month</div>
            </div>
        </div>
        
        <!-- Charts Row -->
        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
            <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 1.5rem;">
                <h3 style="color: var(--primary-color); margin-bottom: 1rem;">📊 Monthly Trend</h3>
                <canvas id="monthlyChart" height="200"></canvas>
            </div>
            <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 1.5rem;">
                <h3 style="color: var(--primary-color); margin-bottom: 1rem;">🌍 Top Cities</h3>
                <canvas id="cityChart" height="200"></canvas>
            </div>
        </div>
        
        <!-- Bottom Row -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
            <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 1.5rem;">
                <h3 style="color: var(--primary-color); margin-bottom: 1rem;">🏆 Top Dealers</h3>
                <div style="max-height: 300px; overflow-y: auto;">
                    {dealers_html if dealers_html else '<p style="color: var(--text-muted); text-align: center; padding: 2rem;">No data yet</p>'}
                </div>
            </div>
            <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 1.5rem;">
                <h3 style="color: var(--primary-color); margin-bottom: 1rem;">📋 Recent Orders</h3>
                <div style="max-height: 300px; overflow-y: auto;">
                    {recent_html if recent_html else '<p style="color: var(--text-muted); text-align: center; padding: 2rem;">No orders yet</p>'}
                </div>
            </div>
        </div>
    </div>
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script>
        // Monthly trend chart
        const monthlyCtx = document.getElementById('monthlyChart').getContext('2d');
        new Chart(monthlyCtx, {{{{
            type: 'line',
            data: {{{{
                labels: {chart_labels},
                datasets: [{{{{
                    label: 'Orders',
                    data: {chart_values},
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#6366f1',
                    pointRadius: 5
                }}}}]
            }}}},
            options: {{{{
                responsive: true,
                plugins: {{{{ legend: {{{{ display: false }}}} }}}},
                scales: {{{{
                    y: {{{{ beginAtZero: true, ticks: {{{{ stepSize: 1 }}}} }}}}
                }}}}
            }}}}
        }}}});
        
        // City pie chart
        const cityCtx = document.getElementById('cityChart').getContext('2d');
        new Chart(cityCtx, {{{{
            type: 'doughnut',
            data: {{{{
                labels: {city_labels},
                datasets: [{{{{
                    data: {city_values},
                    backgroundColor: ['#6366f1', '#22c55e', '#f97316', '#0ea5e9', '#ec4899']
                }}}}]
            }}}},
            options: {{{{
                responsive: true,
                plugins: {{{{
                    legend: {{{{ position: 'bottom' }}}}
                }}}}
            }}}}
        }}}});
    </script>
    """
    return create_page_template("Dashboard", body, is_container=True)


# ==================== Advanced Search ====================
@app.route('/search')
@login_required
def search_page():
    query = request.args.get('q', '').strip()
    dealer = request.args.get('dealer', '').strip()
    city = request.args.get('city', '').strip()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    results = []
    searched = False
    
    if query or dealer or city or date_from or date_to:
        searched = True
        try:
            conn = get_db_connection()
            
            conditions = []
            params = []
            
            if query:
                conditions.append("(dealer_name LIKE ? OR city LIKE ? OR order_id LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
            if dealer:
                conditions.append("dealer_name LIKE ?")
                params.append(f"%{dealer}%")
            if city:
                conditions.append("city LIKE ?")
                params.append(f"%{city}%")
            if date_from:
                conditions.append("generated_at >= ?")
                params.append(date_from)
            if date_to:
                conditions.append("generated_at <= ?")
                params.append(f"{date_to} 23:59:59")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            results = conn.execute(f"""
                SELECT * FROM sale_orders WHERE {where_clause}
                ORDER BY generated_at DESC LIMIT 100
            """, tuple(params)).fetchall()
            
            conn.close()
        except Exception as e:
            current_app.logger.error(f"Search error: {e}")
    
    # Build results HTML
    results_html = ""
    if searched:
        if results:
            for r in results:
                results_html += f"""
                <div style="background: var(--gradient-accent); border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; border: 1px solid var(--border-color); transition: all 0.2s ease;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                        <div style="flex: 1; min-width: 200px;">
                            <h4 style="color: var(--primary-color); margin-bottom: 0.5rem;">📋 {r['dealer_name']}</h4>
                            <p style="margin: 0.25rem 0;"><strong>🌍 City:</strong> {r['city']}</p>
                            <p style="margin: 0.25rem 0;"><strong>🔢 Order ID:</strong> {r['order_id']}</p>
                            <p style="color: var(--text-muted); font-size: 0.85rem; margin: 0.25rem 0;">📅 {r['generated_at']} • By: {r['username']}</p>
                        </div>
                        <a href="/download/{r['report_name']}" style="background: var(--primary-color); color: white; padding: 0.5rem 1rem; border-radius: 8px; text-decoration: none; font-weight: 500;">
                            📥 Download
                        </a>
                    </div>
                </div>
                """
        else:
            results_html = '<div style="text-align: center; padding: 3rem; color: var(--text-muted);"><div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div><h3>No results found</h3><p>Try different search terms</p></div>'
    
    # Check admin
    admin_users = os.getenv('ADMIN_USERS', 'admin').split(',')
    is_admin = session['user'] in admin_users

    body = f"""
    <div class="header">
        <div class="header-controls">{THEME_SELECTOR_HTML}</div>
        <h1>🔍 Advanced Search</h1>
        <p class="tagline">Find orders quickly with powerful filters</p>
        <div class="nav-links">
            <a href="/" class="btn btn-secondary">🏠 Home</a>
            <a href="/dashboard" class="btn btn-secondary">📈 Dashboard</a>
            <a href="/orders" class="btn btn-secondary">📋 My Orders</a>
            <a href="/search" class="btn btn-secondary" style="background: rgba(255,255,255,0.2);">🔍 Search</a>
            {'<a href="/admin" class="btn btn-secondary">⚙️ Admin</a>' if is_admin else ''}
            <a href="/logout" class="btn btn-secondary">🚪 Logout</a>
        </div>
    </div>
    <div class="main">
        <!-- Search Form -->
        <div style="background: var(--gradient-accent); border-radius: 16px; padding: 1.5rem; margin-bottom: 2rem; border: 1px solid var(--border-color);">
            <form method="GET" id="searchForm">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
                    <div class="form-group" style="margin: 0;">
                        <label>🔍 Quick Search</label>
                        <input type="text" name="q" value="{query}" placeholder="Search anything..." style="width: 100%;">
                    </div>
                    <div class="form-group" style="margin: 0;">
                        <label>🏢 Dealer Name</label>
                        <input type="text" name="dealer" value="{dealer}" placeholder="Dealer name..." style="width: 100%;">
                    </div>
                    <div class="form-group" style="margin: 0;">
                        <label>🌍 City</label>
                        <input type="text" name="city" value="{city}" placeholder="City name..." style="width: 100%;">
                    </div>
                    <div class="form-group" style="margin: 0;">
                        <label>📅 From Date</label>
                        <input type="date" name="date_from" value="{date_from}" style="width: 100%;">
                    </div>
                    <div class="form-group" style="margin: 0;">
                        <label>📅 To Date</label>
                        <input type="date" name="date_to" value="{date_to}" style="width: 100%;">
                    </div>
                </div>
                <div style="display: flex; gap: 1rem; justify-content: center;">
                    <button type="submit" class="btn btn-primary">🔍 Search</button>
                    <a href="/search" class="btn btn-secondary">↻ Reset</a>
                    <button type="button" class="btn btn-secondary" onclick="exportResults()">📥 Export Results</button>
                </div>
            </form>
        </div>
        
        <!-- Results -->
        {f'<div style="margin-bottom: 1rem; color: var(--text-muted);">Found <strong>{len(results)}</strong> results</div>' if searched else ''}
        <div id="searchResults">
            {results_html if searched else '<div style="text-align: center; padding: 3rem; color: var(--text-muted);"><div style="font-size: 3rem; margin-bottom: 1rem;">🔎</div><h3>Start Searching</h3><p>Use the filters above to find orders</p></div>'}
        </div>
    </div>
    
    <script>
        function exportResults() {{{{
            const params = new URLSearchParams(window.location.search);
            params.set('export', 'true');
            fetch('/api/v1/orders/export?' + params.toString())
                .then(r => r.json())
                .then(data => {{{{
                    if (data.success) {{{{
                        // Create CSV
                        let csv = 'Order ID,Dealer Name,City,Username,Generated At\\n';
                        data.data.forEach(o => {{{{
                            csv += `"${{o.order_id}}","${{o.dealer_name}}","${{o.city}}","${{o.username}}","${{o.generated_at}}"\\n`;
                        }}}});
                        
                        const blob = new Blob([csv], {{{{ type: 'text/csv' }}}});
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'orders_export_' + new Date().toISOString().slice(0,10) + '.csv';
                        a.click();
                    }}}} else {{{{
                        alert('Export failed: ' + data.error);
                    }}}}
                }}}})
                .catch(err => alert('Export failed: ' + err));
        }}}}
    </script>
    """
    return create_page_template("Search", body, is_container=True)


@app.route('/favicon.ico')
def favicon():
    # Return a simple SVG favicon
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
        <rect width="64" height="64" rx="12" fill="#6366f1"/>
        <text x="32" y="45" font-family="Arial, sans-serif" font-size="36" font-weight="bold" text-anchor="middle" fill="white">📊</text>
    </svg>'''
    return svg_content, 200, {'Content-Type': 'image/svg+xml'}

# Additional routes would follow the same pattern...
# For brevity, I'll include the main function and note that other routes follow similar enhancement patterns

# ---------------- Main ----------------
if __name__ == "__main__":
    debug = _env_bool("FLASK_DEBUG", default=_app_env not in {"production", "prod"})
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=debug, host=host, port=port)
