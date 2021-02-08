from setuptools import setup


setup(
    name='cldfbench_palula',
    py_modules=['cldfbench_palula'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'palula=cldfbench_palula:Dataset',
        ]
    },
    install_requires=[
        'cldfbench',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
