import numpy as np
import matplotlib.pyplot as plt


def plot_3d(
    x,
    y,
    z,
    intensity,
    elev=-90,
    azim=90,
    show_cbar=False,
    figsize=(6, 4),
    alpha=0.7,
    cmap="rainbow",
):
    """
    Make a 3d intensity plot

    x,y,z: cartesian coordinates, must be 1-D arraylike
    intensity: value associated with coordinates,
    elev: configure alitude of camera angle of 3d plot (0-90 degrees). Defa
    azim: configure horizontal/azimuthal camera angle of 3d plot
    show_cbar: Optionally show colorbar of intensity values (default=False)
    figsize: alter figure size  (default=(6,4))
    alpha: transparency, 0-1 (default=0.7)
    cmap: colormap keyword (default='rainbow')
    """

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")

    img = ax.scatter(x, y, z, c=intensity, cmap="rainbow", alpha=alpha)

    if show_cbar:
        cbar = fig.colorbar(img)
        cbar.set_label("Intensity")

    ax.view_init(azim=azim, elev=elev)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    plt.show()


def polar_to_cartesian(theta, phi, distance=1):
    """
    Convert polar coordinates to cartesian coordinates.

    Parameters:
    theta (float): Polar angle in degrees. 0 degrees is down, 180 is up.
    phi (float): Azimuthal angle in degrees.
    distance (float): Radius value. Assumed to be 1 meter.

    Returns:
    tuple: (x, y, z, value) in Cartesian coordinates.
    """
    # Convert angles to radians
    theta_rad = np.radians(180 - theta)  # to account for reversed z direction
    phi_rad = np.radians(phi)

    # Polar to Cartesian conversion
    x = np.sin(theta_rad) * np.sin(phi_rad)
    y = np.sin(theta_rad) * np.cos(phi_rad)
    z = np.cos(theta_rad)

    return x, y, z


def get_coords(thetas, phis, which="cartesian"):
    """
    Get an ordered pair of lists of coordinates.
    thetas: arraylike of vertical angles
    phis: arraylike of horizontal angles
    which: {'cartesian','polar'}
    """

    if which.lower() not in ["cartesian", "polar"]:
        raise Exception(
            "Invalid coordinate type: must be either `polar` or `cartesian`"
        )

    tgrid, pgrid = np.meshgrid(thetas, phis)
    tflat, pflat = tgrid.flatten(), pgrid.flatten()

    if which.lower() == "cartesian":
        coordslist = [polar_to_cartesian(t, p) for t, p in zip(tflat, pflat)]
        coords = np.array(coordslist).T
    elif which.lower() == "polar":
        coords = np.array([tflat, pflat])

    return coords
