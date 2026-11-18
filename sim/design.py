"""NCM-LDO design point (180 nm, TT, 27 C). Every simulation, figure, the schematic and the design sheet use this.

Spec: 1.71-1.89 V in, 1.40 V out, 8-10 mA (stable 0-10 mA), <= 300 uA overhead, <= 1 nF total capacitance.
"""
from techplot import device

VIN_NOM, VOUT, ILOAD = 1.8, 1.4, 10e-3
VIN_MIN = 1.71

# Pass device: gm/Id = 10 at 10 mA, L = 180 nm, |VDS| = 1.71 - 1.40 = 0.31 V (worst case, low line)
PASS = device('p', 180e-9, 10, VIN_MIN - VOUT, ILOAD)

D = dict(
    # mirror power stage: Mpass = N x Mref; cascode Mc holds Mref's drain r at Vout; Cn neutralises N*Cgd
    N=100, Wpass=PASS['W'], Wc=40e-6, Cn=1.0e-12, Rg=20e3,
    # driver: NMOS Mdrv (W/L = 24/1 um) cascoded by Mcn (gate at 0.9 V)
    Wdrv=24e-6, Ldrv=1e-6, Wcn=20e-6, Vcn=0.9,
    # error amplifier, powered from Vout: PMOS input pair, NMOS mirror load, divider to 0.5 V reference
    Itail=50e-6, Wpi=20e-6, Wnl=3e-6, Lea=540e-9, Rtop=180e3, Rbot=100e3, Vref=0.5, Cff=8e-12,
    Rz=4e3, Cz=100e-12,
    # tracking amplifier, powered from Vout: followers -> degenerated NMOS pair -> PMOS mirror
    Wf=4e-6, If=20e-6, Wp=12e-6, It=30e-6, Rdeg=13e3, Cdeg=150e-15, Wl=6e-6,
    # output capacitor (trimmed so the total intentional capacitance is exactly 1 nF)
    Cout=890.85e-12,
    # start-up kick (powered from Vin): Msp weak pull-up, Msn+Msd stack trips at ~2 Vth of Vout; while Vout is low,
    # follower Mku charges the error-amp output od (held by Cz, so the kick is remembered: no chatter). Off afterwards.
    Wsp=1e-6, Lsp=4e-6, Wsn=2e-6, Wsd=2e-6, Lsn=540e-9, Wku=0.5e-6, Lku=4e-6,
)

CAP_TOTAL = D['Cout'] + D['Cz'] + D['Cff'] + D['Cn'] + D['Cdeg']
