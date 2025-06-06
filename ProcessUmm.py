from csv import DictWriter
from os import getcwd, makedirs
from os.path import basename, isdir, isfile, join, sep
from subprocess import call
from sys import argv


import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, hex2color
from py_drive_api.dependencies.umm_sd import umm

if 'workdir' in argv:
    dir = argv[argv.index('workdir')+1]
    run_again = False
else:
    dir = getcwd()
    run_again = True
if 'subvolume' in argv:
    subvolume = True
    vol_label = argv[argv.index('subvolume')+1]+'_'
    volume = [float(v)/2 for v in vol_label[:-1].split('x')]
    diam_vol = ' '.join(['subvolume',vol_label[:-1]])
else:
    subvolume = False; volume=None; vol_label=''; diam_vol=''
if 'vbbLim' in argv:
    vbbLim = [float(v) for v in argv[argv.index('vbbLim')+1].split(';')]
    vbbLim = (min(vbbLim),max(vbbLim))
    print('Limiting vbb plot to ',vbbLim)
else:
    vbbLim = (-80,80)
if 'title' in argv:
    title=argv[argv.index('title')+1]
else:
    title = f'Run {basename(dir)[-1]} '
if 'processedFile' in argv:
    vol_label += 'sphereDetector_'
    useNomR = None
    fName = argv[argv.index('processedFile')+1]
    if not isfile(fName): raise Exception(f'The file {fName} could not be opened or does not exist!')
else:
    if 'nomR' in argv:
        useNomR = True
        fName = 'multiprocess-nomR-scanDataCSV_P.txt'
    else:
        useNomR = False
        fName = 'multiprocess-actR-scanDataCSV_P.txt'
if 'cmmView' in argv:
    cmmCoords = True
    vol_label += 'cmm-coords_'
else:
    cmmCoords = False


def PlotScatter2D(x, y, ax, size, col, marker, **kwargs):

    if ax==0:
        fig = plt.figure(figsize=(19.20,10.80),dpi=800)
        ax = plt.axes()

    ax.scatter(x, y, s=size, c=col, marker=marker,
        **kwargs)
    return ax

def PlotPoints3D(v3d, n, ax, size, col):

    if ax==0:
        fig = plt.figure()
        ax = plt.axes(projection='3d')
            
    if n!=0:
        x = np.zeros(2)
        y = np.zeros(2)
        z = np.zeros(2)
        
        c = np.mean(v3d, 0)
        x[:] = c[0]
        y[:] = c[1]
        z[:] = c[2]

        x[1] = x[1]+n
        ax.plot(x, y, z, 'r')
        x[1] = c[0]

        y[1] = y[1]+n
        ax.plot(x, y, z, 'g')
        y[1] = c[1]

        z[1] = z[1]+n
        ax.plot(x, y, z, 'b')
        z[1] = c[2] 

    ax.scatter(v3d[:, 0], v3d[:, 1], v3d[:, 2], s=size, c=col, marker='*')
    return ax

def Plotline3D(v3d, ax, lw, col):

    if ax==0:
        fig = plt.figure(figsize=(40.96,21.60),dpi=600)
        ax = plt.axes(projection='3d')

    v3d = np.copy(v3d)  # to ensure that the drawn line can not be changed in the future

    ax.plot(v3d[:, 0], v3d[:, 1], v3d[:, 2], lw=lw, c=col)

    return ax

def Sphere(c, r, n):
    u = np.linspace(0, np.pi, n)
    v = np.linspace(0, 2 * np.pi, n)

    x = np.outer(np.sin(u), np.sin(v))
    y = np.outer(np.sin(u), np.cos(v))
    z = np.outer(np.cos(u), np.ones_like(v))

    x = x*r+c[0]
    y = y*r+c[1]
    z = z*r+c[2]

    return x, y, z

def DisplaySpheres(v3d, r, n, ax, col, col_map=None, **kwargs):

    if ax==0:
        fig = plt.figure(figsize=(40.96,21.60),dpi=600)
        ax = plt.axes(projection='3d')

    if n!=0:
        x = np.zeros(2)
        y = np.zeros(2)
        z = np.zeros(2)

        c = np.mean(v3d, 0)
        x[:] = c[0]
        y[:] = c[1]
        z[:] = c[2]

        x[1] = x[1]+n
        x[1] = c[0]

        y[1] = y[1]+n
        y[1] = c[1]

        z[1] = z[1]+n
        z[1] = c[2] 

        try:
            ax.plot(x, y, z, 'r')
            ax.plot(x, y, z, 'g')
            ax.plot(x, y, z, 'b')
        except TypeError:
            x = x.get()
            y = y.get()
            z = z.get()
            ax.plot(x, y, z, 'r')
            ax.plot(x, y, z, 'g')
            ax.plot(x, y, z, 'b')
    N = v3d.shape[0]

    for i in range(N):
        x, y, z = Sphere(v3d[i, :], r[i], 10)
    
        try:
            wf= ax.plot_wireframe(x, y, z, linewidth=0.10, facecolors=col[i], color='k',cmap=col_map, **kwargs)
        except TypeError:
            x = x.get()
            y = y.get()
            z = z.get()
            wf= ax.plot_wireframe(x, y, z, linewidth=0.10, facecolors=col[i], color='k',cmap=col_map, **kwargs)
    if col_map is not None:
        fig.colorbar(ax.get_children()[0],orientation='horizontal', shrink=0.5, extend='both').set_label(
            "Error in um",size=35
        )
    return ax

def PairWiseLengths(cXYZ):
    """ lengths = PairWiseLengths (cXYZ)
       find the lengths between all pairs 
       cXYZ is an nx3 matrix of XYZ data
    """

    n = cXYZ.shape[0] 

    X = np.broadcast_to(cXYZ[:, 0].reshape((1, n)), (n, n))-np.broadcast_to(cXYZ[:, 0].reshape((n, 1)), (n, n))
    Y = np.broadcast_to(cXYZ[:, 1].reshape((1, n)), (n, n))-np.broadcast_to(cXYZ[:, 1].reshape((n, 1)), (n, n))
    Z = np.broadcast_to(cXYZ[:, 2].reshape((1, n)), (n, n))-np.broadcast_to(cXYZ[:, 2].reshape((n, 1)), (n, n))
    
    CoG = [np.mean(X),np.mean(Y),np.mean(Z)]

    lenMatrix = np.sqrt(X**2 + Y**2 + Z**2)
    CGs = np.hypot((X-CoG[0])/2,(Y-CoG[1])/2,(Z-CoG[2])/2)#vbb pairs midpoint to CG
    index = np.zeros((n, n), dtype=int)
    index2 = np.zeros((int(n*(n-1)/2), 2), dtype=int)

    for i in range(n-1):
        index[i, i+1:n] = 1

    iIndex = np.broadcast_to(np.array(np.arange(n), dtype=int).reshape((n, 1)), (n, n))
    jIndex = np.broadcast_to(np.array(np.arange(n), dtype=int).reshape((1, n)), (n, n))   

    lengths = lenMatrix[index==1]
    CG_dist = CGs[index==1]
    index2[:, 0] = iIndex[index==1]
    index2[:, 1] = jIndex[index==1]

    return lengths, index2, CG_dist

def DisplayVectors(start, end, reCenter=None):
    direction = end-start
    if reCenter is not None: start = reCenter
    fig = plt.figure(figsize=(40.96,21.60))
    ax = plt.axes(projection='3d')
    ax.quiver3D(start[:,0], start[:,1], start[:,2], direction[:,0], direction[:,1], direction[:,2],arrow_length_ratio=1000,
    linewidth=1.3,color='k',)
    return ax

def save_data(
scan_Dir,
cAll=None,
rAll=None,
cmmPos=None,
R=None,
t=None,
cT=None,
atC=None,
mag=None,
lengths1=None,
lengths2=None,
diff_lengths=None,
cg_dist=None,
indices=None,
output_name_pref=''):
    output_name_pref=output_name_pref.strip().replace(' ','-')
    if not isdir(scan_Dir): makedirs(scan_Dir)
    if (cAll is not None and
        rAll is not None and
        cmmPos is not None and
        cT is not None and
        atC is not None and
        mag is not None):
        coords = [{
            'cX':c[0],'cY':c[1],'cZ':c[2],
            'diameter':rAll[i]*2,
            'cmmX':cmmPos[i,0],'cmmY':cmmPos[i,1], 'cmmZ':cmmPos[i,2],
            'cXa':cT[i,0],'cYa':cT[i,1],'cZa':cT[i,2],
            'scan_number':atC[i],'residual_error':mag[i],
            'nx':R[0,0],'ny':R[0,1],'nz':R[0,2],
            'ox':R[1,0],'oy':R[1,1],'oz':R[1,2],
            'ax':R[2,0],'ay':R[2,1],'az':R[2,2],
            'Px':t[0],'Py':t[1],'Pz':t[2],
        } for i, c in enumerate(cAll)]
        with open(join(scan_Dir,output_name_pref+'coordinate-data.log'), 'w',newline='') as cfile:
            w = DictWriter(cfile,coords[0].keys())
            w.writeheader()
            w.writerows(coords)
    if (lengths1 is not None and 
        lengths2 is not None and
        diff_lengths is not None and
        cg_dist is not None and
        indices is not None):
        calculated = [{
            'Lenth_Target':l,
            'Length_Actual':lengths2[i],
            'Length_Error':diff_lengths[i],
            'cg_dist_to_center':cg_dist[i],
            'point1':indices[i][0],'point2':indices[i][1]
        }for i, l in enumerate(lengths1)]
        with open(join(scan_Dir,output_name_pref+'vbb-data.log'),'w',newline='') as cfile:
            w = DictWriter(cfile,calculated[0].keys())
            w.writeheader()
            w.writerows(calculated)
    return True

def filter_volume(centers:np.ndarray, radii, positions:np.ndarray,
    scan_numbers, rotation, translation, error_mag, transformed_centers):
    from numpy.linalg import norm
    from py_drive_api.dependencies.umm_sd.Transform3D import (
        ApplyRigidTransform, RobustTransform3D)
    if volume is not None:
        print(f'filtering data to {vol_label[:-1]}. started with {centers.shape[0]} points',end='...')
        tol = 2 #tolerance in mm for clipping volume
        for i in range(3):
            print(f'removing points out of {["x","y","z"][i]} bounds: ({-volume[i]-tol},{volume[i]+tol})')
            mask =( 
                (centers[:,i]>-volume[i]-tol) & (centers[:,i]<volume[i]+tol)
            )
            centers = centers[mask]
            radii=radii[mask]
            positions=positions[mask]
            scan_numbers=scan_numbers[mask]
            print(f'{centers.shape[0]} points remaining')
    while False in mask:
        rotation, translation = RobustTransform3D(centers, positions, 10)
        transformed_centers = ApplyRigidTransform(centers, rotation, translation)
        error_mag = norm(positions-transformed_centers, axis=1)
        mask = error_mag<0.05
        centers=centers[mask]
        radii=radii[mask]
        positions=positions[mask]
        scan_numbers=scan_numbers[mask]
    print(f'done filtering data with {centers.shape[0]} points left!')
    return centers, radii, positions, scan_numbers, rotation, translation, error_mag, transformed_centers

def run_UMM(scan_Dir):
    def plot_centers():
        fig = plt.figure(figsize=(40.96,21.60),dpi=dpi_glo)
        ax2 = fig.gca()
        ax2.plot(cD2M[:, 0], lw=0.5, c='r')
        ax2.plot(cD2M[:, 1], lw=0.5, c='g')
        ax2.plot(cD2M[:, 2], lw=0.5, c='b')
        ax2.legend(['x','y','z'])
        plt.title(f'{unit_label} Center Coordinates (mm)',fontsize=title_size)
        ax2.autoscale(tight=True)
        ax2.set_xlabel('Scan Number',fontsize=label_size)
        ax2.set_ylabel('Position in (mm)',fontsize=label_size)
        plt.savefig(join(scan_Dir,vol_label+'center-coordinates.png'),dpi=dpi_glo)
    
    def plot_tomatos():
        ax = DisplaySpheres(plotpoints, mag*300, 0, 0, [hex2color('#C03854') for _ in range(cmmPos.shape[0])])
        ax.autoscale(tight=True)
        ax.set_xlabel('Scanner Z',fontsize=label_size)
        ax.set_ylabel('Scanner X',fontsize=label_size)
        ax.set_zlabel('Scanner Y',fontsize=label_size)
        plt.title(
            f'{unit_label} Position Error Magnitudes\nMax Abs: {maxMag*1000:.3f} um, Mean: {meanMag*1000:.3f} um\n'+
            f'N={plotpoints.shape[0]}',
            fontsize=title_size)
        if not isfile(join(scan_Dir,vol_label+'position-tomato.png')):
            plt.savefig(join(scan_Dir,vol_label+'position-tomato.png'))
        ax = Plotline3D(plotpoints, ax, 0.25, '#6B3A97')
        ax.legend(['CMM Path'])
        plt.savefig(join(scan_Dir,vol_label+'position-tomato-with-path.png'),dpi=dpi_glo)
    
    def plot_vectors():
        ax4 = DisplayVectors(cmmPos, cT)
        ax4.set_xlabel('Scanner X',fontsize=label_size)
        ax4.set_ylabel('Scanner Z-->',fontsize=label_size)
        ax4.set_zlabel('Scanner Y',fontsize=label_size)
        plt.title(f'{unit_label} Position Error Directions',fontsize=title_size)
        ax4.autoscale(tight=True)
        plt.savefig(join(scan_Dir, vol_label+'position-error-vectors.png'),dpi=dpi_glo)

    def plot_vbb():
        lengths1, ind1, cg_dist1 = PairWiseLengths(cAll)
        lengths2, ind2, cg_dist2 = PairWiseLengths(cmmPos)
        diff_lengths = (lengths1-lengths2)
        N=lengths2.shape[0]
        if N>600000: alp=0.2
        elif N>50000: alp=0.45
        elif N>5000: alp=0.6
        elif N>500: alp=0.9
        else: alp=1
        pt_colors = []
        sizes = []
        for diff in diff_lengths:
            if diff == diff_lengths.max or diff == diff_lengths.min:
                sizes.append(4)
                pt_colors.append('k')
            else:
                sizes.append(1.5)
                pt_colors.append(hex2color('#C03854'))
        ax2d = PlotScatter2D(lengths2, diff_lengths*1000, 0, sizes, pt_colors, '.',alpha=alp)
        ax2d.autoscale(tight=True)
        meanLerror = np.mean(diff_lengths,axis=0)*1000
        maxLerror = np.max(diff_lengths)*1000;minLerror = np.min(diff_lengths)*1000
        plt.title(f'{unit_label} Virtual Ball Barr Errors (N = {N})\nMax: {maxLerror:.3f} um, Min:{minLerror:.3f} um, Mean: {meanLerror:.3f} um',
        fontsize=title_size)
        [ax2d.axhline(y=yy, color='g', linestyle=':', linewidth=1.5) for yy in [-20,20,0]]
        [ax2d.axhline(y=yy, color='#6B3A97', linestyle='-', linewidth=.75) for yy in [minLerror, maxLerror, meanLerror]]
        ax2d.set_xlabel('VBB Length (mm)',fontsize=label_size)
        ax2d.set_ylabel('Measured Error (um)',fontsize=label_size)
        ax2d.set_ylim(vbbLim)
        plt.savefig(join(scan_Dir,vol_label+'all-vbb-errors.png'),dpi=dpi_glo)
        print(f'Length Errors: Mean = {meanLerror*1000:.4} um Max = {maxLerror:.3f} um, Min = {minLerror:.3f} um')
        return lengths1,lengths2,diff_lengths,cg_dist2,ind2

    def plot_diameters():
        d_glo = 25.410
        dAll = rAll*2 - d_glo
        meanDerror = np.mean(dAll)
        maxDerror = np.max(dAll);minDerror = np.min(dAll)
        if abs(minDerror)>maxDerror: maxDerror=minDerror
        print('Diameter Errors: Mean = {:.4} um and Max= {:.4} um'.format(meanDerror*1000, maxDerror*1000))
        colnorm=Normalize(vmin=-20, vmax=20, clip=True)
        ax3 = DisplaySpheres(plotpoints, dAll*200, 100, 0, ScalarMappable(norm=colnorm, cmap='viridis').to_rgba(dAll*1000,0.95),'viridis')
        ax3.set_xlabel('Scanner Z',fontsize=label_size)
        ax3.set_ylabel('Scanner X',fontsize=label_size)
        ax3.set_zlabel('Scanner Y',fontsize=label_size)
        ax3.autoscale(tight=True)
        plt.title(f'{unit_label} Diameter Errors\nMax: {maxDerror*1000:.3f} um, Mean: {meanDerror*1000:.3f} um',
        fontsize=title_size)
        plt.savefig(join(scan_Dir,vol_label+'diameter-errors.png'),dpi=dpi_glo)

    print(scan_Dir)
    unit_label = [l for l in scan_Dir.split(sep) if l.startswith('LP-')]
    if len(unit_label)==1: 
        print(f'detected data from unit {unit_label[0]} {title}')
        unit_label = unit_label[0]+' '+title
    else:
        unit_label = title

    cAll, rAll, cmmPos, atC, R, t, mag, cT = umm.UmmProcessDir(
        scan_Dir, fName, useNomR, globalR=25.410/2, doClean=False
    )

    if mag.size==0:
        print("failed to find consistent scan and CMM data")
        return

    if subvolume:
        cAll, rAll, cmmPos, atC, R, t, mag, cT = filter_volume(cAll, rAll, cmmPos, atC, R, t, mag, cT)
    dpi_glo = 700
    label_size = 18
    title_size = 24
    cMean = np.mean(cAll, axis=0)
    cD2M = cAll-cMean.reshape((1,3))
    if cmmCoords:
        plotpoints = cmmPos
    else:
        plotpoints = [(c[2],c[0],c[1]) for c in cD2M]
        plotpoints = np.array(plotpoints)
    
    if useNomR or useNomR is None:
        magTh = 0.05
        meanMag = np.mean(mag[mag<magTh])
        maxMag = np.max(mag[mag<magTh])
        print('Position:  Mean = {:.4} um and Max Abs = {:.4} um'.format(meanMag*1000, maxMag*1000))

        #Center aligned residual errors
        if not isfile(join(scan_Dir,vol_label+'position-tomato-with-path.png')):
            plot_tomatos()

        #Virtual Ball-bars
        if not isfile(join(scan_Dir,vol_label+'all-vbb-errors.png')):
            lengths1, lengths2, diff_lengths, cg_dist2, ind2 = plot_vbb()
        else: lengths1 = lengths2 = diff_lengths = cg_dist2 = ind2 = None

        #Plot Position Error Vectors
        if not isfile(join(scan_Dir, vol_label+'position-error-vectors.png')):
            plot_vectors()
        save_data(scan_Dir,cAll,rAll,cmmPos,R,t,cT,atC,mag,lengths1,lengths2,diff_lengths, cg_dist2, ind2, unit_label+'-fixedFit-')
    #Actual Radius fits
    if not useNomR or useNomR is None:
        if useNomR is None:
            rAll = rAll[:,1]
        #Atomic Tomatos Plot-Diameter Errors
        if not isfile(join(scan_Dir,vol_label+'diameter-errors.png')):
            plot_diameters()
            save_data(scan_Dir, cAll, rAll, cmmPos, R, t, cT, atC, mag, output_name_pref=unit_label+'-variableFit-')
            exit()

if __name__ == '__main__':
    if run_again and useNomR is not None:
        call(f'py "ProcessUmm.py" workdir "{dir}" nomR title "{title}" '+diam_vol,shell=True,cwd=dir)
    run_UMM(dir)
    exit()
