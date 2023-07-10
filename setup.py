import io

import setuptools

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
    install_requires=["click>=8.1.3"],
    packages=setuptools.find_packages(),
    entry_points={"console_scripts": "lki = lki.cmdline:entry"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Operating System :: Unix",
    ],
)
