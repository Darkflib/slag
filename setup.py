from setuptools import setup

setup(
    name="slag-commenting",
    version="0.1.0",
    packages=["slag"],
    py_modules=["main"],
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.115.13",
        "uvicorn>=0.27.0",
        "pydantic>=2.5.0",
        "rich>=13.7.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "black>=23.12.0",
            "mypy>=1.7.0",
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "isort>=5.12.0",
        ],
    },
)
