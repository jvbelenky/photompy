import photompy.ies as ies

def test_numeric_round_trip(load_ies, tmp_path):
    """Read → write → read again and compare numeric header row."""
    original = load_ies("sample_A.ies")
    tmp_file = tmp_path / "out.ies"
    original.write(tmp_file)            # exercise the writer
    reread = ies.IESFile.read(tmp_file)

    # Row-11 numeric fields should be identical after a full cycle.
    assert original.header.num_lamps == reread.header.num_lamps
    assert original.header.num_vert_angles == reread.header.num_vert_angles
    assert original.header.units == reread.header.units
