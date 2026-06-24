from setuptools import setup, find_packages

setup(
    name="paper-trading-sim",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={"trading_sim": ["templates/*.html"]},
    install_requires=[
        "flask>=3.0",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "trading-sim=trading_sim.server:main",
        ],
    },
)
