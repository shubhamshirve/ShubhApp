"""Application configuration constants."""
import os

JWT_SECRET = os.environ.get('JWT_SECRET', 'saas-billing-secret-key-2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
