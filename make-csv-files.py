from csv import DictWriter
from datetime import datetime as dt
from os import getcwd, listdir
from os.path import isdir, join
from sys import argv
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from time import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def flatten_metadata(metadata_stream):
    scan_meta = ET.fromstring(metadata_stream)
    flat = {}
    flat['scan_name'] = scan_meta.attrib['name']
    flat['file'] = 'metadata'
    for entry in scan_meta:
        if entry.tag == 'metaentry':
            flat[entry.attrib['name']] = entry.attrib['value']
        elif entry.tag == 'metatree' and entry.attrib['name'] == 'hardwareSetup':
            hwSetup = entry.find('hardwareSetup')
            for a in hwSetup.attrib:
                flat[f'hardwareSetup_{a}'] = hwSetup.attrib[a]
            calibInfo = hwSetup.find('calibrationInfo')
            projectors = hwSetup.find('projectors')
            cameras = hwSetup.find('cameras')
            for a in calibInfo.attrib:
                flat[f'calibrationInfo_{a}'] = calibInfo.attrib[a]
            for ch in calibInfo:
                for a in ch.attrib:
                    flat[f'calibrationInfo_{ch.tag}_{a}'] = ch.attrib[a]
                for item in ch:
                    if ch.tag=='temperaturesStatistics':
                        for a in item.attrib:
                            if a == 'name': continue
                            flat[f'calibrationInfo_{ch.tag}_{item.attrib["name"]}_{a}'] = item.attrib[a]
                    else:
                        for a in item.attrib:
                            if a != 'name' and a != 'value':
                                flat[f'calibrationInfo_{item.tag}_{a}'] = item.attrib[a]
                            elif a == 'name' and len(item.attrib)==2:
                                flat[f'calibrationInfo_{item.tag}_{item.attrib["name"]}'] = item.attrib['value']
            c_p = [cameras, projectors]
            for i in c_p:
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
        elif entry.tag == 'metatree':
            if entry.attrib['name']=='capturePatternsStatistics': # specific parser for stats tree
                for stats in entry:
                    for a in stats.attrib:
                        flat[f'{stats.tag}_{a}'] = stats.attrib[a]
                    for cam in stats:
                        for a in cam.attrib:
                            flat[f'{stats.tag}_{cam.tag}_{a}'] = cam.attrib[a]
            else: # generic parse metatree
                if entry.attrib['name']=='referenceData' and entry[0].attrib['name']=='python': entry = entry[0]
                for a in entry:
                    if a.tag=='alignmentGuide': # specific format for alignmentGuide elements
                        for att in a.attrib:
                            flat[f'{entry.attrib["name"]}_{a.tag}_{att}'] = a.attrib[att]
                    if a.tag=='metaentry': flat[f'{entry.attrib["name"]}_{a.attrib["name"]}'] = a.attrib['value']
    print(f'done reading {flat["scan_name"]}!')
    return flat

def flatten_artefact_fits(xml_stream):
    fits = ET.fromstring(xml_stream)
    flattened_fits = []
    try:
        xml_stream = xml_stream.decode()
    except:
        pass
    if 'artefact' in xml_stream:
        tag = 'artefactFit'
    elif 'artifact' in xml_stream:
        tag = 'artifactFit'
    for fit in fits.findall(tag):
        flat = {}
        flat['scan_name'] = fit.attrib['scan']
        flat['file'] = 'artifactFits'
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
                    if measure is None: continue
                    for a in measure.attrib:
                        if a not in ['scan', 'name', 'x', 'y', 'z']:
                            flat[f'{measure.attrib["name"]}_{a}'] = measure.attrib[a]
                distances = fits.findall(f"distanceMeasures/distanceMeasure[@scan='{fit.attrib['scan']}']")
                if len(distances)==0: distances = fits.findall(f"distanceMeasures/sphereDistanceMeasure[@scan='{fit.attrib['scan']}']")
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
    print(f'done reading {flat["scan_name"]}')
    return flattened_fits

def handle_file(input_arg):
    if type(input_arg) is str:
        if input_arg.endswith('Fits.xml'):
            with open(input_arg,'r') as fitxml:
                return flatten_artefact_fits(fitxml.read())
        elif input_arg.endswith('.metadata'):
            with open(input_arg, 'r') as metaxml:
                return flatten_metadata(metaxml.read())
    elif type(input_arg) is tuple and len(input_arg)==2:
        with ZipFile(input_arg[0]) as measurezip:
            if input_arg[1].endswith('Fits.xml'):
                return flatten_artefact_fits(measurezip.read(input_arg[1]).decode())
            elif input_arg[1].endswith('.metadata'):
                return flatten_metadata(measurezip.read(input_arg[1]).decode())
    return True

if 'workdir' in argv:
    workdir = argv[argv.index('workdir')+1]
else:
    workdir = getcwd()
if 'multiCSV' in argv:
    multiOutputMode = True
else: 
    multiOutputMode = False
    all_output_data = []
    all_headings = {}
if 'ReScanPyOut' in argv:
    calibIsTimeStamp = True
else: calibIsTimeStamp = False

start = time()
all_inputs = []
for calib in listdir(workdir):
    metadata = {}
    fits = []
    if not isdir(join(workdir, calib)): continue
    for f in listdir(join(workdir, calib)):
        if f.endswith('Fits.xml'):
            all_inputs.append(join(workdir, calib, f))
        if f.endswith('.metadata'):
            all_inputs.append(join(workdir, calib, f))
        if 'Measured' in f and f.endswith('.zip'):
            with ZipFile(join(workdir, calib, f)) as measureZip:
                for f in measureZip.filelist:
                    if 'Fits.xml' in f.filename:
                        all_inputs.append((join(workdir, calib, measureZip.filename), f.filename))
                    elif f.filename.endswith('.metadata'):
                        all_inputs.append((join(workdir, calib, measureZip.filename), f.filename))
    with ThreadPoolExecutor(500) as tp:
        future = {
            tp.submit(handle_file, i): i
            for i in all_inputs
        }
        all_inputs = []
        for f in as_completed(future):
            res = f.result()
            try:
                if res['file']=='metadata':
                    metadata[res['scan_name']] = res
            except TypeError:
                if res is None: continue
                for r in res:
                    if 'Fit' in r['file']:
                        fits.append(r)
    rowified = []
    for scan in fits:
        print(f'compiling data for {scan["scan_name"]}...')
        if calibIsTimeStamp:
            try:
                if int(scan['scan_name'].split('_')[4])<int(calib): continue #if the scan was taken before calibration, skip it
            except TypeError:
                pass
        flat = scan
        try:
            for a in metadata[scan['scan_name']]:
                flat[a] = metadata[scan['scan_name']][a]
        except KeyError:
            pass
        rowified.append(flat)
        flat = {}
    headings = {}
    for r in rowified:
        if not multiOutputMode:
            r['SourceFolder'] = calib
            all_output_data.append(r)
        for item in r:
            try:
                headings[item]+=1
                if not multiOutputMode: all_headings[item]+=1
            except KeyError:
                headings[item] = 1
                if not multiOutputMode: all_headings[item] = 1
    if multiOutputMode:
        with open(join(workdir, f'csv-report_{dt.now().strftime("%y%m%d_%H%M%S")}_{calib}.csv'), mode='x', newline='') as csv:
            csv_writer = DictWriter(csv, headings)
            csv_writer.writeheader()
            csv_writer.writerows(rowified)
if not multiOutputMode:
    with open(join(workdir, f'csv-report_{dt.now().strftime("%y%m%d_%H%M%S")}.csv'), mode='x', newline='') as csv:
        csv_writer = DictWriter(csv, all_headings)
        csv_writer.writeheader()
        csv_writer.writerows(all_output_data)
print(f'runtime was {time()-start} seconds!')