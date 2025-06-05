"""
This uses the ReScan executable to make new scan data
from existing projects, but with a different calibration
setup file. This script is for compressed project files.
The decompression/compression will be handled to avoid 
creating massive quantities of data. 

Call from command line to pass the parameters for work directory,
project source directory, and desired output directory, along with 
specifying an alternate artifact file. 

Command Line Arguments:
calibs    --------    This tells script where the calib zips or hardware setup files are located
projects  --------    This tells script where the projzip files are
output    --------    This allows user to send converted output files to a destination other than current working directory/reprocess folder

be sure to use quotes if paths contain any spaces!
"""
from datetime import datetime as dt
from os import getcwd, getenv, listdir, rename, remove, makedirs
from os.path import join, isdir, isfile
from shutil import rmtree
from subprocess import call
from sys import argv
from xml.etree import ElementTree as ET
from zipfile import ZipFile


tools_dir = join(getenv('OneDrive'), 'tools')
date = dt.now().strftime("%y%m%d")
temp = join(getenv('LOCALAPPDATA'), 'temp')
if 'calibs' in argv:
    cwd = argv[argv.index('calibs')+1]
else:
    cwd = getcwd()
if 'projects' in argv:
    projects = argv[argv.index('projects')+1]
else:
    projects = cwd
if 'output' in argv:
    output = argv[argv.index('output')+1]
    if not isdir(output): makedirs(output)
else:
    output = join(cwd, 'reprocessed', date)
if 'artifact' in argv:
    artifact = argv[argv.index('artifact')+1]
else:
    artifact = r"Calibration\artifacts\P06_ASL-Avg_200520.artifact"

def get_calib_timestamp(raw_bytes,source):
    xml = ET.fromstring(raw_bytes.decode())
    timestamp = xml.find('calibrationInfo')
    if timestamp is not None:
        timestamp = timestamp.attrib['timestamp']
        return f'{timestamp[2:4]}{timestamp[5:7]}{timestamp[8:10]}{timestamp[11:17]}'
    else:
        return source


def get_setup_files(directory):
    setup = [join(directory, f) for f in listdir(directory) if f.endswith('.3dscansetup') or 'hardwaresetup' in f.lower() or 'rescan' in f.lower()]
    if not len(setup): # if the list was empty look for zips and extract
        zips = [join(directory, f) for f in listdir(directory) if f.endswith('.zip') and 'calibrationdata' in f.lower()]
        if not len(zips):
            return False
        else:
            for z in zips:
                with ZipFile(z) as calibZip:
                    for f in calibZip.filelist:
                        if f.filename.endswith('.3dscansetup'):
                            timestamp = get_calib_timestamp(calibZip.read(f),calibZip.filename)
                            destination = join(output, f'{timestamp}_{f.filename}')
                            if isdir(destination) or isdir(destination.replace('.3dscansetup','')): continue
                            calibZip.extract(
                                f, 
                                destination)
    return True

if get_setup_files(cwd):
    setup_file_dirs = [join(output, f) for f in listdir(output) if f.endswith('.3dscansetup') and isdir(join(output, f))]
    if not len(setup_file_dirs):
        setup_file_dirs = [join(output, f) for f in listdir(output) if 'hardwaresetup' in f.lower() or 'rescan' in f.lower()]
    zippedprojects = [join(projects, f) for f in listdir(projects) if f.endswith('.3dscanprojzip')]
    for s in setup_file_dirs:
        if isdir(s):
            snew = s.replace('.3dscansetup','')
            try:
                rename(s, snew)
            except: # another process is already handling it
                pass
            s = snew
        proj_dir = join(output, s)
        setupFile = [join(proj_dir, sf) for sf in listdir(s) if sf.endswith('.3dscansetup')][0]
        for p in zippedprojects:
            exists = False
            with ZipFile(p) as projzip:
                for f in projzip.filelist:
                    if f.filename.endswith('.3dscanproj'): 
                        if isfile(join(proj_dir, f.filename+'zip')) or isfile(join(proj_dir, 'input', f.filename)) or isfile(join(proj_dir, f.filename.replace('.3dscanprojzip','_artifactFits.xml'))):
                            exists = True
                        else:
                            try:
                                projzip.extract(f, join(proj_dir, 'input'))
                            except:
                                pass
            if exists: continue
            inProj = join(proj_dir, 'input', f.filename)
            outProj = join(proj_dir, f.filename)
            call(f'ReScan.exe --in "{inProj}" --out "{outProj}" --hwsetup "{setupFile}" --artifact "{artifact}"', cwd=tools_dir, shell=True)
            try:
                with ZipFile(outProj+'zip', 'a') as newprojzip:
                    newprojzip.write(outProj)
            except:
                pass
            try:
                [remove(i) for i in [inProj, outProj]]
            except:
                continue
        try:
            rmtree(join(proj_dir, 'input'))
        except:
            pass