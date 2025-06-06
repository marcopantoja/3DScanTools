from os import walk, getcwd
from os.path import join,basename,dirname
from sys import argv
from py_drive_api import ProcessScript,SERVER_INCLUDE_FOLDER
from subprocess import call

if 'workdir' in argv:
    workdir = argv[argv.index('workdir')+1]
else:
    workdir = getcwd()
if 'NoMeshAnalyze' in argv:
    MeshAnalyze = False
else: MeshAnalyze = True
minScanCount = 250

def get_name(path_str:str):
    splitpath = path_str.split('\\')
    unit = [_[_.find('LP-'):_.find('LP-')+5] for _ in splitpath if _.startswith('LP-')]
    if unit: unit = '3DScanner'+unit[0]
    else: unit = '3DScannerSystem'
    time = splitpath[-1].split('_')[0]
    runID = splitpath[-1].split('_')[-1]
    print(unit)
    return ('_'.join([unit,time,runID]),' '.join([unit,runID]))

for r,d,f in walk(workdir):
    if 'meshes' in d:
        csvfile = [join(r,f2) for f2 in f if f2.endswith('.csv')]
        meshdir = join(r,'meshes')
        if len(csvfile) and len(f)>minScanCount:
            imTitle = get_name(r)
            print(f'Processing data: {basename(r)}\nTitle: {imTitle[0]}',end='\t')
            if MeshAnalyze:
                with open(join(meshdir,'SphereDetector.log'),'w') as processLog:
                    call(f'SphereDetector.exe --folder "{meshdir}" \
                        --project "{join(meshdir,imTitle[0])}" \
                        --diameter 25.41 \
                        --refTemp 20 \
                        --CTE_m_m_K 8.6E-06 \
                        --minPointCountPerSphere 5000 \
                        --minSphericalCapPolarAngle 40 \
                        --analyze',
                        cwd=SERVER_INCLUDE_FOLDER,shell=True,
                        stdout=processLog,stderr=processLog)
                with open(join(meshdir,'SphereDetector.log'),'r') as processLog:
                    while not processLog.readline().startswith('Processing '):pass
                    while processLog.readline().startswith('Processing '):pass
                    print(''.join(processLog.readlines()))
                with open(join(meshdir,imTitle[0]+'.csv'),'r',newline='') as csvfile:
                    allData = [_.split(',') for _ in csvfile.readlines()]
                with open(join(meshdir,imTitle[0]+'.csv'),'w',newline='') as csvfile:
                    notName = len(allData[0])-1
                    csvfile.write(','.join(allData[:1][0]))
                    for line in allData[1:]:
                        csvfile.write('|'.join(line[:len(line)-notName])+','+','.join(line[len(line)-notName:]))
            with open(join(r,'console.log'),'a') as processLog:
                for subvol in ['240x200x200','220x150x150','180x100x100']:
                    print('calling python processor at: '+r+'\t'+subvol)
                    call(f'python "{ProcessScript}" workdir "{r}" title {imTitle[-1]} overwrite\
                        subvolume {subvol}',
                        cwd=dirname(SERVER_INCLUDE_FOLDER),stderr=processLog,stdout=processLog)
                    call(f'python "{ProcessScript}" workdir "{r}" nomR title {imTitle[-1]} overwrite\
                        subvolume {subvol}',
                        cwd=dirname(SERVER_INCLUDE_FOLDER),stderr=processLog,stdout=processLog)
                    call(f'python "{ProcessScript}" workdir "{meshdir}" title {imTitle[-1]} overwrite\
                        processedFile "{join(meshdir,imTitle[0])}.csv" subvolume {subvol}',
                        cwd=dirname(SERVER_INCLUDE_FOLDER),stderr=processLog,stdout=processLog)