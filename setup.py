# yum install libxslt-devel - for lxml

from setuptools import setup, find_packages
import os
import sys

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, "README.md")).read()
CHANGES = open(os.path.join(here, "CHANGES.txt")).read()

VERSION = "0.1"

requires = [
    "lxml",
    "argparse",
    "nose",
    "unittest2",
    "mock",
    "coverage",
    "futures"
]

setup(
    name="sleuth",
    version=VERSION,
    description="Pivotal Tracker Activity Web Hook Listener",
    long_description=README + "\n\n" + CHANGES,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    packages=find_packages(),
    license="",
    include_package_data=True,
    package_data={},
    zip_safe=False,
    namespace_packages=[],
    test_suite="sleuth.tests",
    install_requires=requires,
    entry_points={
        'console_scripts': [
            'start-sleuth = sleuth:main',
        ]
    },
    scripts=[],
    setup_requires=["setuptools_git >= 0.3"],
)
