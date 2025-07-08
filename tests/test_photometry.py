import numpy as np
import photompy.interpolate as interp

def test_intensity_interpolation(load_ies):
    ies_file = load_ies("sample_B.ies")
    phot = ies_file.photometry      
    θ, φ = 22.5, 135.0
    v1 = phot.get_intensity(θ, φ)
    v2 = interp.get_intensity(phot, θ, φ)     # legacy helper
    np.testing.assert_allclose(v1, v2, rtol=1e-6)
