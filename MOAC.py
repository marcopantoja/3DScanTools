"""
This script is to create lists of required files for 
a calibration, given the nStops, rotate, and tilt "id"
"""
from os import listdir, remove, makedirs, rename, getenv
from sys import argv
import time
from datetime import datetime as dt
from os.path import join, basename, isdir
from shutil import copy
from zipfile import ZipFile
from subprocess import Popen, call
from csv import DictReader

if len(argv)>0:
    if 'tools' in argv:
        calib_tools = argv[argv.index('tools')+1]
    else:
        calib_tools = getenv('OneDrive')+r'\Optimus-LP\OptimusCalibration'
    if 'timeout' in argv:
        calib_timeout = float(argv[argv.index('timeout')+1]) * 60
    else:
        calib_timeout = 60*20
    if 'hybridFilter' in argv:
        hybFilter = [h for h in argv[argv.index('hybridFilter')+1].split(",") if h != '']
        hybrid = 'FFF'
    else:
        hybFilter = []
        hybrid = ''
    if 'NegativeTilt' in argv:
        tilt_combo = 'NegativeTilt'
        zero_search = '-'
    elif 'PositiveTilt' in argv:
        tilt_combo = 'PositiveTilt'
        zero_search = '+'
    else:
        tilt_combo = 'BothTilt'
        zero_search = '-'
    if 'trialsDir' in argv:
        trials_dir = argv[argv.index("trialsDir")+1]
    else:
        trials_dir = r'F:\Round2MOAC\Scanner-30Tilt'
    if 'subBase' in argv:
        sub_base = argv[argv.index("subBase")+1]
    else:
        sub_base = r"F:\Round2MOAC\Scanner-30Tilt\calibrations"
    if 'Trial' in argv:
        t_lower = int(argv[argv.index("Trial")+1])
        t_upper = t_lower+1
    else:
        t_lower = 1
        t_upper = len([d for d in listdir(trials_dir) if 'Trial' in d and isdir(d)])+2
t1 = time.thread_time_ns()
subfolder = f'{sub_base}/{len(hybFilter)}_Artifact/{tilt_combo}'
# convert a treatment tuple into list of pose coordinates
def lists_from_treatment(treatment): # treatment is (nStops, rotate, tilt) conditions
    nStops = [0,
        ['-60', '-30', '+00', '+30', '+60'],    #treatment 1
        ['-60', '-40', '-20', '+00', '+20', '+40', '+60'],  #treatment 2
        ['-60', '-45', '-30', '-15', '+00', '+15', '+30', '+45', '+60'] #treatment 3
    ]
    rotate = [0,
        ['-10', '+10', '+00'],
        ['-15', '+15', '+00'],
        ['-20', '+20', '+00']
    ]
    tilt = {
        'PositiveTilt':[
            0,
            ['+15'],
            ['+17.5'],
            ['+20']
        ],
        'NegativeTilt':[
            0,
            ['-15'],
            ['-17.5'],
            ['-20']
        ],
        'BothTilt':[
            0,
            ['-15','+15'],
            ['-17.5','+17.5'],
            ['-20','+20']
        ]
    }
    pose_coordinates = []
    file_paths = []
    for t in tilt[tilt_combo][treatment[2]]:
        for s in nStops[treatment[0]]:
            for r in rotate[treatment[1]]:
                tag = f'({s}Pz{r}Ry{t}T)'
                path = f'{t}Tilt'
                pose_coordinates.append(tag)
                file_paths.append(path)
    return pose_coordinates, file_paths
def get_temps(times, directory):
    temperatures = [join(directory, f) for f in listdir(directory) if f.endswith('.csv') and 'TargetTemp' in f]
    avg_temp = 0
    no_temp = 0
    temp_dict = {}
    for f in temperatures:
        with open(f, mode='r', newline='') as t_csv:
            all_temps = DictReader(t_csv)
            for t in all_temps:
                temp_dict[t['Timestamp'][:-3]] = (float(t['Ch0'])+float(t['Ch1']))/2
    for t in times:
        t = [str(tt).zfill(2) for tt in t]
        try:
            avg_temp += temp_dict[f'{t[2]}-{t[1]}-{t[0]}_{t[3]}-{t[4]}']
        except KeyError: # if no time is found at file-time
            max_offset=3
            for o in range(max_offset):
                try:
                    avg_temp += temp_dict[f'{t[2]}-{t[1]}-{t[0]}_{t[3]}-{int(t[4])-o}'] # look o min before
                except KeyError:
                    try:
                        avg_temp += temp_dict[f'{t[2]}-{t[1]}-{t[0]}_{t[3]}-{int(t[4])+o}'] # then look o min later
                    except KeyError:
                        no_temp += 1
                        continue
    if len(times)-no_temp==0:
        return ''
    else:
        return avg_temp/(len(times)-no_temp)
    
def populate_calibration(pose_coordinates, base_dir, file_paths, new_calib_dir, artifact):
    png = 0
    copied_files = []
    capture_times = []
    for idx, pose in enumerate(pose_coordinates):
        Pz = float(pose.split('Pz')[0][1:])
        all_zips = listdir(join(base_dir, file_paths[idx]))
        possible_zips = []
        artefact_zips = []
        for z in all_zips:
            if 'P102' in z:
                possible_zips.append(join(base_dir, file_paths[idx], z))
                artefact_zips.append(join(base_dir, file_paths[idx], z))
            try:
                lower = float(z.split('_')[0])
                upper = float(z.split('_')[1])
            except ValueError:
                pass
            if Pz>=lower and Pz<=upper:
                possible_zips.append(join(base_dir, file_paths[idx], z))
        for z in possible_zips:
            with ZipFile(z, mode='r') as zfile:
                for f in zfile.filelist:
                    if pose in f.filename and 'FlatPlate' in f.filename:
                        if (f'+00Pz+00Ry{zero_search}' in pose or
                            f'+60Pz+00Ry{zero_search}' in pose):
                            if f.filename.endswith('.png'):
                                png+=1
                            extracted = False
                            while not extracted:
                                try:
                                    zfile.extract(f, new_calib_dir)
                                    rename(join(new_calib_dir, f.filename),join(new_calib_dir, f.filename.replace('_001_','_000_')))
                                    copied_files.append(f.filename.replace('_001_','_000_'))
                                    extracted = True
                                    capture_times.append(zfile.NameToInfo[f.filename].date_time)
                                except:
                                    time.sleep(2)
                        elif f.filename.endswith('.pfm'):
                            continue
                        elif f.filename.endswith('.png'):
                            extracted = False
                            while not extracted:
                                try:
                                    zfile.extract(f, path=new_calib_dir)
                                    copied_files.append(f.filename)
                                    extracted = True
                                    capture_times.append(zfile.NameToInfo[f.filename].date_time)
                                except:
                                    time.sleep(2)
                            png+=1
    copy(join(calib_tools, artifact), new_calib_dir)
    copy(join(calib_tools, 'LPGoldenCalibtargetUPDATEDCENTERS', 'LP-A-updatedCenter.calibtarget'), new_calib_dir)
    copied_files.append(artifact)
    copied_files.append('LP-A-updatedCenter.calibtarget')
    for tilt in listdir(base_dir):
        if isdir(join(base_dir, tilt)):
            for fol in listdir(join(base_dir, tilt)):
                if 'P102' in fol:
                    fol = join(base_dir, tilt, fol)
                    with ZipFile(fol, mode='r') as zfile:
                        for f in zfile.filelist:
                            if 'Artifact' in f.filename:
                                name = f.filename
                                extracted = False
                                while not extracted:
                                    try:
                                        zfile.extract(f, new_calib_dir)
                                        if name[ name.find('_(')+1 : name.find(')_')+1 ] in hybFilter:
                                            name = f.filename.replace(
                                                        'w_0',
                                                        f'w_{hybrid}'
                                                    )
                                            rename(
                                                join(new_calib_dir, f.filename),
                                                join(
                                                    new_calib_dir, 
                                                    name
                                                )
                                            )
                                        copied_files.append(name)
                                        extracted = True
                                        capture_times.append(zfile.NameToInfo[f.filename].date_time)
                                    except:
                                        time.sleep(2)
    avg_temp = get_temps(capture_times, trials_dir)
    return str(round(png/4)).zfill(3), copied_files, avg_temp
def run_batch_scripts(treatment, subfolder, trial, base_dir):
    coordinates, file_paths = lists_from_treatment(treatment)
    new_calibration = join(
        subfolder, 
        f'Trial{trial}', 
        f'({treatment[0]}_{treatment[1]}_{treatment[2]})_LP-01_P-102_CalibrationData_MeasuredArtefact'
    )
    print("new calib:", new_calibration)
    try:
        makedirs(new_calibration)
    except OSError:
        return True
    if trial in (2, 3):
        artifact = 'P102_QPlus-Avg_200108_North-Orientation.artefact'
    else:
        artifact = 'P102_QPlus-Avg_200108_South-Orientation.artefact'
    views, _, avg_temp = populate_calibration(coordinates, base_dir, file_paths, new_calibration, artifact)
    print(f'Views: {views}')
    total_fits = 0
    for f in listdir(new_calibration):
        if 'Artefact' in basename(f) and f.endswith('.png'): total_fits += 1
        if 'Artifact' in basename(f):
            if f.endswith('.png'): total_fits += 1
            rename(
                join(new_calibration, f),
                join(new_calibration, f.replace('Artifact', 'Artefact'))
            )
    print(f'Expecting {total_fits} meshes and artifact fits.')
    optimus_calib = Popen(f'1_calibrate.bat "{new_calibration}" "{hybrid}" "{avg_temp}"', shell=True, cwd=calib_tools)
    fit_files = []
    done = False
    print('waiting for calibrations to finish...')
    calib_start = time.time()
    while not done: 
        for f in listdir(new_calibration):
            if 'artefactFits' in f:
                if f not in fit_files:
                    fit_files.append(f)
            if len(fit_files)==total_fits:
                runtime=str(time.time()-calib_start)+' seconds'
                done = True
            elif time.time()-calib_start>=calib_timeout:
                runtime=f'timed out at {calib_timeout} seconds'
                done = True
    print('comparing calibrations...')
    call(f'2_compare.bat "{new_calibration}"', shell=True, cwd=calib_tools)
    removed = [f'Calibration Treatment Time: {runtime}.'+'\n']
    for f in listdir(new_calibration):
        if 'CameraView' in f or f.endswith('.calibtarget') or f.endswith('.artefact'):
            removed.append(f+'\n')
            remove( join(new_calibration, f))
    with open(join(new_calibration, 'remove_log.txt'), mode='w') as fh:
        fh.writelines(removed)
    optimus_calib.kill()
    return True
for t in range(t_lower,t_upper):
    base_dir = trials_dir + f'\\Trial{t}'
    for i in range(1,4):
        for ii in range(1,4):
            for iii in range(1,4):
                t2 = time.thread_time_ns()
                treatment = (i, ii, iii)
                run_batch_scripts(treatment, subfolder, t, base_dir)
                print(f'calib treatment run time: {(time.thread_time_ns()-t2)/10**9} seconds.')
                print(f'total running time: {(time.thread_time_ns()-t1)/10**9} seconds.')