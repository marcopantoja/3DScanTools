from os import listdir, getcwd
from os.path import join, isdir
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from csv import DictWriter


all_data = []
for trial in listdir(getcwd()):
    if isdir(trial):
        for tilt in listdir(trial):
            for calib_source in listdir(join(trial, tilt)):
                data = {}
                with ZipFile(join(trial, tilt, calib_source)) as zip_file:
                    for f in zip_file.filelist:
                        if f.filename.endswith('.3dscansetup'):
                            setup = ET.fromstring(zip_file.read(f))
                temps = [t.attrib for t in setup.findall('calibrationInfo/temperatures/temperature') if 'camera' in t.attrib['name']]
                data['Tilt'] = tilt
                data['Trial'] = trial
                data['ZipDir'] = calib_source.split('_')[-1]
                for t in temps:
                    data[t['name']] = t['value']
                all_data.append(data)
headings = ['Tilt', 'Trial', 'camera1', 'camera2', 'ZipDir']
with open('temp-data.csv', mode='a', newline='') as csvfile:
    writer = DictWriter(
        csvfile, 
        headings,
        '-'
    )
    writer.writeheader()
    writer.writerows(all_data)