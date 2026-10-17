import sys; sys.path.insert(0, '/tmp/bl2')
from k2 import *
sc, cam = reset(10)
L, TW = letters('DELFONA', 57.7, 0.24)
print('CAL TW', TW, 'CAP', cap_height(57.7), 'first', L[0][1], 'last', L[-1][1], L[-1][2])
