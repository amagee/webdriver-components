import os
from setuptools import setup

setup(
    name="webdriver_components",
    version="0.14.0",
    author="Andrew Magee",
    author_email="amagee@gmail.com",
    description="Webdriver_components",
    license='Apache License, Version 2.0',
    keywords="selenium webdriver testing page objects components",
    url="https://github.com/amagee/webdriver-components",
    packages=['webdriver_components'],
    long_description="Takes away the pain of writing Selenium tests",
    install_requires=[
        'selenium',
        'ordered_set',
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
        'pyquery'
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Utilities",
        "Topic :: Software Development :: Testing",
    ],
)
