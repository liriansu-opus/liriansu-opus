import setuptools

import lki

setuptools.setup(
    name='lki',
    version=lki.__version__,
    description='connect Lirian\'s useful commands',
    author='Lirian Su',
    author_email='liriansu@gmail.com',
    url='https://github.com/LKI/LKI',
    license='MIT License',
    install_requires=['fire'],
    packages=setuptools.find_packages(),
    entry_points={'console_scripts': 'lki = lki:entry'},
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
