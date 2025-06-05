from subprocess import call


tilt_types = [
    'BothTilt',
    'PositiveTilt',
    'NegativeTilt'
]
for t in tilt_types:
    for tr in range(2,4):
            call(f'py MOAC.py {t} Trial {tr} hybridFilter (+00Pz+00Ry+45T)')
