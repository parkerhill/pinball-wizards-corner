import os
import sqlite3
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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

    # Get the path to the SQLite database file
    sqlite_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blog.db")

    if not os.path.exists(sqlite_db_path):
        print(f"ERROR: SQLite database file not found at {sqlite_db_path}")
        return

    print(f"SQLite database found at: {sqlite_db_path}")

    # Connect to SQLite database directly
    sqlite_conn = sqlite3.connect(sqlite_db_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # Create Flask app context to use SQLAlchemy models
    app = create_app()

    with app.app_context():
        # Make sure all tables exist in PostgreSQL
        db.create_all()

        print("Starting migration from SQLite to PostgreSQL...")

        # Get blog posts from SQLite
        sqlite_cursor.execute("SELECT * FROM blog_posts")
        posts = sqlite_cursor.fetchall()
        print(f"Found {len(posts)} blog posts in SQLite database")

        # Migrate blog posts
        for post in posts:
            print(f"Migrating post: {post['title']}")

            # Check if post already exists in PostgreSQL
            existing_post = BlogPost.query.filter_by(id=post['id']).first()

            if existing_post:
                print(f"  - Post already exists in PostgreSQL, updating: {post['title']}")
                # Update existing post
                existing_post.title = post['title']
                existing_post.subtitle = post['subtitle']
                existing_post.date = post['date']
                existing_post.body = post['body']
                existing_post.author = post['author']
                existing_post.image_url = post['image_url']
            else:
                print(f"  - Creating new post in PostgreSQL: {post['title']}")
                # Create new post
                new_post = BlogPost(
                    id=post['id'],
                    title=post['title'],
                    subtitle=post['subtitle'],
                    date=post['date'],
                    body=post['body'],
                    author=post['author'],
                    image_url=post['image_url']
                )
                db.session.add(new_post)

        # Try to get users from SQLite
        try:
            sqlite_cursor.execute("SELECT * FROM users")
            users = sqlite_cursor.fetchall()
            print(f"Found {len(users)} users in SQLite database")

            # Migrate users
            for user in users:
                print(f"Migrating user: {user['name']}")

                # Check if user already exists in PostgreSQL
                existing_user = User.query.filter_by(email=user['email']).first()

                if existing_user:
                    print(f"  - User already exists in PostgreSQL, updating: {user['name']}")
                    # Update existing user
                    existing_user.name = user['name']
                    existing_user.password = user['password']
                    # Add reset token fields if they exist
                    if 'reset_token' in user.keys():
                        existing_user.reset_token = user['reset_token']
                    if 'reset_token_expiry' in user.keys():
                        existing_user.reset_token_expiry = user['reset_token_expiry']
                else:
                    print(f"  - Creating new user in PostgreSQL: {user['name']}")
                    # Create new user with required fields
                    new_user = User(
                        id=user['id'],
                        name=user['name'],
                        email=user['email'],
                        password=user['password']
                    )
                    # Add reset token fields if they exist
                    if 'reset_token' in user.keys():
                        new_user.reset_token = user['reset_token']
                    if 'reset_token_expiry' in user.keys():
                        new_user.reset_token_expiry = user['reset_token_expiry']

                    db.session.add(new_user)
        except sqlite3.OperationalError as e:
            print(f"No users table found in SQLite database or error: {e}")

        # Try to get comments from SQLite
        try:
            sqlite_cursor.execute("SELECT * FROM comments")
            comments = sqlite_cursor.fetchall()
            print(f"Found {len(comments)} comments in SQLite database")

            # Migrate comments
            for comment in comments:
                print(f"Migrating comment ID: {comment['id']}")

                # Check if comment already exists in PostgreSQL
                existing_comment = Comment.query.filter_by(id=comment['id']).first()

                if existing_comment:
                    print(f"  - Comment already exists in PostgreSQL, updating")
                    # Update existing comment
                    existing_comment.text = comment['text']
                    existing_comment.author = comment['author']
                    existing_comment.date = comment['date']
                    existing_comment.post_id = comment['post_id']
                else:
                    print(f"  - Creating new comment in PostgreSQL")
                    # Create new comment
                    new_comment = Comment(
                        id=comment['id'],
                        text=comment['text'],
                        author=comment['author'],
                        date=comment['date'],
                        post_id=comment['post_id']
                    )
                    db.session.add(new_comment)
        except sqlite3.OperationalError as e:
            print(f"No comments table found in SQLite database or error: {e}")

        # Commit all changes
        try:
            db.session.commit()
            print("Migration completed successfully!")
        except Exception as e:
            print(f"Error during database commit: {e}")
            db.session.rollback()
            print("Migration failed - changes rolled back")

        # Close SQLite connection
        sqlite_conn.close()


if __name__ == "__main__":
    migrate_to_postgres()