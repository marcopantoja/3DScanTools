from os import listdir

cam1 = {
    'maxStdError':0,
    'maxHybError':0
}
cam2 = {
    'maxStdError':0,
    'maxHybError':0
}
for f in listdir('.'):
    if 'OptimusCalibrationLog' in f:
        with open(f, 'r') as log:
            contents = log.read()
        contents = [l for l in contents.splitlines() if l!='']
        hybrid = False
        for linenum, line in enumerate(contents):
            if line.startswith('Max error'):
                read = True
            else:
                read = False
            if 'Hybrid calibration' in line and linenum>50:
                hybrid = True
                print(f'Hybrid Started on line {linenum}')
            if read:
                maxerror = float(line.split('): ')[-1])
                if '0): ' in line:
                    if maxerror>cam1['maxStdError']:
                        if hybrid or linenum>50:
                            cam1['maxHybError'] = maxerror
                        else:
                            cam1['maxStdError'] = maxerror
                elif '1): ' in line:
                    if maxerror>cam2['maxStdError']:
                        if hybrid or linenum>50:
                            cam2['maxHybError'] = maxerror
                        else:
                            cam2['maxStdError'] = maxerror