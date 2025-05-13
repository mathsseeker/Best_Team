from setuptools import setup, find_packages

setup(
    name="Best_Team",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A brief description of the Best_Team project.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/mathssekeer/Best_Team",  
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        # Add your project's dependencies here
        # Example: "numpy>=1.21.0",
    ],
    entry_points={
        "console_scripts": [
            # Add command-line scripts here
            # Example: "best_team=best_team.cli:main",
        ],
    },
)