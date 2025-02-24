from setuptools import setup, find_packages

setup(
    name="cuprj-cli",
    version="0.1.0",
    description="Caravel User's Project CLI - A tool for generating Verilog code for Wishbone systems",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="efabless",
    author_email="info@efabless.com",
    url="https://github.com/shalan/cuprj-cli",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "PyYAML>=6.0",
        "PyQt6>=6.0; python_version>='3.9'",
        "requests>=2.25.0",
        "pathlib>=1.0.1",
    ],
    entry_points={
        "console_scripts": [
            "cuprj=cuprj_cli.cli:main",
            "cuprj-gui=cuprj_cli.main_gui:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
    python_requires=">=3.9",
) 