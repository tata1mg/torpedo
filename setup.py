from setuptools import find_packages, setup

with open("requirements/base.txt") as f:
    base_requirements = f.read().splitlines()

with open("requirements/test.txt") as f:
    test_requirements = f.read().splitlines()

with open("requirements/dev.txt") as f:
    dev_requirements = f.read().splitlines()


setup(
    name="torpedo",
    version="1.0.0",
    author="1mg",
    author_email="devops@1mg.com",
    url="https://github.com/tata1mg/torpedo",
    description="Vanilla code for Sanic application setup",
    packages=find_packages(exclude=("examples", "requirements")),
    install_requires=base_requirements + test_requirements + dev_requirements,
)
