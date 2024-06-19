PhotomPy: Photometric Python
===========================
A library for reading, writing, and viewing photometric files.

<!-- Installation -->
## Installation

Install with pip:

	pip install photompy

Alternatively, clone the repo and build locally:

	git clone https://github.com/jvbelenky/photompy.git
    cd photompy
    python setup.py sdist
    pip install .


<!-- USAGE EXAMPLES -->
## Usage

### Read files

Most of the core functionality of the library is in `read_ies_data` :


	from photompy import *
	lampdict = read_ies_data(filename)
	

By default, an ies file will be read in its original form, the angle values formatted in accordance with its photometry type, and interpolated to achieve a value for vertical angles (0,180) and horizontal angles (0,360). They are stored in dictionaries with keys `phis`,`thetas`, and `values`. They can be accessed like so:

	original_dict = lampdict["original_vals"]
	full_dict = lampdict["full_vals"]
	interp_dict = lampdict["interp_vals"]

Extending the angles and interpolation between them can be disabled if desired:

	lampdict = read_ies_data(filename, extend=False, interpolate=False)
	
### Simple calculations

If finer interpolation is desired, the `interp_vals` dictionary can be overwritten:
	
	interpolate_values(lampdict, overwrite=True, num_thetas=361, num_phis=721)
	finer_interp_dict = lampdict["interp_vals"]

Simple calculations are performed at the filename level:

	power = total_optical_power(filename)
	luminous_area = lamp_area(filename, units="meters")

### Visualization

Some plotting functions are provided for quickly visualizing a file. The default is a standard polar plot:

	plot_ies(filename)
	
An alternative cartesian plotting function is provided and maybe be useful for those less familiar with polar plots to quickly gut-check any changes made to a file:

	plot_ies(filename, type="cartesian", "original")
	plot_ies(filename, type="cartesian", "full", elev=90, azim=45)
	plot_ies(filename, type="cartesian", "interpolated", title="Interpolated", show_cbar=True)


Any dictionary that has keys `thetas`, `phis`, and `values`, where `values` contains a numpy array of shape `( len(phis), len(thetas) )` can also be quickly plotted with `plot_valdict_cartesian` or `plot_valdict_polar` 

	full_dict = lampdict["full_vals"]
	new_dict = full_dict.copy()
	new_dict["values"] = full_dict["values"] * 5
	fig, ax = plot_valdict_cartesian(new_dict)
	fig, ax = plot_valdict_polar(new_dict)

### Writing files

To write a new ies file, you must pass a `lampdict` object and a key pointing to the dictionary where the theta, phi, and candela values are stored. You may want to save the extended or interpolated versions of the original file:

    lampdict = read_ies_data(filename)
    outfile = "full_vals.ies"
    write_ies_data(outfile, lampdict, valkey="full_vals")
    outfile = "interp_vals.ies"
    write_ies_data(outfile, lampdict, valkey="interp_vals")

If you wish to save a different array of candela values, you can either manipulate the 3 provided value dictionary, or you must create a new dictionary and add it to the `lampdict` object before writing it to a new file.

    # read 
    lampdict = read_ies_data(filename)
    interp_dict = lampdict["interp_vals"]
    
    # copy and manipulate new dictionary
    new_dict = interp_dict.copy()
    new_dict["values"] = interp_dict["values"] * 5
    
    # save in lampdict object
    lampdict["scaled_vals"] = newdict
    
    # write new value dictionary 
    outfile = "scaled_interp_vals.ies"
    write_ies_data(outfile, lampdict, valkey="scaled_vals")

Note that header data is _not_ automatically updated in the latter case. Verify that all information is correct before writing.

<!-- ROADMAP -->
## Roadmap

- [ ] PhotometricData and AngleData objects (as opposed to lampdict and valdict dictionaries)
- [ ] Generate .ies files from an angular distribution table
- [ ] Type A and B photometry support
- [ ] Dialux file (.ldt) support
- [ ] More extensive write support


<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<!-- CONTACT -->
## Contact

Vivian Belenky - jvb@osluv.org
