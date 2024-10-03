import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres_user:postgres_password@db:5432/postgres_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-very-secret-key'

    FRONTEND_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))
