from setuptools import setup, find_packages

setup(
    name="agora-governance",
    version="1.0.0",
    description="Multi-Agent 系统的三级治理体系",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="T-Mind",
    author_email="t-mind@agora.ai",
    url="https://github.com/lawcontinue/agora-governance",
    packages=find_packages(),
    install_requires=[
        "jieba>=0.42.1",
        "scikit-learn>=1.3.0",
        "pydantic>=2.0.0",
        "pyyaml>=6.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)
