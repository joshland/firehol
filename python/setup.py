from setuptools import setup, find_packages

setup(
    name="firehol",
    version="3.1.9",
    description="A firewall for humans - Python implementation",
    author="FireHOL Team",
    author_email="firehol-devs@lists.firehol.org",
    url="http://firehol.org/",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "ipaddress",
    ],
    entry_points={
        "console_scripts": [
            "firehol=firehol:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Networking :: Firewall",
    ],
)
