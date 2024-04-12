def write_ies_data(lampdict,filename):
    """
    write a lampdict object to an .ies file
    """
    # header
    iesdata = ''
    header = '\r\n'.join(lampdict['Header'])+'\r\n'
    row1 = list(lampdict.values())[3:13]
    row2 = list(lampdict.values())[13:16]
    header += " ".join([str(val) for val in row1])+'\r\n'
    header += " ".join([str(val) for val in row2])+'\r\n'
    iesdata += header
    # thetas and phis
    iesdata += _process_row(lampdict['original_vals']['thetas'])
    iesdata += _process_row(lampdict['original_vals']['phis'])
    # candela values
    candelas = ''
    values = lampdict['original_vals']['values']
    for row in values:
        candelas += _process_row(row,sigfigs=2)
    iesdata += candelas

    #write
    with open(filename, "w") as newfile:
        newfile.write(iesdata)
        
        
def _process_row(row,sigfigs=2):
    total = 0
    newstring = ''
    for i,number in enumerate(row):
        if total>76:
            newstring += '\r\n'
            total = 0
        numberstring = str(round(number,sigfigs))
        newstring += numberstring
        total += len(numberstring)
        if i!=len(row)-1: 
        # don't add extra characters if it's the end of the file
            if total>76:
                newstring += '\r\n'
                total = 0
            newstring += ' '
            total += 1
    if newstring[-4:] != '\r\n':
        newstring += '\r\n'
    return newstring