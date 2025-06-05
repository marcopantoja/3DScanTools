from os import getcwd, listdir
from os.path import isdir, join
from subprocess import Popen
from time import sleep
from xml.etree import ElementTree as ET

from d3scantool import hipposcantool

server_dir = r"C:\Client-Server\Server"
artefact_0rot = r'Calibration\P102_QPlus-Avg_200108_0rot.artefact'
artefact_90rot = r'Calibration\P102_QPlus-Avg_200108_-90rotX.artefact'
server = Popen('sdk_server.exe', shell=True, cwd=server_dir)
sleep(7)
def measure_scans(calib):
    all_files = [join(calib, f) for f in listdir(calib)]
    if join(calib, 'api-scripted_artifactFits.xml') in all_files: 
        print(f'skipping...already measured {calib}')
        return True
    mesh_paths_0deg = [f for f in all_files if f.endswith('.3dscanmesh') and '-60T' not in f]
    mesh_paths_90deg = [f for f in all_files if f.endswith('.3dscanmesh') and '-60T' in f]
    scans_0deg = [scanner.ImportSurface(m) for m in mesh_paths_0deg]
    scans_90deg = [scanner.ImportSurface(m) for m in mesh_paths_90deg]
    measure_0deg = scanner.MeasureArtifact(scans_0deg, artefact_0rot)
    measure_90deg = scanner.MeasureArtifact(scans_90deg, artefact_90rot)
    measurexml = ET.fromstring(measure_0deg)
    measurexml.extend(ET.fromstring(measure_90deg))
    fit_path = join(calib, 'api-scripted_artifactFits.xml')
    scanner.Clear()
    with open(fit_path, 'w') as fit_file:
        fit_file.write(ET.tostring(measurexml).decode())
    print(f'finished measuring {calib}')
    return True
try:
    scanner = hipposcantool()
    for tilt in listdir(getcwd()):
        if isdir(tilt):
            for trial in listdir(tilt):
                if isdir(join(tilt, trial)):
                    for treatment in listdir(join(tilt, trial)):
                        measure_scans(join(getcwd(), tilt, trial, treatment))
except hipposcantool.HippoScanToolError as e:
    server.kill()
    print(f'error: {e}')
server.kill()
