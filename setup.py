"""Setup script for harbor-day2-operator."""
from setuptools import setup, find_packages

setup(
    name="harbor-day2-operator",
    version="0.1.0",
    packages=find_packages(),
    package_dir={"": "src"},
    install_requires=[
        "harborapi",
        "chevron",
        "python-json-logger",
    ],
)
