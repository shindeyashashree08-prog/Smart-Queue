

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import datetime
from database import get_db_connection, init_db, hash_password, DB_NAME

app = Flask(__name__)
# Secret key for encrypting session cookies
app.secret_key = "smartqueue_college_project_secret_key_2025"

# Auto-initialize database if it does not exist yet
if not os.path.exists(DB_NAME):
    init_db()

# ----------------- HELPER FUNCTIONS ----------------- #

def get_current_user():
    """Returns the logged-in user details dictionary or None."""
    if 'user_id' not in session:
        return None
    conn = get_db_connection()
    user = conn.execute("SELECT id, fullname, email, phone FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return user

def calculate_queue_info(token_id, service_id):
    """
    Calculates queue metrics for a given token:
    1. The token currently being served/called.
    2. How many people are ahead in the waiting line.
    3. Estimated waiting time in minutes based on service average time.
    4. Whether this token is currently called.
    """
    conn = get_db_connection()
    service = conn.execute("SELECT * FROM services WHERE id = ?", (service_id,)).fetchone()
    token = conn.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()

    if not service or not token:
        conn.close()
        return None

    # Find the token currently serving or called at the counter for this service
    serving_token_row = conn.execute(
        "SELECT token_number FROM tokens WHERE service_id = ? AND status IN ('called', 'Serving') ORDER BY called_at DESC LIMIT 1",
        (service_id,)
    ).fetchone()
    serving_token = serving_token_row['token_number'] if serving_token_row else "None (Waiting for Next)"

    # Count people waiting ahead: status is 'Waiting' and token id is smaller (created earlier)
    ahead_count_row = conn.execute(
        "SELECT COUNT(*) as count FROM tokens WHERE service_id = ? AND status = 'Waiting' AND id < ?",
        (service_id, token_id)
    ).fetchone()
    people_ahead = ahead_count_row['count'] if ahead_count_row else 0

    avg_time = service['avg_time_mins']
    
    is_called = token['status'] in ('called', 'Serving')
    if is_called:
        est_wait = 0
        message = "It is your turn! Please proceed to the service counter."
    elif token['status'] == 'Waiting':
        est_wait = (people_ahead + (1 if serving_token_row else 0)) * avg_time
        message = f"Approximately {est_wait} minutes remaining."
    else:
        est_wait = 0
        message = f"Token is {token['status']}."

    conn.close()
    return {
        "token_id": token['id'],
        "token_number": token['token_number'],
        "status": token['status'],
        "is_called": is_called,
        "service_name": service['name'],
        "avg_time": avg_time,
        "serving_token": serving_token,
        "people_ahead": people_ahead,
        "estimated_wait_time": est_wait,
        "status_message": message
    }


# ----------------- PUBLIC ROUTES ----------------- #

@app.route('/')
def index():
    """Landing Home Page with overview, features, and college project info."""
    conn = get_db_connection()
    services = conn.execute("SELECT * FROM services WHERE is_active = 1").fetchall()
    
    # Calculate live system stats to display on home page
    total_tokens = conn.execute("SELECT COUNT(*) as total FROM tokens").fetchone()['total']
    completed_tokens = conn.execute("SELECT COUNT(*) as completed FROM tokens WHERE status = 'Completed'").fetchone()['completed']
    active_tokens = conn.execute("SELECT COUNT(*) as active FROM tokens WHERE status IN ('Waiting', 'called', 'Serving')").fetchone()['active']
    conn.close()

    stats = {
        "total_served": completed_tokens,
        "active_queue": active_tokens,
        "total_registered": total_tokens
    }
    return render_template('index.html', services=services, stats=stats)


# ----------------- USER AUTHENTICATION ----------------- #

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User Registration Route."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        fullname = request.form.get('fullname', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not fullname or not email or not phone or not password:
            flash("All fields are required. Please fill in all information.", "danger")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter carefully.", "danger")
            return render_template('register.html')

        if len(password) < 4:
            flash("Password must be at least 4 characters long.", "warning")
            return render_template('register.html')

        conn = get_db_connection()
        existing_user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            conn.close()
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for('login'))

        hashed = hash_password(password)
        conn.execute(
            "INSERT INTO users (fullname, email, phone, password) VALUES (?, ?, ?, ?)",
            (fullname, email, phone, hashed)
        )
        conn.commit()
        conn.close()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User Login Route."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template('login.html')

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and user['password'] == hash_password(password):
            session['user_id'] = user['id']
            session['user_name'] = user['fullname']
            session['user_email'] = user['email']
            flash(f"Welcome back, {user['fullname']}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    """User Logout Route."""
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)
    flash("You have been safely logged out.", "info")
    return redirect(url_for('index'))


# ----------------- USER DASHBOARD & TOKEN ACTIONS ----------------- #

@app.route('/dashboard')
def dashboard():
    """
    User Dashboard:
    - View active waiting / serving tokens with live queue metrics.
    - Select a service to generate a new queue token.
    - View past token history.
    """
    if 'user_id' not in session:
        flash("Please log in to access your queue dashboard.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    # Fetch available services
    services = conn.execute("SELECT * FROM services WHERE is_active = 1 ORDER BY id ASC").fetchall()

    # Fetch active tokens for this user (Waiting, called, or Serving)
    active_tokens_rows = conn.execute(
        """
        SELECT t.*, s.name as service_name, s.avg_time_mins, s.prefix
        FROM tokens t
        JOIN services s ON t.service_id = s.id
        WHERE t.user_id = ? AND t.status IN ('Waiting', 'called', 'Serving')
        ORDER BY t.id DESC
        """,
        (user_id,)
    ).fetchall()

    active_tokens = []
    for row in active_tokens_rows:
        queue_data = calculate_queue_info(row['id'], row['service_id'])
        active_tokens.append({
            "id": row['id'],
            "token_number": row['token_number'],
            "service_name": row['service_name'],
            "status": row['status'],
            "is_called": queue_data['is_called'] if queue_data else (row['status'] in ('called', 'Serving')),
            "created_at": row['created_at'],
            "serving_token": queue_data['serving_token'] if queue_data else "None",
            "people_ahead": queue_data['people_ahead'] if queue_data else 0,
            "estimated_wait_time": queue_data['estimated_wait_time'] if queue_data else 0,
            "status_message": queue_data['status_message'] if queue_data else ""
        })

    # Fetch previous tokens history (Completed, Cancelled, Skipped)
    history_tokens = conn.execute(
        """
        SELECT t.*, s.name as service_name
        FROM tokens t
        JOIN services s ON t.service_id = s.id
        WHERE t.user_id = ? AND t.status NOT IN ('Waiting', 'called', 'Serving')
        ORDER BY t.id DESC
        LIMIT 10
        """,
        (user_id,)
    ).fetchall()

    conn.close()
    return render_template('dashboard.html', services=services, active_tokens=active_tokens, history_tokens=history_tokens)


@app.route('/generate_token/<int:service_id>', methods=['POST'])
def generate_token(service_id):
    """Generates a sequential token for the selected service."""
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    # Check if the service exists
    service = conn.execute("SELECT * FROM services WHERE id = ? AND is_active = 1", (service_id,)).fetchone()
    if not service:
        conn.close()
        flash("Selected service is currently unavailable.", "danger")
        return redirect(url_for('dashboard'))

    # Prevent duplicate active tokens for the same user in the same service
    existing = conn.execute(
        "SELECT id, token_number FROM tokens WHERE user_id = ? AND service_id = ? AND status IN ('Waiting', 'called', 'Serving')",
        (user_id, service_id)
    ).fetchone()

    if existing:
        conn.close()
        flash(f"You already hold an active token ({existing['token_number']}) for {service['name']}.", "info")
        return redirect(url_for('dashboard'))

    # Calculate sequential token number (e.g. HOSP-101, HOSP-102)
    count_row = conn.execute("SELECT COUNT(*) as count FROM tokens WHERE service_id = ?", (service_id,)).fetchone()
    sequence_num = 100 + count_row['count'] + 1
    token_number = f"{service['prefix']}-{sequence_num}"

    # Insert new token
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tokens (token_number, user_id, service_id, status) VALUES (?, ?, ?, 'Waiting')",
        (token_number, user_id, service_id)
    )
    token_id = cursor.lastrowid

    # Record action in queue_history audit trail
    cursor.execute(
        "INSERT INTO queue_history (token_id, action, notes) VALUES (?, 'Created', 'Token generated by user')",
        (token_id,)
    )

    conn.commit()
    conn.close()

    flash(f"Token {token_number} generated successfully for {service['name']}!", "success")
    return redirect(url_for('dashboard'))


@app.route('/cancel_token/<int:token_id>', methods=['POST'])
def cancel_token(token_id):
    """Allows user to cancel their waiting token."""
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    token = conn.execute("SELECT * FROM tokens WHERE id = ? AND user_id = ?", (token_id, user_id)).fetchone()
    if not token:
        conn.close()
        flash("Token not found or unauthorized.", "danger")
        return redirect(url_for('dashboard'))

    if token['status'] != 'Waiting':
        conn.close()
        flash(f"Cannot cancel token {token['token_number']} because it is already {token['status']}.", "warning")
        return redirect(url_for('dashboard'))

    cursor = conn.cursor()
    cursor.execute("UPDATE tokens SET status = 'Cancelled' WHERE id = ?", (token_id,))
    cursor.execute(
        "INSERT INTO queue_history (token_id, action, notes) VALUES (?, 'Cancelled', 'Token cancelled by user')",
        (token_id,)
    )
    conn.commit()
    conn.close()

    flash(f"Token {token['token_number']} has been cancelled.", "info")
    return redirect(url_for('dashboard'))


# ----------------- REAL-TIME API ENDPOINTS ----------------- #

@app.route('/api/queue_status/<int:token_id>')
def api_queue_status(token_id):
    """
    JSON API for live client-side status polling via JavaScript.
    Validates that customers can only access their own token information.
    """
    if 'user_id' not in session and not session.get('admin_logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    if session.get('admin_logged_in'):
        token = conn.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()
    else:
        token = conn.execute(
            "SELECT * FROM tokens WHERE id = ? AND user_id = ?",
            (token_id, session['user_id'])
        ).fetchone()

    if not token:
        conn.close()
        return jsonify({"error": "Token not found or unauthorized access"}), 404

    data = calculate_queue_info(token_id, token['service_id'])
    conn.close()
    return jsonify(data)


@app.route('/api/my_active_tokens')
def api_my_active_tokens():
    """
    Returns live queue status for all active tokens belonging to the logged-in customer.
    Enables multi-token simultaneous tracking with security checks.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    tokens = conn.execute(
        "SELECT id, service_id FROM tokens WHERE user_id = ? AND status IN ('Waiting', 'called', 'Serving')",
        (session['user_id'],)
    ).fetchall()

    results = []
    for t in tokens:
        info = calculate_queue_info(t['id'], t['service_id'])
        if info:
            results.append(info)
    conn.close()
    return jsonify({"tokens": results})


# ----------------- ADMIN PORTAL ----------------- #

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin Login Portal."""
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        conn.close()

        if admin and admin['password'] == hash_password(password):
            session['admin_logged_in'] = True
            session['admin_username'] = admin['username']
            session['admin_role'] = admin['role']
            flash("Admin login successful. Welcome to the Control Panel!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid administrator credentials.", "danger")

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Admin Logout."""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    session.pop('admin_role', None)
    flash("Administrator logged out successfully.", "info")
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
def admin_dashboard():
    """
    Admin Dashboard:
    - Live service counter monitor
    - Call Next Token button
    - Mark Completed & Skip buttons
    - Queue statistics & full token audit log
    """
    if not session.get('admin_logged_in'):
        flash("Administrator access required. Please log in.", "warning")
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    services = conn.execute("SELECT * FROM services ORDER BY id ASC").fetchall()

    # Get optional service filter from URL query string
    selected_service_id = request.args.get('service_id', type=int)
    if not selected_service_id and services:
        selected_service_id = services[0]['id']

    # Statistics Calculation
    total_tokens = conn.execute("SELECT COUNT(*) as c FROM tokens").fetchone()['c']
    waiting_tokens = conn.execute("SELECT COUNT(*) as c FROM tokens WHERE status = 'Waiting'").fetchone()['c']
    serving_tokens = conn.execute("SELECT COUNT(*) as c FROM tokens WHERE status IN ('called', 'Serving')").fetchone()['c']
    completed_tokens = conn.execute("SELECT COUNT(*) as c FROM tokens WHERE status = 'Completed'").fetchone()['c']
    cancelled_tokens = conn.execute("SELECT COUNT(*) as c FROM tokens WHERE status IN ('Cancelled', 'Skipped')").fetchone()['c']

    stats = {
        "total": total_tokens,
        "waiting": waiting_tokens,
        "serving": serving_tokens,
        "completed": completed_tokens,
        "cancelled": cancelled_tokens
    }

    # Fetch token currently serving/called for selected service
    current_serving = conn.execute(
        """
        SELECT t.*, u.fullname, u.phone, u.email, s.name as service_name
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN services s ON t.service_id = s.id
        WHERE t.service_id = ? AND t.status IN ('called', 'Serving')
        ORDER BY t.called_at DESC
        LIMIT 1
        """,
        (selected_service_id,)
    ).fetchone()

    # Fetch waiting queue for selected service
    waiting_list = conn.execute(
        """
        SELECT t.*, u.fullname, u.phone, s.name as service_name
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN services s ON t.service_id = s.id
        WHERE t.service_id = ? AND t.status = 'Waiting'
        ORDER BY t.id ASC
        """,
        (selected_service_id,)
    ).fetchall()

    # Fetch recent tokens list (all services)
    recent_tokens = conn.execute(
        """
        SELECT t.*, u.fullname, u.phone, s.name as service_name
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN services s ON t.service_id = s.id
        ORDER BY t.id DESC
        LIMIT 25
        """
    ).fetchall()

    conn.close()

    return render_template(
        'admin_dashboard.html',
        services=services,
        selected_service_id=selected_service_id,
        stats=stats,
        current_serving=current_serving,
        waiting_list=waiting_list,
        recent_tokens=recent_tokens
    )


@app.route('/admin/call_next/<int:service_id>', methods=['POST'])
def admin_call_next(service_id):
    """
    Calls the next waiting token:
    1. If a token is already called or serving, automatically marks it as 'Completed'.
    2. Finds the oldest 'Waiting' token for this service and sets status to 'called'.
    """
    if not session.get('admin_logged_in'):
        flash("Administrator access required.", "danger")
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Mark any currently serving/called token in this service as Completed
    active_serving = conn.execute(
        "SELECT id, token_number FROM tokens WHERE service_id = ? AND status IN ('called', 'Serving')",
        (service_id,)
    ).fetchall()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item in active_serving:
        cursor.execute("UPDATE tokens SET status = 'Completed', completed_at = ? WHERE id = ?", (now, item['id']))
        cursor.execute(
            "INSERT INTO queue_history (token_id, action, notes) VALUES (?, 'Completed', 'Auto-completed on calling next token')",
            (item['id'],)
        )

    # Find the next waiting token
    next_token = conn.execute(
        "SELECT id, token_number FROM tokens WHERE service_id = ? AND status = 'Waiting' ORDER BY id ASC LIMIT 1",
        (service_id,)
    ).fetchone()

    
    if next_token:
        # Update token status to 'called'
        cursor.execute(
            "UPDATE tokens SET status = 'called', called_at = ? WHERE id = ?",
            (now, next_token['id'])
        )

        cursor.execute(
            "INSERT INTO queue_history (token_id, action, notes) VALUES (?, 'Called', 'Token called to counter by administrator')",
            (next_token['id'],)
        )

        conn.commit()
        flash(f"Token {next_token['token_number']} called to Counter!", "success")
    else:
        conn.commit()
        flash("No waiting customers in the queue for this service.", "info")

    conn.close()
    return redirect(url_for('admin_dashboard', service_id=service_id))



@app.route('/admin/mark_completed/<int:token_id>', methods=['POST'])
def admin_mark_completed(token_id):
    """Marks a serving or waiting token as Completed."""
    if not session.get('admin_logged_in'):
        flash("Administrator access required.", "danger")
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    token = conn.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()

    if token:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE tokens SET status = 'Completed', completed_at = ? WHERE id = ?", (now, token_id))
        cursor.execute(
            "INSERT INTO queue_history (token_id, action, notes) VALUES (?, 'Completed', 'Marked completed by admin')",
            (token_id,)
        )
        conn.commit()
        flash(f"Token {token['token_number']} marked as Completed.", "success")
    else:
        flash("Token not found.", "danger")

    service_id = token['service_id'] if token else None
    conn.close()
    return redirect(url_for('admin_dashboard', service_id=service_id))


@app.route('/admin/skip_token/<int:token_id>', methods=['POST'])
def admin_skip_token(token_id):
    """Marks a token as Skipped (customer was absent or not ready)."""
    if not session.get('admin_logged_in'):
        flash("Administrator access required.", "danger")
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    token = conn.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()

    if token:
        cursor.execute("UPDATE tokens SET status = 'Skipped' WHERE id = ?", (token_id,))
        cursor.execute(
            "INSERT INTO queue_history (token_id, action, notes) VALUES (?, 'Skipped', 'Customer skipped / absent')",
            (token_id,)
        )
        conn.commit()
        flash(f"Token {token['token_number']} marked as Skipped.", "warning")
    else:
        flash("Token not found.", "danger")

    service_id = token['service_id'] if token else None
    conn.close()
    return redirect(url_for('admin_dashboard', service_id=service_id))


# ----------------- APPLICATION ENTRYPOINT ----------------- #

if __name__ == '__main__':
    # Running in debug mode allows live code reloading
    print("=" * 60)
    print(" SmartQueue Web Application Starting...")
    print(" College Mini Project: AI & DS Department")
    print(" Student: Yashashri Shekhar Shinde (Roll 437, PRN 24062171263077)")
    print(" Project Guide: S. R. Pol Mam")
    print(" Access Web App at: http://127.0.0.1:5000")
    print(" Admin Portal at:   http://127.0.0.1:5000/admin/login")
    print("=" * 60)
    app.run(debug=True, port=5000)
