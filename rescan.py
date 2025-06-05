from os import getcwd, listdir, makedirs
from os.path import join, basename
from subprocess import call
from datetime import datetime as dt
cwd = r'Varied-DRP-Calibrations\Varied-DRP-Calibrations'
date = '210202'
tools_dir = r'Calibration\tools'
artifact = r"Calibration\artifacts\P509_SDME-Avg_210121.artifact"
setup_files = [join(cwd, 'reprocess',date, f) for f in listdir(join(cwd, 'reprocess',date)) if f.endswith('.3dscansetup')]
projects = [join(cwd, f) for f in listdir(cwd) if f.endswith('.3dscanproj')]
for s in setup_files:
    try:
        proj_dir = join(cwd, 'reprocess',date, basename(s).split('_')[0])
        makedirs(proj_dir)
    except OSError:
        continue
    for p in projects:
        new = join(proj_dir, basename(p))
        call(f'ReScan.exe --in "{p}" --out "{new}" --hwsetup "{s}" --artifact "{artifact}"', cwd=tools_dir, shell=True)