import io

import setuptools
from pipenv.project import Project
from pipenv.utils import convert_deps_to_pip

import lki

with io.open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="lki",
    version=lki.__version__,
    description="connect Lirian's useful commands",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Lirian Su",
    author_email="liriansu@gmail.com",
    url="https://github.com/LKI/LKI",
    license="MIT License",
    install_requires=convert_deps_to_pip(Project(chdir=False).parsed_pipfile["packages"], r=False),
    packages=setuptools.find_packages(),
    entry_points={"console_scripts": "lki = lki:entry"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Operating System :: Unix",
    ],
)
