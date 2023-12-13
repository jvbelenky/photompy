from ies_utils import read_ies_data, get_intensity

lampdict = read_ies_data('LLIA001477-003.ies')

thetamap = lampdict['extended_vals']['thetas']
phimap = lampdict['extended_vals']['phis']
valuemap = lampdict['extended_vals']['values'].reshape(len(phimap),len(thetamap))

# make up some test values
newthetas = np.linspace(0,180, 100)
newphis = np.linspace(0,360,100)

thetaflat, phiflat = get_coords(newthetas, newphis, which='polar') 

intensity = [get_intensity(theta, phi, thetamap, phimap, valuemap) for theta, phi in zip(thetaflat, phiflat)]