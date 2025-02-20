from setuptools import setup, find_packages

setup(
    name="si_opportunity_manager",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy",
        "alembic",
        "psycopg2-binary",
        "PyQt5",
        "python-dotenv",
        "passlib",
        "bcrypt",
        "python-jose",
    ],
    python_requires=">=3.8",
) 