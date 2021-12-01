#!/usr/bin env python3

from setuptools import setup, find_packages
import pathlib

path = pathlib.Path(__file__).parent.resolve()

setup(
    name='SortingShop',
    version='1.0.1',
    description='Sort your pictures!',
    long_description = (path / 'README.md').read_text(encoding='utf-8'),
    long_description_content_type="text/markdown",
    author='Eike Kühn',
    author_email='eike.kuehn@pixelwoelkchen.de',
    license='The Unlicense',
    url='https://github.com/randomchars42/sortingshop',
    project_urls={
        'Documentation': 'https://github.com/randomchars42/sortingshop',
        'Source': 'https://github.com/randomchars42/sortingshop',
        'Tracker': 'https://github.com/randomchars42/sortingshop/issues',
    },
    keywords='',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: The Unlicense (Unlicense)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
    ],
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    package_data={
        'sortingshop': ['settings/config.ini'],
        'sortingshop.ui': ['resources/*']
    },
    python_requires='>=3.6, < 4',
    setup_requires=[
        'docutils>=0.3',
        'wheel',
        'setuptools',
    ],
    install_requires=[
        'wxPython>=4.0'
    ],
    entry_points={
        'console_scripts':['SortingShop=sortingshop.sortingshop:main','sortingshop=sortingshop.sortingshop:main']
    }
)
