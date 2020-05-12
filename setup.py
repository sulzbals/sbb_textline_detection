from io import open
from setuptools import find_packages, setup

with open('requirements.txt') as fp:
    install_requires = fp.read()

setup(
    name="qurator-sbb-textline",
    version="0.0.1",
    author="The Qurator Team",
    author_email="qurator@sbb.spk-berlin.de",
    description="Qurator",
    long_description=open("README.md", "r", encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    keywords='qurator',
    license='Apache',
    url="https://qurator.ai",
    packages=find_packages(exclude=["*.tests", "*.tests.*",
                                    "tests.*", "tests"]),
    install_requires=install_requires,
    package_data={
        '': ['*.json'],
    },
    entry_points={
      'console_scripts': [
        "ocrd-sbb-crop=qurator.sbb_textline_detector:ocrd_sbb_crop",
        "ocrd-sbb-segment-page=qurator.sbb_textline_detector:ocrd_sbb_segment_page",
      ]
    },
    python_requires='>=3.6.0',
    tests_require=['pytest'],
    classifiers=[
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3',
          'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)
