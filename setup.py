#!/usr/bin/env python

from setuptools import setup
from src import pbm_version

setup(name='Pybimun',
      version=pbm_version,
      description='Simple software for downloading a full resolution image from '
                  'bibliotheques-specialisees.paris.fr',
      author='Cyril Novel',
      author_email='pybimun@kosmon.fr',
      install_requires=['requests', 'pillow', 'wget', 'pytest', 'pytest-cov'],
      packages=['src'],
      scripts=['src/app.py', 'src/save_image.py', 'src/callback.py']
      )
