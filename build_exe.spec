# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['keypoint_annotation_tool.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('keypoints.ico', '.'),
        ('std_pic', 'std_pic'),  # 打包std_pic文件夹及其内容
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'numpy.random._examples',
        'IPython',
        'jupyter',
        'notebook',
        'pandas',
        'pytest',
        'sphinx',
        'setuptools',
        'pip',
        'wheel',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KeypointAnnotationTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='keypoints.ico',
)
