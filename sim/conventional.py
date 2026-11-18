"""Reference: a conventional PMOS LDO with the same pass device, used only to show the PSRR problem.

5T OTA (NMOS input pair gm/Id 15, PMOS mirror load to Vin, L = 540 nm, 100 uA tail), unity feedback
(Vref = 1.4 V), Miller-type Cc = 369 pF from gate to Vin, Cout = 470 pF (839 pF total), 10 mA load.
"""
from spice import run
from techplot import device
from design import PASS

ITAIL, CC, COUT = 100e-6, 368.9e-12, 470e-12
NIN = device('n', 540e-9, 15, 0.2, ITAIL / 2)
PLD = device('p', 540e-9, 10, PASS['vgs'], ITAIL / 2)


def netlist(vin=1.8, load=10e-3):
    return f"""Vin vin 0 {vin} AC 1
Vref ref 0 1.4
Mp1 a a vin vin pmos292p W={PLD['W']*1e6:.2f}u L=540n
Mp2 g a vin vin pmos292p W={PLD['W']*1e6:.2f}u L=540n
Mn1 a out t 0 nmos292p W={NIN['W']*1e6:.2f}u L=540n
Mn2 g ref t 0 nmos292p W={NIN['W']*1e6:.2f}u L=540n
It t 0 {ITAIL}
Mpass out g vin vin pmos292p W={PASS['W']*1e6:.0f}u L=180n
Cc g vin {CC}
Co out 0 {COUT}
Iload out 0 {load}
.nodeset V(out)=1.4
.options numdgt=12
"""


def psrr(vin=1.8, load=10e-3):
    r = run('conv', netlist(vin, load) + '.ac dec 50 10 10G\n')[0]
    return r['frequency'].real, r['v(out)']
