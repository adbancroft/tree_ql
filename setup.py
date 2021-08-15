from setuptools import setup

setup(name='tree-ql',
      version='0.1',
      description='A query language for trees',
      url='https://github.com/adbancroft/tree_ql',
      author='adbancroft',
      author_email='13982343+adbancroft@users.noreply.github.com',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Interpreters',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Text Processing',
      ],      
      license='LGPL',
      packages=['tree_ql'],
      package_data={'tree_ql': ['*.lark', '*.lark.cache' ]},
      install_requires=[
          'lark-parser',
          'more-itertools',
          'python_log_indenter'
      ],
      zip_safe=False)