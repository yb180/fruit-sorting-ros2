from setuptools import find_packages, setup

setup(
    name='fruit_sorting_perception',
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/fruit_sorting_perception']),
        ('share/fruit_sorting_perception', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Fruit Sorting Maintainers',
    maintainer_email='maintainers@example.com',
    description='Mock produce perception for ROS 2 Humble.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': [
        'mock_perception = fruit_sorting_perception.mock_node:main',
    ]},
)
