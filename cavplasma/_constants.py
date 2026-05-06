"""Physical constants used across cavplasma. Values from scipy.constants
(CODATA 2018) wherever possible; cross-referenced to dossier `equations.md`."""

from scipy import constants as _spc

K_B = _spc.k                  # Boltzmann constant, J/K
H_PLANCK = _spc.h             # Planck constant, J·s
HBAR = _spc.hbar              # Reduced Planck constant, J·s
C_LIGHT = _spc.c              # Speed of light, m/s
E_CHARGE = _spc.e             # Elementary charge, C
M_ELECTRON = _spc.m_e         # Electron mass, kg
EPS0 = _spc.epsilon_0         # Vacuum permittivity, F/m
SIGMA_SB = _spc.sigma         # Stefan–Boltzmann, W/m²/K⁴
N_AVOGADRO = _spc.N_A         # Avogadro, 1/mol
R_GAS = _spc.R                # Gas constant, J/(mol·K)
RY_EV = 13.605693122994       # Rydberg energy, eV (CODATA 2018)
RY_J = RY_EV * E_CHARGE       # Rydberg, J

ATM_PA = 101325.0             # 1 atm in Pa (exact)
EV_J = E_CHARGE               # 1 eV in J
NM_M = 1e-9                   # 1 nm in m
