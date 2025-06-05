from os import getcwd, listdir
from os.path import abspath
from subprocess import Popen
from time import sleep


from d3scantool import scantool


server_dir = r"C:\Client-Server\Server"
artefact_0rot = r'Calibration\P102_QPlus-Avg_200108_0rot.artefact'
artefact_90rot = r'Calibration\P102_QPlus-Avg_200108_-90rotX.artefact'
server = Popen('sdk_server.exe', shell=True, cwd=server_dir)
sleep(7)
fusion_params = scantool.FusionParameters(
    resolutionPercent=75,
    pointWeight=4,
    holeSizeThresRel=0.015,
    smoothing=0
)
try:
    scanner = scantool()
    for f in listdir(getcwd()):
        if f.endswith('.3dscanmesh'):
            mesh_path = abspath(f)
            scans = scanner.ImportSurface(mesh_path)
            fused = scanner.Fuse(scans, fusion_params)
            scanner.ExportSurface(fused, mesh_path.replace('.3dscanmesh','_FusedScan.3dscanmesh'))
except scantool.HippoScanToolError as e:
    server.kill()
    print(f'Error: {e}\nScript ended.')
server.kill()