import os
import shutil
from setuptools import setup, find_packages
from setuptools.command.install import install

class PostInstallCommand(install):
    def run(self):
        # Create scripts directory in package
        package_scripts_dir = os.path.join(self.install_lib, 'rhoshift', 'scripts')
        os.makedirs(package_scripts_dir, exist_ok=True)
        os.makedirs(os.path.join(package_scripts_dir, 'cleanup'), exist_ok=True)

        # Copy scripts to package
        shutil.copy2('scripts/run_upgrade_matrix.sh', package_scripts_dir)
        shutil.copy2('scripts/cleanup/cleanup_all.sh', os.path.join(package_scripts_dir, 'cleanup'))

        # Make scripts executable
        os.chmod(os.path.join(package_scripts_dir, 'run_upgrade_matrix.sh'), 0o755)
        os.chmod(os.path.join(package_scripts_dir, 'cleanup', 'cleanup_all.sh'), 0o755)

        install.run(self)

setup(
    cmdclass={
        'install': PostInstallCommand,
    },
    packages=find_packages(),
    package_data={
        'rhoshift': [
            'scripts/cleanup/*.sh',
            'scripts/run_upgrade_matrix.sh'
        ]
    },
    include_package_data=True
)