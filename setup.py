from setuptools import setup, find_packages

setup(
    name="oobe-capital-agent",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["cli"],
    entry_points={
        "console_scripts": [
            "oobe-agent=cli:main",
        ],
    },
    python_requires=">=3.10",
)
