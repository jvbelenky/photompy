from ._read import verify_valdict


def _process_row(row, sigfigs=2):
    total = 0
    newstring = ""
    for i, number in enumerate(row):
        if total > 76:
            newstring += "\n"
            total = 0
        numberstring = str(round(number, sigfigs))
        newstring += numberstring
        total += len(numberstring)
        if i != len(row) - 1:
            # don't add extra characters if it's the end of the file
            if total > 76:
                newstring += "\n"
                total = 0
            newstring += " "
            total += 1
    if newstring[-4:] != "\n":
        newstring += "\n"
    return newstring



def write_ies_data(filename, lampdict, valkey="original_vals"):
    """
    write a lampdict object to an .ies file

    filename: file to write to
    lampdict: dictionary object containing all ies file data
    valkey: key in lampdict that points to the dictionary where the phis,
        thetas, and values are stored. May be `original_vals`, `full_vals`,
        or another user-defined dictionary, so long as it is stored in the
        lampdict object. Valdict must have keys `thetas`, `phis`, and `values`
        If `full_vals` or `interp_vals` is chosen, the `multiplier` value in 
        lampdict will be recorded as 1.
    """

    valdict = lampdict[valkey]

    # check that the valdict is in order
    verify_valdict(valdict)

    if valkey in ["full_vals","interp_vals"]:
        # the full_vals dictionary takes into account the multiplier, so if
        # they are being written, the multiplier should be set to 1, regardless
        # of what it was with respect to the original_vals dictionary
        lampdict["multiplier"] = 1

    thetas = valdict["thetas"]
    phis = valdict["phis"]
    values = valdict["values"]

    lampdict["num_vertical_angles"] = len(thetas)
    lampdict["num_horizontal_angles"] = len(phis)

    # begin building string
    iesdata = lampdict["version"] + "\n"
    # header
    for key, val in lampdict["keywords"].items():
        if key != "TILT":
            iesdata += "[" + key + "] " + val + "\n"
        else:
            iesdata += key + "=" + val + "\n"

    row1 = list(lampdict.values())[3:13]
    row2 = list(lampdict.values())[13:16]
    iesdata += " ".join([str(val) for val in row1]) + "\n"
    iesdata += " ".join([str(val) for val in row2]) + "\n"
    # thetas and phis
    iesdata += _process_row(thetas)
    iesdata += _process_row(phis)
    # candela values
    candelas = ""
    for row in values:
        candelas += _process_row(row, sigfigs=2)
    iesdata += candelas

    # write
    with open(filename, "w", encoding='utf-8') as newfile:
        newfile.write(iesdata)


# def write_ies_data(filename, lampdict, valkey="original_vals"):
    # """
    # write a lampdict object to an .ies file

    # filename: file to write to
    # lampdict: dictionary object containing all ies file data
    # valkey: key in lampdict that points to the dictionary where the phis,
        # thetas, and values are stored. May be `original_vals`, `full_vals`,
        # or another user-defined dictionary, so long as it is stored in the
        # lampdict object. Valdict must have keys `thetas`, `phis`, and `values`
        # If `full_vals` is chosen, the `multiplier` value in lampdict will
        # be recorded as 1.
    # """

    # valdict = lampdict[valkey]

    # # check that the valdict is in order
    # verify_valdict(valdict)

    # if valkey in ["full_vals","interp_vals"]:
        # # the full_vals dictionary takes into account the multiplier, so if
        # # they are being written, the multiplier should be set to 1, regardless
        # # of what it was with respect to the original_vals dictionary
        # lampdict["multiplier"] = 1

    # thetas = valdict["thetas"]
    # phis = valdict["phis"]
    # values = valdict["values"]

    # lampdict["num_vertical_angles"] = len(thetas)
    # lampdict["num_horizontal_angles"] = len(phis)

    # # begin building string
    # iesdata = lampdict["version"] + "\n"
    # # header
    # for key, val in lampdict["keywords"].items():
        # if key != "TILT":
            # iesdata += "[" + key + "] " + val + "\n"
        # else:
            # iesdata += key + "=" + val + "\n"

    # row1 = list(lampdict.values())[3:13]
    # row2 = list(lampdict.values())[13:16]
    # iesdata += " ".join([str(val) for val in row1]) + "\n"
    # iesdata += " ".join([str(val) for val in row2]) + "\n"
    # # thetas and phis
    # iesdata += _process_row(thetas)
    # iesdata += _process_row(phis)
    # # candela values
    # candelas = ""
    # for row in values:
        # candelas += _process_row(row, sigfigs=2)
    # iesdata += candelas

    # # write
    # with open(filename, "w", encoding='utf-8') as newfile:
        # newfile.write(iesdata)
