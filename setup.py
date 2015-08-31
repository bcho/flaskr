import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


version = '0.0.1'


class PyTest(TestCommand):

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name='flaskr',
    version=version,
    packages=find_packages('.', exclude=['test*']),

    cmdclass={'test': PyTest},
    tests_require=['pytest'],
)
