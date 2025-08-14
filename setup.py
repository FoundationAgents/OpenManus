from setuptools import setup, find_packages

def parse_requirements(filename):
    """Tries to read a requirements file and returns a list of dependencies"""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except IOError:
        return []

# Parse requirements files
install_requires = parse_requirements('requirements.txt')
dev_requires = parse_requirements('requirements-dev.txt')

setup(
    name='openmanus-qinyuan',
    version='0.1.0',
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        'dev': dev_requires
    },
    python_requires='>=3.12',
)