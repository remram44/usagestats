import os
from setuptools import setup


# pip workaround
os.chdir(os.path.abspath(os.path.dirname(__file__)))


def list_files(d, root):
    files = []
    for e in os.listdir(os.path.join(root, d)):
        if os.path.isdir(os.path.join(root, d, e)):
            files.extend(list_files('%s/%s' % (d, e), root))
        elif not e.endswith('.pyc'):
            files.append('%s/%s' % (d, e))
    return files


with open('README.rst') as fp:
    description = fp.read()
setup(name='usagestats',
      version='0.1',
      py_modules=['usagestats'],
      description="Anonymous usage statistics collecter",
      install_requires=['requests'],
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
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python',
          'Topic :: Internet',
          'Topic :: Internet :: Log Analysis',
          'Topic :: Software Development',
          'Topic :: System :: Logging',
          'Topic :: Utilities'])
