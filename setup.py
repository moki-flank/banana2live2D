# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="banano2live2d",
    version="1.0.0",
    description="Componentized Live2D Generation Engine powered by Gemini Image & Multimodal Models",
    author="Hrio / banano2live2D",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pillow>=9.0.0",
        "numpy>=1.20.0",
        "opencv-python>=4.5.0",
    ],
    entry_points={
        "console_scripts": [
            "banano2live2d=banano2live2D.cli:main",
        ],
    },
    python_requires=">=3.8",
)
