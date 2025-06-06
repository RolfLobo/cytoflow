from PyInstaller.utils.hooks import (copy_metadata, collect_submodules, 
                                     collect_data_files)
datas = copy_metadata('pyface') + collect_data_files('pyface')

hiddenimports = collect_submodules('pyface.ui.qt') + \
                collect_submodules('pyface.ui.qt.action') + \
                collect_submodules('pyface.timer') + \
                collect_submodules('pyface.tasks')

