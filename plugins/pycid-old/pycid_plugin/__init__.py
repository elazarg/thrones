"""PyCID plugin service - MAID Nash equilibrium analysis."""

# Compatibility shim for pgmpy 0.1.17 which uses deprecated np.product
# (removed in numpy 2.0). Must be applied before importing pgmpy.
import numpy as np

if not hasattr(np, "product"):
    np.product = np.prod
