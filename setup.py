#!/usr/bin/env python
from pathlib import Path

from setuptools import find_packages, setup

test_requires = [
    "coverage",
    "pytest",
    "pytest-cov",
    "zipp",
]

doc_requires = [
    "sphinx>=3.0",
    "sphinx_rtd_theme",
]

readme_path = Path(__file__).parent / "README.rst"
long_description = readme_path.read_text()

setup(
    name="catalystcoop.dbfread",
    version="3.0.0",
    description="Read DBF Files with Python",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="Ole Martin Bjorndalen",
    author_email="ombdalen@gmail.com",
    url="https://github.com/catalyst-cooperative/dbfread",
    maintainer="Zane A. Selvans",
    maintainer_email="zane.selvans@catalyst.coop",
    project_urls={
        "Source": "https://github.com/catalyst-cooperative/dbfread",
        # "Documentation": "https://catalystcoop-dbfread.readthedocs.io",
        "Issue Tracker": "https://github.com/catalyst-cooperative/dbfread/issues",
    },
    package_data={"": ["LICENSE"]},
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    zip_safe=True,
    install_requires=[],
    extras_require={
        "doc": doc_requires,
        "test": test_requires,
    },
    scripts=["examples/dbf2sqlite"],
    python_requires=">=3.8",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
