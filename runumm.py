from os.path import join
from os import getcwd
from subprocess import call
from sys import stdout

with open('console.log','w') as logfile:
    call(f'python umm2.py test Fast_Capture_Update configVol 240x200x200-6x5x5;160x120x120-8x6x6 logPath "{join(getcwd(),"console.log")}"',
        shell=True, stdout=stdout, stderr=logfile)