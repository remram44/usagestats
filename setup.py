import os
from setuptools import setup


# pip workaround
os.chdir(os.path.abspath(os.path.dirname(__file__)))


with open('README.rst') as fp:
    description = fp.read()
setup(name='usagestats',
      version='0.8',
      py_modules=['usagestats'],
      description="Anonymous usage statistics collector",
      install_requires=['requests', 'distro'],
      author="Remi Rampin",
      author_email='remirampin@gmail.com',
      maintainer="Remi Rampin",
      maintainer_email='remirampin@gmail.com',
      url='https://github.com/remram44/usagestats',
      long_description=description,
      license='Apache License 2.0',
      keywords=['server', 'log', 'logging', 'usage', 'stats', 'statistics',
                'collection', 'report'],
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python',
          'Topic :: Internet',
          'Topic :: Internet :: Log Analysis',
          'Topic :: Software Development',
          'Topic :: System :: Logging',
          'Topic :: Utilities'])
