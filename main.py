import os
import smtplib
import secrets
import datetime
from datetime import date, timedelta
from flask import Flask, render_template, request, url_for, redirect, flash, jsonify, session
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor, CKEditorField
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL, Email, Length, EqualTo
from flask_wtf.csrf import CSRFProtect
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_mail import Mail, Message
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Initialize Flask extensions without the app
db = SQLAlchemy()
login_manager = LoginManager()
ckeditor = CKEditor()
mail = Mail()

csrf = CSRFProtect()


# Form for creating/editing a blog post
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


# Form for user registration
class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    submit = SubmitField("Register")


# Form for user login
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


# Form for comments
class CommentForm(FlaskForm):
    text = StringField("Comment", validators=[DataRequired()],
                       render_kw={"placeholder": "Write your comment here...", "class": "form-control"})
    submit = SubmitField("Submit Comment")


# Form for requesting a password reset
class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()],
                        render_kw={"placeholder": "Enter your email address"})
    submit = SubmitField("Send Reset Link")


# Form for resetting the password
class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long")
    ], render_kw={"placeholder": "Enter your new password"})
    confirm_password = PasswordField("Confirm New Password", validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ], render_kw={"placeholder": "Confirm your new password"})
    submit = SubmitField("Reset Password")


# Define models
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    image_url = db.Column(db.String(250), nullable=False)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    post_id = db.Column(db.Integer, nullable=False)


def create_app():
    app = Flask(__name__)

    # Secret key from environment variable
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

    # # Database configuration - Use PostgreSQL in production, SQLite in development
    # if os.getenv('DATABASE_URL'):
    #     # For production with PostgreSQL
    #     db_url = os.getenv('DATABASE_URL', '')
    #     # Remove sslmode if present in the URL to add our own parameters
    #     if '?' in db_url:
    #         db_url = db_url.split('?')[0]
    #
    #     app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    #
    #     # Add robust connection options for PostgreSQL
    #     app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    #         'connect_args': {
    #             'sslmode': 'prefer',  # Try other modes if this doesn't work: disable, allow, require
    #             'connect_timeout': 10,
    #             'keepalives': 1,
    #             'keepalives_idle': 30,
    #             'keepalives_interval': 10,
    #             'keepalives_count': 5
    #         },
    #         'pool_pre_ping': True,
    #         'pool_recycle': 300,
    #         'pool_size': 5,
    #         'max_overflow': 10
    #     }
    # else:
    #     # For development with SQLite
    #     db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blog.db")
    #     app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    if os.getenv('DATABASE_URL'):
        # For production with PostgreSQL (currently commented out in .env)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', '').replace(
            'postgres://', 'postgresql://')
    else:
        # For development with SQLite
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blog.db")
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    # Add connection pooling settings
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,  # Recycle connections after 5 minutes
        'pool_timeout': 30,  # Connection timeout of 30 seconds
        'pool_size': 10  # Maximum pool size
    }

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Add CKEditor configuration lines
    app.config['CKEDITOR_ENABLE_CSRF'] = True
    app.config['CKEDITOR_PKG_TYPE'] = 'standard'  # This will disable the notification banner
    app.config['CKEDITOR_SERVE_LOCAL'] = True
    app.config['CKEDITOR_HEIGHT'] = 400

    # Configure email settings
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USE_SSL=False,
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.getenv('MAIL_DEFAULT_SENDER')
    )

    # Initialize extensions with the app
    db.init_app(app)
    ckeditor.init_app(app)
    Bootstrap(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'login'



    # Check if reset token columns need to be added
    with app.app_context():
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]

            if 'reset_token' not in columns:
                db.session.execute('ALTER TABLE users ADD COLUMN reset_token VARCHAR(100)')
                print("Added reset_token column to users table")

            if 'reset_token_expiry' not in columns:
                db.session.execute('ALTER TABLE users ADD COLUMN reset_token_expiry DATETIME')
                print("Added reset_token_expiry column to users table")

            db.session.commit()
        except Exception as e:
            print(f"Error updating database schema: {e}")
            # Continue with application startup even if schema update fails

    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def safe_query(model, action='all', **kwargs):
        """Execute a query with error handling and retries."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if action == 'all':
                    return model.query.all()
                elif action == 'filter_by':
                    return model.query.filter_by(**kwargs).all()
                # Add more actions as needed
            except Exception as e:
                print(f"Database query error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    # Last attempt failed, return empty list
                    return []
                # Small delay before retry
                import time
                time.sleep(1)

    # Routes

    # Get NM Player rankings routes
    @app.route('/api/nm_players')
    def nm_players():
        try:
            with open('static/data/nm_players.json', 'r') as f:
                data = json.load(f)
            return jsonify(data)
        except FileNotFoundError:
            return jsonify({'error': 'Rankings data not found'}), 404

    # Password reset routes
    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        form = ForgotPasswordForm()
        current_year = datetime.now().year

        if form.validate_on_submit():
            email = form.email.data
            user = User.query.filter_by(email=email).first()

            if user:
                # Generate a secure token
                token = secrets.token_urlsafe(32)

                # Store the token in the database with expiry time (24 hours)
                user.reset_token = token
                user.reset_token_expiry = datetime.now() + timedelta(hours=24)
                db.session.commit()

                # Create the reset link
                reset_link = url_for('reset_password', token=token, _external=True)

                # Send the email with reset link
                try:
                    msg = Message('Password Reset Request',
                                  recipients=[email])
                    msg.body = f'''To reset your password, visit the following link:
{reset_link}

This link is valid for 24 hours.

If you did not make this request, simply ignore this email.

Thanks,
The Pinball Wizard's Corner Team
'''
                    mail.send(msg)

                    flash('A password reset link has been sent to your email address. It will expire in 24 hours.',
                          'success')
                    return redirect(url_for('login'))
                except Exception as e:
                    print(f"Error sending email: {e}")
                    flash('There was an error sending the password reset email. Please try again later.', 'danger')
            else:
                # Don't reveal if the user exists for security reasons
                flash('If an account with that email exists, a password reset link has been sent.', 'info')

        return render_template('forgot_password.html', form=form, current_year=current_year)

    @app.route('/reset-password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        current_year = datetime.now().year

        # Check if token is valid
        user = User.query.filter_by(reset_token=token).first()

        if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.now():
            flash('The password reset link is invalid or has expired.', 'danger')
            return redirect(url_for('forgot_password'))

        form = ResetPasswordForm()

        if form.validate_on_submit():
            # Hash the new password
            hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)

            # Update user's password
            user.password = hashed_password
            user.reset_token = None
            user.reset_token_expiry = None
            db.session.commit()

            flash('Your password has been updated! You can now log in with your new password.', 'success')
            return redirect(url_for('login'))

        return render_template('reset_password.html', form=form, current_year=current_year)

    @app.route('/')
    def root_home():
        return redirect(url_for('home'))
    @app.route('/home')
    def home():
        posts = safe_query(BlogPost)
        current_year = datetime.datetime.now().year
        return render_template("home.html", posts=posts, current_page='home', current_year=current_year)

    @app.route('/about')
    def about():
        current_year = datetime.datetime.now().year
        return render_template("about.html", current_page='about', current_year=current_year)

    @app.route('/blog')
    def blog():
        posts = safe_query(BlogPost)
        current_year = datetime.datetime.now().year
        return render_template("blog.html", posts=posts, current_page='blog', current_year=current_year)

    @app.route('/contact')
    def contact():
        current_year = datetime.datetime.now().year
        return render_template("contact.html", current_page='contact', current_year=current_year)

    @app.route('/post/<int:post_id>', methods=["GET", "POST"])
    def show_post(post_id):
        requested_post = BlogPost.query.get_or_404(post_id)
        comments = Comment.query.filter_by(post_id=post_id).all()
        form = CommentForm()
        current_year = datetime.datetime.now().year

        if form.validate_on_submit():
            if not current_user.is_authenticated:
                flash("Please log in to comment.", "error")
                return redirect(url_for('login'))

            new_comment = Comment(
                text=form.text.data,
                author=current_user.name,
                date=date.today().strftime("%B %d, %Y"),
                post_id=post_id
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=post_id))

        return render_template("post.html", post=requested_post, form=form, comments=comments, current_page='post',
                               current_year=current_year)

    @app.route('/tournaments')
    def tournaments():
        current_year = datetime.datetime.now().year

        try:
            # Load NACS standings data
            nacs_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          'static', 'data', 'nm_nacs_standings_2025.json')
            print(f"Attempting to load NACS standings from: {nacs_file_path}")

            with open(nacs_file_path, 'r') as f:
                nacs_data = json.load(f)

            # Get top 20 players from NACS standings
            nacs_players = nacs_data.get('standings', [])[:20]
            updated = nacs_data.get('updated', 'Unknown')

            # Load WPPR data
            wppr_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          'static', 'data', 'nm_combined_rankings_2025.json')
            print(f"Attempting to load combined rankings from: {wppr_file_path}")

            wppr_lookup = {}

            try:
                with open(wppr_file_path, 'r') as f:
                    combined_data = json.load(f)
                    combined_players = combined_data.get('players', [])

                    # Create lookup dictionary by player_id
                    for player in combined_players:
                        # Use exact player name as key
                        wppr_lookup[player['name']] = player.get('current_wppr_rank', '-')

                    print(f"Successfully loaded {len(combined_players)} players from combined data")
            except Exception as e:
                print(f"Error loading combined data: {e}")

            # Create list of players with WPPR ranks
            processed_players = []
            for player in nacs_players:
                player_data = {
                    'series_rank': player['series_rank'],
                    'player_name': player['player_name'],
                    'city': player['city'],
                    'stateprov_code': player['stateprov_code'],
                    'wppr_points': player['wppr_points'],
                    'event_count': player['event_count'],
                    'win_count': player['win_count'],
                    'wppr_rank': wppr_lookup.get(player['player_name'], '-')
                }
                processed_players.append(player_data)

            print(f"Successfully processed {len(processed_players)} players")

        except Exception as e:
            print(f"Error loading player data: {e}")
            processed_players = []
            updated = 'Unknown'

        return render_template("tournaments.html",
                               current_page='tournaments',
                               current_year=current_year,
                               nm_players=processed_players,
                               last_updated=updated)
    @app.route('/tips')
    def tips():
        current_year = datetime.datetime.now().year
        return render_template("tips.html", current_page='tips', current_year=current_year)

    @app.route('/machines')
    def machines():
        current_year = datetime.datetime.now().year
        return render_template("machines.html", current_page='machines', current_year=current_year)

    @app.route('/send_message', methods=['POST'])
    def submit():
        form_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'topic': request.form.get('topic'),
            'message': request.form.get('message')
        }

        # Create email content
        email_body = f"""
        New Contact Form Submission:

        Name: {form_data['name']}
        Email: {form_data['email']}
        Topic: {form_data['topic']}
        Message: {form_data['message']}
        """

        # Get email credentials from environment variables
        my_email = os.getenv('MAIL_USERNAME')
        my_password = os.getenv('MAIL_PASSWORD')
        smtp_server = "smtp.gmail.com"  # Changed to Gmail server
        smtp_port = 587

        # Create message
        msg = MIMEMultipart()
        msg['From'] = my_email
        msg['To'] = my_email
        msg['Subject'] = f"New Contact Form Submission - {form_data['topic']}"
        msg.attach(MIMEText(email_body, 'plain'))

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(user=my_email, password=my_password)
                server.send_message(msg)
                return jsonify({'success': True, 'message': 'Message sent successfully!'})
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return jsonify({'success': False, 'message': 'Failed to send message. Please try again later.'}), 500
    # User Authentication Routes
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegisterForm()
        current_year = datetime.datetime.now().year

        if form.validate_on_submit():
            name = form.name.data
            email = form.email.data
            password = form.password.data

            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("Email already registered. Please use a different email.", "danger")
                return redirect(url_for('register'))

            # Hash the password and create the user
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            new_user = User(
                name=name,
                email=email,
                password=hashed_password
            )

            try:
                db.session.add(new_user)
                db.session.commit()
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash("An error occurred. Please try again.", "danger")
                print(f"Registration error: {e}")
                return redirect(url_for('register'))

        return render_template("registration.html", form=form, current_year=current_year)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        current_year = datetime.datetime.now().year

        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data

            user = User.query.filter_by(email=email).first()

            if user and check_password_hash(user.password, password):
                login_user(user)
                session['user_id'] = user.id
                session['user_name'] = user.name
                flash(f'Welcome back, {user.name}!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid email or password', 'danger')
                return redirect(url_for('login'))

        return render_template('login.html', form=form, current_year=current_year)

    @app.route('/logout')
    @login_required
    def logout():
        session.pop('user_id', None)
        session.pop('user_name', None)
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for('home'))

    @app.route("/new-post", methods=["GET", "POST"])
    @login_required
    def add_new_post():
        form = CreatePostForm()
        current_year = datetime.datetime.now().year

        if form.validate_on_submit():
            # Check if title already exists
            existing_post = BlogPost.query.filter_by(title=form.title.data).first()
            if existing_post:
                flash("A post with this title already exists. Please choose a different title.", "danger")
                return render_template("make-post.html", form=form, current_year=current_year)

            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                image_url=form.img_url.data,
                author=current_user.name,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("blog"))
        return render_template("make-post.html", form=form, is_edit=False, current_year=current_year)

    @app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
    @login_required
    def edit_post(post_id):
        post = BlogPost.query.get_or_404(post_id)
        current_year = datetime.datetime.now().year

        # Only allow the author to edit their own post
        if current_user.name != post.author:
            flash("You can only edit your own posts.", "danger")
            return redirect(url_for("show_post", post_id=post_id))

        edit_form = CreatePostForm(
            title=post.title,
            subtitle=post.subtitle,
            img_url=post.image_url,
            body=post.body
        )
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.image_url = edit_form.img_url.data
            post.author = current_user.name
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))
        return render_template("make-post.html", form=edit_form, is_edit=True, current_year=current_year)

    @app.route("/delete/<int:post_id>")
    @login_required
    def delete_post(post_id):
        post_to_delete = BlogPost.query.get_or_404(post_id)
        # Only allow the author to delete their own post
        if current_user.name != post_to_delete.author:
            flash("You can only delete your own posts.", "danger")
            return redirect(url_for("show_post", post_id=post_id))

        db.session.delete(post_to_delete)
        db.session.commit()
        return redirect(url_for('blog'))

    return app


# Create the Flask application
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)