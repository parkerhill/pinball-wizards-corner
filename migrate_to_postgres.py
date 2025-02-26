import os
import sqlite3
import psycopg2
from dotenv import load_dotenv
from main import create_app, db, User, BlogPost, Comment

# Load environment variables
load_dotenv()


def migrate_to_postgres():
    """Migrate data from SQLite to PostgreSQL."""
    # Get PostgreSQL connection string from environment
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set.")
        return

    # Create Flask app context to use SQLAlchemy models
    app = create_app()

    with app.app_context():
        # Make sure all tables exist in PostgreSQL
        db.create_all()

        print("Starting migration from SQLite to PostgreSQL...")

        # Migrate users
        users = User.query.all()
        for user in users:
            print(f"Migrating user: {user.name}")
            # Check if user already exists in PostgreSQL
            existing_user = User.query.filter_by(email=user.email).first()
            if not existing_user:
                new_user = User(
                    id=user.id,
                    email=user.email,
                    password=user.password,
                    name=user.name,
                    reset_token=user.reset_token,
                    reset_token_expiry=user.reset_token_expiry
                )
                db.session.add(new_user)

        # Migrate blog posts
        posts = BlogPost.query.all()
        for post in posts:
            print(f"Migrating post: {post.title}")
            existing_post = BlogPost.query.filter_by(title=post.title).first()
            if not existing_post:
                new_post = BlogPost(
                    id=post.id,
                    title=post.title,
                    subtitle=post.subtitle,
                    date=post.date,
                    body=post.body,
                    author=post.author,
                    image_url=post.image_url
                )
                db.session.add(new_post)

        # Migrate comments
        comments = Comment.query.all()
        for comment in comments:
            print(f"Migrating comment ID: {comment.id}")
            existing_comment = Comment.query.filter_by(id=comment.id).first()
            if not existing_comment:
                new_comment = Comment(
                    id=comment.id,
                    text=comment.text,
                    author=comment.author,
                    date=comment.date,
                    post_id=comment.post_id
                )
                db.session.add(new_comment)

        # Commit all changes
        db.session.commit()
        print("Migration completed successfully!")


if __name__ == "__main__":
    migrate_to_postgres()