# umm2.py
# with added ability to tilt the pose sequence
from sys import argv
from winsound import Beep
from asyncio import new_event_loop
from asyncio.events import set_event_loop
from datetime import datetime
from math import atan2, cos, degrees, hypot, radians, sin
from os import getenv, makedirs, system
from os.path import dirname, isdir, isfile, join
from subprocess import call
from threading import Thread
from time import sleep, time
from xml.etree import ElementTree as ET
from numpy import linspace
from subprocess import call
from shutil import copy

from py_drive_api import hst, CMMFunctions, CMMConnection, ui, start_server

# handles multi-threading while api scanner is running
loop = new_event_loop()
set_event_loop(loop)

# this is where the projector cross-hairs are nominally
# at the optical centre of target sphere on CMM axes
# 0 degree tilt scanner
# Ti sphere
centreX = -335.8532
centreY = -225.6534
centreZ = -414.2453

# this is the full extent (in mm) for which each axis moves
Xmax = 160.0
Ymax = 100.0
Zmax = 100.0

nXsteps = 7
nYsteps = 7
nZsteps = 7
if 'steps' in argv:
    steps = argv[argv.index('steps')+1].split(';')
    if len(steps) == 3:
        nXsteps = int(steps[0])
        nYsteps = int(steps[1])
        nZsteps = int(steps[2])
if 'serpentine' in argv:
    serpentine = True
else:
    serpentine = False
if 'configVol' in argv:
    configuration = argv[argv.index('configVol')+1]
else:
    configuration = None
if 'dryRun' in argv:
    dry = True
else: 
    dry = False
if 'logPath' in argv:
    log_file = argv[argv.index('logPath')+1]
else:
    log_file = None
if 'runInfo' in argv:
    run_number = argv[argv.index('runInfo')+1]
else:
    run_number = ui.userInput('Enter run number for test path:','Run-',True,'Trial run input')
if 'test' in argv:
    test_folder = argv[argv.index('test')+1]
    ScanFileLocation = join('E:', 'UMM',test_folder)
else:
    ScanFileLocation = join('E:','UMM')
if 'drp' in argv:
    DRP = [
        hst.ScanOptions.DynamicRange.DRP1,
        hst.ScanOptions.DynamicRange.DRP2,
        hst.ScanOptions.DynamicRange.DRP3,
        hst.ScanOptions.DynamicRange.DRP4,
        hst.ScanOptions.DynamicRange.AUTO
    ][int(argv[argv.index('drp')+1])-1]
else:
    DRP = hst.ScanOptions.DynamicRange.DRP2
print(f'selected drp: {DRP}')
# sphere start position (bottom left corner of measurement volume)
startX = centreX - (Xmax/2.0)
startY = centreY - (Ymax/2.0)
startZ = centreZ - (Zmax/2.0)

# XYZ axis upper and lower limits
# all get more -ve as they move out from top right corner origin
Xul = -184
Xll = -506
Yul = -2
Yll = -360
Zul = -196
Zll = -616

# globals
useCMM = True
useTilt = False
useOptimus = True
returnToCentre = False
limitFound = False
save_thread = None
randomize_poselist = True

nReadings = 10
timeDelay = 0.2  # seconds
timenow = datetime.now().strftime("%Y%m%d-%H%M%S")

# for handling the tilt (if present)
def rect(r, theta):  # theta(degrees)
    x = r * cos(radians(theta))
    y = r * sin(radians(theta))
    return x, y

# also for handling the tilt (if present)
def polar(x, y):
    # returns r, theta(degrees)
    return hypot(x, y), degrees(atan2(y, x))

def createPoses(config_string = None):
    """
    generates a list of poses given the inputs
    lines 31-37 of this script. Bypass changing these
    lines and provide 'configVol' followed by a semicolon
    and hyphen delimited string to specify the scan volume.

    This must be entered from command line arguments, or
    a config string must be entered into this script.

    Use this for generating various sub-volumes or different
    pitch in different regions. ex:

    python umm2.py configVol 240x200x200-6x5x5;160x120x120-8x6x6

    running the line above will generate points fitting a volume
    240 Xmax, 200 Ymax & Zmax with 6 spaces in X and 5 in Y & Z.
    volumes seperated by semicolons and hyphens delimit vol size
    from vol steps. 
    """
    global poses;global Xmax;global nXsteps
    global Ymax;global nYsteps;global Zmax
    global nZsteps
    flop = True  # to create serpentine pattern
    flip = True
    cPdebug = False  # only for print

    if cPdebug:
        count = 0
    if serpentine:
        print(f'Test Volume--{Xmax}x{Ymax}x{Zmax}\t{nXsteps}x{nYsteps}x{nZsteps}')
        deltaX = Xmax/nXsteps
        deltaY = Ymax/nYsteps
        deltaZ = Zmax/nZsteps

        for z in range(nZsteps+1):
            Zpos = round(startZ + (z * deltaZ), 5)
            if flip:
                for x in range(nXsteps+1):
                    Xpos = round(startX + (x * deltaX), 5)
                    if not flop:
                        for y in range(nYsteps, -1, -1):
                            Ypos = round(startY + (y * deltaY), 5)
                            poses.append([Xpos, Ypos, Zpos])
                            if cPdebug:
                                count += 1
                                print(
                                    f'A [{count:2}] {Xpos:.7}, {Ypos:.7}, {Zpos:.7}')
                        flop = True
                    else:
                        for y in range(nYsteps+1):
                            Ypos = round(startY + (y * deltaY), 5)
                            poses.append([Xpos, Ypos, Zpos])
                            if cPdebug:
                                count += 1
                                print(
                                    f'B [{count:2}] {Xpos:.7}, {Ypos:.7}, {Zpos:.7}')
                        flop = False
                flip = False
            else:  # flop
                for x in range(nXsteps, -1, -1):
                    Xpos = round(startX + (x * deltaX), 5)
                    if flop:
                        for y in range(nYsteps+1):
                            Ypos = round(startY + (y * deltaY), 5)
                            poses.append([Xpos, Ypos, Zpos])
                            if cPdebug:
                                count += 1
                                print(
                                    f'C [{count:2}] {Xpos:.7}, {Ypos:.7}, {Zpos:.7}')
                        flop = False
                    else:
                        for y in range(nYsteps, -1, -1):
                            Ypos = round(startY + (y * deltaY), 5)
                            poses.append([Xpos, Ypos, Zpos])
                            if cPdebug:
                                count += 1
                                print(
                                    f'D [{count:2}] {Xpos:.7}, {Ypos:.7}, {Zpos:.7}')
                        flop = True
                flip = True
    elif config_string is not None:
        all_poses = []
        for config in config_string.split(';'):
            volume, steps = config.split('-')
            Xmax, Ymax, Zmax = [float(i) for i in volume.split('x')]
            nXsteps, nYsteps, nZsteps = [int(i) for i in steps.split('x')]
            X = linspace(centreX-Xmax/2,centreX+Xmax/2,num=nXsteps+1)
            Y = linspace(centreY-Ymax/2,centreY+Ymax/2,num=nYsteps+1)
            Z = linspace(centreZ-Zmax/2,centreZ+Zmax/2,num=nZsteps+1)
            for z in Z:
                for y in Y:
                    for x in X:
                        pose = [round(x,5),round(y,5),round(z,5)]
                        if pose not in all_poses: all_poses.append(pose)
        [poses.append(p) for p in all_poses]

    poses.append([centreX, centreY, centreZ])

    if useTilt:
        newposes = []
        posezero = []

        for i in range(len(poses)):
            posezero.append(
                [poses[i][0]-centreX, poses[i]
                [1]-centreY, poses[i][2]-centreZ])
            r, theta = polar(posezero[i][2], posezero[i][1])
            theta += tilt
            Z, Y = rect(r, theta)
            newposes.append(
                [posezero[i][0]+centreX, Y+centreY, Z+centreZ])

        # overwrite existing poses[]
        poses = newposes

    if randomize_poselist:
        from random import shuffle
        random_poses = poses[1:-1]  # leave center captures where they are
        shuffle(random_poses)
        random_poses.insert(0, poses[0])
        random_poses.append(poses[0])
        poses = random_poses

def checkLimits():
    global limitFound
    for (x, y, z) in poses:
        if not limitFound:
            if x > Xul or x < Xll:
                print(f'X-axis limit found: {x:.3f}')
                limitFound = True
            if y > Yul or y < Yll:
                print(f'Y-axis limit found: {y:.3f}')
                limitFound = True
            if z > Zul or z < Zll:
                print(f'Z-axis limit found: {z:.3f}')
                limitFound = True
        else:
            return limitFound
    return limitFound

def save_file(guid, r, scan_start, coords):
    if useOptimus:
        scan_world = (
            coords[0]-centreX, coords[2]-centreZ, -coords[1]+centreY
        )
        filenames = [
            join(ScanFileLocation, f'Scan_{str(r).zfill(4)}.obj'),
            join(ScanFileLocation, 'meshes',
                 f'({scan_world[0]},{scan_world[1]},{scan_world[2]})__({coords[0]},{coords[1]},{coords[2]}).scanmesh')
        ]
        try:
            [(scanner.ExportSurface(guid, f),print(f'saving {f.split(".")[-1]} to file', end='...')) for f in filenames]
        except hst.HippoScanToolError as e:
            print(e.message)
            return False
        print(f'{time()-scan_start:.1f}s', end=' ', flush=True)
        return True

def align_to_scanner_origin(iterations=15):
    def make_artifact_file(artifact_file):
        with open(artifact_file, 'w') as art_file:
            art_file.write('''
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <artifact type="S0" name="umm titanium 1 sphere" date="2021-05-07" revision="1">
                    <scanGuide dynamicRange="DRP2" />
                    <pointFilter maxNormalAngleError="20" outlierRemoval="0.3" />
                    <spheres>
                        <sphere name="S0" x="0" y="0" z="0" diameter="25.410" count="36" stdev_mm="0.000628092" CTE_m_m_K="8.6E-06"/>
                    </spheres>
                </artifact>
            ''')
    tolerance = 0.001  # mm
    global centreX
    global centreY
    global centreZ
    from xml.etree import ElementTree as ET
    artifact_file = join(dirname(hardwareSetupFile),
                         'artifacts', 'umm-titanium.artifact')
    if not isfile(artifact_file):
        make_artifact_file(artifact_file)
    for it in range(iterations):
        cmm.move_to(centreX, centreY, centreZ)
        sleep(6)
        print(f'Moved to center at: ({centreX},{centreY},{centreZ})')
        while True:
            try:
                align_guid = scanner.ScanOnce(scanOptions=hst.ScanOptions(
                    dynamicRange=hst.ScanOptions.DynamicRange.DRP2))
                break
            except:
                pass
        measure = ET.fromstring(scanner.MeasureArtifact(
            [align_guid], artifact_file)).find('sphereMeasures/sphereMeasure').attrib
        wx, wy, wz = float(measure['wx']), float(
            measure['wy']), float(measure['wz'])
        if abs(wx) < tolerance and abs(wy) < tolerance and abs(wz) < tolerance:
            break
        if abs(wx) > tolerance:
            centreX -= wx
            print('adjusted cX')
        if abs(wz) > tolerance:
            centreY += wz
            print('adjusted cY')
        if abs(wy) > tolerance:
            centreZ -= wy
            print('adjusted cZ')
        # makes sure we dont "automatically crash!"<--cool feature
        if centreX < Xll or centreX > Xul or centreY < Yll or centreY > Yul or centreZ < Zll or centreZ > Zul:
            raise Exception(
                'Auto-centering routine failed. Ensure start center is nominally close to scanner origin!')
        print(
            f"iteration {it}: Center coordinate aligned to scanner's world\nX={wx}\tY={wy}\tZ={wz}")
    print(f'Final Sphere Alignment:\nScanner World: ({wx},{wy},{wz})\nCMM World: ({centreX},{centreY},{centreZ})')
    scanner.Clear()
    return True

def get_in_position():
    """
    Moves cmm probe to next required position.
    """
    global poseID, READY_TO_MOVE
    # Lets us hear through door to know if it's safe to enter room
    # Long low town means we are moving / door can be opened
    Thread(target=Beep,args=(1000,3000)).start()
    # Move Here -- to X Y Z
    try:
        (x, y, z) = poses[poseID+1] # gets called by current, so always drives to next!
    except: return False
    if returnToCentre:
        if not cmm.move_to(centreX, centreY, centreZ):
            print(
                f'Error: move_to centre: ({centreX},{centreY},{centreZ})')
        sleep(2)  # wait for axes to settle
    if not cmm.move_to(x, y, z):
        print(f'Error: move_to ({x},{y},{z})')
    sleep(6)  # wait for axes to settle # was 6
    READY_TO_MOVE = False
    return True

def notificationHandler(notificationMethod, notificationParams):
    """
    starts thread to start moving cmm to next scan position.
    """
    global CHECKING_CMM_DEVIATION
    if 'on_image_capture_done' in notificationMethod and READY_TO_MOVE:
        CHECKING_CMM_DEVIATION = Thread(target=check_cmm_deviation)
        CHECKING_CMM_DEVIATION.start()

def check_cmm_deviation():
    """
    calculates if cmm probe was held steady during pattern acquisition.
    """
    global tot_retries,retry,xr,yr,zr, px,py,pz, nx,ny,nz
    global READY_TO_MOVE
    while True:
        try:
            nx, ny, nz = cmm.get_position(nReadings, timeDelay);break
        except:
            pass
    dx = (abs(px) - abs(nx))*1000.0  # calculate differences
    dy = (abs(py) - abs(ny))*1000.0
    dz = (abs(pz) - abs(nz))*1000.0
    print(f'{dx},{dy},{dz},({retry+1})', end=' ', flush=True)
    if (abs(dx) > 2.0 or abs(dy) > 2.0 or abs(dz) > 2.0) and retry < 3:
        retry += 1
        tot_retries += 1
        if abs(dx) > 2.0: xr += 1
        if abs(dy) > 2.0: yr += 1
        if abs(dz) > 2.0: zr += 1
        if retry == 3:
            READY_TO_MOVE = True
        else:
            px = nx
            py = ny
            pz = nz
    else:
        READY_TO_MOVE = True
    rf.write(f'{nx},{ny},{nz},{dx},{dy},{dz}\n')
    Thread(target=get_in_position).start()

def start_pattern_acquisition():
    """
    starts pattern capture, and verifies cmm probe did not deviate
    from intended position. retries up to 3 times"""
    global tot_retries, xr, yr, zr, READY_TO_MOVE, scan_start
    global px,py,pz, retry
    retry = 0  # number of attempts at this pose
    [Beep(400*i,120) for i in range(1,5)]
    scan_start = time()
    while True:
        try:
            px, py, pz = cmm.get_position(nReadings, timeDelay);break
        except:
            pass
    rf.write(f'{x},{y},{z},{px},{py},{pz},')
    while not READY_TO_MOVE and not dry:
        if CHECKING_CMM_DEVIATION:
            while CHECKING_CMM_DEVIATION.is_alive():pass
        if useOptimus:
            try:
                guid = scanner.ScanOnce(scanopts, filteropts)
            except hst.HippoScanToolError as e:
                guid = None
                print(e.message)
    # Save data if anything was captured
    if guid:
        save_thread = Thread(target=save_file, args=(
            guid, poseID+1, scan_start, (nx, ny, nz)))
        save_thread.start()
        print('saving...\n')

# main
start_server()
CHECKING_CMM_DEVIATION = None

if useOptimus and not dry:
    while True:
        scanner = hst()
        break
    scanner.Clear()
    hardwareSetupFile = join('HardwareSetup.scansetup')
    if isfile(hardwareSetupFile):
        while True:
            try:
                scanner.ConnectScanner(hardwareSetupFile)
                scanner.subscribe(notificationHandler)
                break
            except:
                pass
        print('Scanner calib file loaded')
        try:
            hwxml = ET.parse(hardwareSetupFile).getroot()
            unitID = hwxml.attrib['serialNumber']
            tilt = round(float(hwxml.find('calibrationInfo').attrib['tiltAngleScanner']))
            cams = [c.attrib['name'].split(' ')[0].strip('Optimus-').replace('-','') 
                for c in hwxml.findall('cameras/camera')]
            ScanFileLocation = join(ScanFileLocation, unitID[8:]+'_'+str(tilt)+'-deg', unitID[8:]+f'_{"-".join(cams)}', timenow +
                f'_({Xmax},{Ymax},{Zmax})-({nXsteps+1},{nYsteps+1},{nZsteps+1})_{run_number}')
        except:
            pass
    else:
        raise Exception(
            'Hardware Setup does not exist at '+hardwareSetupFile)
    scanopts = hst.ScanOptions(
        dynamicRange=DRP,# Ti sphere
        scanProfile=hst.ScanOptions.ScanQuality.Quality
    )  # set up some scanning options

    filteropts = hst.FilterOptions()  # use the default filtering options
    print('Set scan and filter options')

    scanner.SetStandbyProjectionMode(hst.StandbyProjectionMode.SINE_SWEEP)

if useTilt:
    print(f'{tilt} degree tilt, ', end='')

if useCMM:
    conn = CMMConnection('CMM_IP_ADDR', 4321)
    cmm = CMMFunctions(conn)
    cmm.set_move_timeout(30000)
    print('connected to cmm...\naligning to scanner origin...')
    if not dry and useOptimus: align_to_scanner_origin()
    if not isdir(ScanFileLocation):
        makedirs(join(ScanFileLocation, 'meshes'))
    print('creating pose grid...')
    poses = [[centreX, centreY, centreZ]]
    createPoses(configuration)
    nPoses = len(poses)
    print(f'{nPoses} poses')
    rf = open(join(ScanFileLocation, f'{timenow}-{str(nPoses)}.csv'), 'w')
    if rf:
        print('Opened ' + timenow + '-' + str(nPoses) + '.csv')
        rf.write(
            'x (mm),y (mm),z (mm),px (mm),py (mm),pz (mm),nx (mm),ny (mm),nz (mm),dx (um),dy (um),dz (um)\n')
    start = time()
    tot_retries = 0
    xr, yr, zr = 0, 0, 0
    if not checkLimits():  # check poses do not go outside XYZ limits
        # called once to start, since positioning is now called from scan notification threads
        poseID=-1;get_in_position()
        for poseID,(x, y, z) in enumerate(poses):
            print(f'{poseID+1}:', end=' ', flush=True)  # did start with Pose
            # Wait for save and Clear last scan
            if save_thread:
                if save_thread.is_alive():
                    print('still saving...', end=None)
                while save_thread.is_alive():
                    pass
                if not dry:scanner.Clear()
                print('done saving')
            # Get next Scan
            start_pattern_acquisition()
    if rf:
        rf.close()

    taken = time() - start
    print(f'Took {taken}s\nTotal retries: {tot_retries}', flush=True)
    print(f'{xr} X, {yr} Y, {zr} Z axis retries', flush=True)
    conn.disconnect()
print("Done")
if save_thread:
    while save_thread.is_alive():
        pass
[system('taskkill /f /im '+s)for s in ['sohal.exe', 'sohalPass.exe']]
call(f'py ProcessUmm.py workdir "{ScanFileLocation}"')
call(f'py ProcessUmm.py workdir "{ScanFileLocation}" nomR')
print('finished processing data!')
if log_file is not None:
    try: copy(log_file, join(ScanFileLocation,'console.log'))
    except: pass