import concurrent.futures
from csv import DictWriter
from datetime import datetime as dt
from os import getcwd, listdir
from os.path import basename, dirname, isdir, join
from xml.etree import ElementTree as ET


def flatten_calibLog(calib_log_path):
    flat = {}
    flat['file'] = 'calibrationLog'
    calib_xml = ET.parse(calib_log_path).getroot()
    calibinfo = calib_xml.find('calibrationInfo')
    for a in calibinfo.attrib:
        flat[f'{calibinfo.tag}_{a}'] = calibinfo.attrib[a]
    flat['treatment'] = basename(dirname(calib_log_path))[:7]
    flat['trial'] = basename(dirname(dirname(calib_log_path))).replace('Trial','')
    if basename(calib_log_path).startswith('1'):
        flat['setup_type'] = 'Standard'
    else:
        flat['setup_type'] = 'Hybrid'
    flat['ID'] = f'{flat["treatment"]}_{flat["trial"]}_{flat["setup_type"][0]}'
    print(f'finished reading {calib_log_path}')
    return flat

def flatten_hw_setup(setup_path):
    hw_setup = ET.parse(setup_path).getroot()
    flat = {}
    flat['file'] = 'hardwareSetup'
    flat['treatment'] = basename(dirname(setup_path))[:7]
    flat['trial'] = basename(dirname(dirname(setup_path))).replace('Trial','')
    if basename(setup_path).startswith('1'):
        flat['setup_type'] = 'Standard'
    else:
        flat['setup_type'] = 'Hybrid'
    flat['ID'] = f'{flat["treatment"]}_{flat["trial"]}_{flat["setup_type"][0]}'
    for i in hw_setup:
        for a in i.attrib:
            flat[f'{i.tag}_{a}'] = i.attrib[a]
        for c, ci in enumerate(i):
            for a in ci.attrib:
                flat[f'{ci.tag}_{c}_{a}'] = ci.attrib[a]
            for cii in ci:
                for a in cii.attrib:
                    flat[f'{ci.tag}_{c}_{cii.tag}_{a}'] = cii.attrib[a]
                if cii.tag.endswith('Model'):
                    intrinsics = cii.find('intrinsics')
                    pose = cii.find('pose')
                    for a in intrinsics.attrib:
                        flat[f'{ci.tag}_{c}_intrinsics_{a}'] = intrinsics.attrib[a]
                    for a in pose.attrib:
                        flat[f'{ci.tag}_{c}_pose_{a}'] = pose.attrib[a]
                    for e in pose:
                        for a in e.attrib:
                            flat[f'{ci.tag}_{c}_pose_{e.tag}{a}'] = e.attrib[a]
    print(f'finished reading {setup_path}')
    return flat

def flatten_artefact_fits(fit_path):
    fits = ET.parse(fit_path)
    flattened_fits = []
    for fit in fits.findall('artefactFit'):
        flat = {}
        flat['file'] = 'artefactFits'
        flat['treatment'] = basename(dirname(fit_path))[:7]
        flat['trial'] = basename(dirname(dirname(fit_path))).replace('Trial','')
        if basename(fit_path).startswith('1'):
            flat['fit_type'] = 'Standard'
        else:
            flat['fit_type'] = 'Hybrid'
        flat['ID'] = f'{flat["treatment"]}_{flat["trial"]}_{flat["fit_type"][0]}'
        flat['scan_name'] = fit.attrib['scan']
        flat['artefact_name'] = fit.attrib['name']
        for a in fit.attrib:
            if a != 'scan' and a != 'name':
                flat[a] = fit.attrib[a]
        for ch in fit:
            if ch.tag == 'spheres':
                for sphere in ch:
                    for ci in sphere:
                        for a in ci.attrib:
                            flat[f'{sphere.attrib["name"]}_{ci.tag}_{a}'] = ci.attrib[a]
                    measure = fits.find(f"sphereMeasures/sphereMeasure[@scan='{fit.attrib['scan']}'][@name='{sphere.attrib['name']}']")
                    for a in measure.attrib:
                        if a not in ['scan', 'name', 'x', 'y', 'z']:
                            flat[f'{measure.attrib["name"]}_{a}'] = measure.attrib[a]
                distances = fits.findall(f"distanceMeasures/sphereDistanceMeasure[@scan='{fit.attrib['scan']}']")
                for dis in distances:
                    for a in dis.attrib:
                        if a not in ['sphereA', 'sphereB', 'scan']:
                            flat[f'{dis.attrib["sphereA"]}_{dis.attrib["sphereB"]}_{a}'] = dis.attrib[a]
            else:
                for a in ch.attrib:
                    flat[f'{ch.tag}_{a}'] = ch.attrib[a]
                for ci in ch:
                    for a in ci.attrib:
                        flat[f'{ch.tag}_{ci.tag[0]}{a[-1]}'] = ci.attrib[a]
        flattened_fits.append(flat)
    print(f'finished reading {fit_path}')
    return flattened_fits

def read_file(file_path):
    if 'HardwareSetup' in basename(file_path):
        return flatten_hw_setup(file_path)
    elif 'artefactFits' in basename(file_path):
        return flatten_artefact_fits(file_path)
    elif 'CalibrationLog' in basename(file_path):
        return flatten_calibLog(file_path)

setup_dicts = {}
log_dicts = {}
fits = []
file_paths = []
for trial in listdir(getcwd()):
    if isdir(trial):
        for folder in listdir(trial):
            if 'CalibrationData' in folder and 'MeasuredArtefact' in folder:
                for subfile in listdir(join(trial, folder)):
                    if 'HardwareSetup' in subfile:
                        file_paths.append(join(trial, folder, subfile))
                    elif 'artefactFits' in subfile:
                        file_paths.append(join(trial, folder, subfile))
                    elif 'CalibrationLog' in subfile:
                        file_paths.append(join(trial, folder, subfile))
with concurrent.futures.ThreadPoolExecutor(500) as tp:
    future_val = {
        tp.submit(read_file, f): f
        for f in file_paths
    }
    for f in concurrent.futures.as_completed(future_val):
        item = future_val[f]
        res = f.result()
        try:
            if res['file'] == 'calibrationLog':
                log_dicts[res["ID"]] = res
            elif res['file'] == 'hardwareSetup':
                setup_dicts[res['ID']] = res
        except TypeError:
            for r in res:
                if r['file'] == 'artefactFits':
                    fits.append(r)
rowified = []
for scan in fits:
    flat = scan
    print(f'compiling data from all files for {scan["ID"]}...')
    try:
        for a in setup_dicts[scan['ID']]:
            if a in ['file']:
                continue
            flat[a] = setup_dicts[scan['ID']][a]
    except KeyError:
        pass
    try:
        for a in log_dicts[scan['ID']]:
            flat[a] = log_dicts[scan['ID']][a]
    except KeyError:
        pass
    rowified.append(flat)
    flat = {}
    print('done!')
longest = len(rowified[0])
headings = rowified[0].keys()
for r in rowified:
    if len(r)> longest:
        headings = r.keys()
with open(f'csv-report_{dt.now().strftime("%y%m%d_%H%M%S")}.csv', mode='a', newline='') as csv:
    csv_writer = DictWriter(csv, headings)
    csv_writer.writeheader()
    csv_writer.writerows(rowified)
