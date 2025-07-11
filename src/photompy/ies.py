from dataclasses import dataclass, asdict
import pathlib
import warnings
import copy
from .photometry import Photometry
from .read import load_bytes, process_keywords, read_angles
from .write import process_row
from .exceptions import IESPathError, IESHeaderError  # , IESDecodeError,
from .ies_header import IESHeader, IESVersion


@dataclass
class IESFile:
    source: str | pathlib.Path | bytes
    header: IESHeader
    photometry: Photometry

    # attribute passthrough to header / photometry -------------
    def __getattr__(self, name):
        # called only if normal attribute lookup fails
        if hasattr(self.photometry, name):
            return getattr(self.photometry, name)
        if hasattr(self.header, name):
            return getattr(self.header, name)
        raise AttributeError(name)

    def __deepcopy__(self, memo):
        """
        Custom deepcopy to avoid the __getattr__ recursion issue.
        We duplicate header and photometry explicitly instead of
        letting copy traverse the whole object graph.
        """
        cls = self.__class__
        new_obj = cls.__new__(cls)
        memo[id(self)] = new_obj

        # shallow-copy simple attributes
        for k, v in self.__dict__.items():
            if k in ("header", "photometry"):
                # these may be big → real deepcopy
                setattr(new_obj, k, copy.deepcopy(v, memo))
            else:
                setattr(new_obj, k, v)

        return new_obj

    def to_dict(self):
        return asdict(self)

    @classmethod
    def read(cls, src, strict=True):
        """parse an ies file from any source"""
        raw, origin = load_bytes(src)
        if origin is not None:  # check filename
            cls._check_filename(origin=origin, strict=strict)

        string = raw.decode("utf-8")

        # TODO: tilt is currently in process_keywords, should be moved out separately
        version, header, tilt, numeric, blocks = cls._split_string(string)

        version = IESVersion.from_token(version, strict=strict)

        hdr = IESHeader.from_tokens(
            version=version,
            keywords=process_keywords(header),
            # tilt=tilt,
            numeric=numeric,
            strict=strict,
        )

        thetas, phis, values = read_angles(
            blocks, hdr.num_vert_angles, hdr.num_horiz_angles
        )
        phot = Photometry(
            thetas=thetas,
            phis=phis,
            values=values * hdr.multiplier,
            photometric_type=hdr.photometric_type,
        )

        hdr = hdr.update(multiplier=1)  # reset

        return cls(source=src, header=hdr, photometry=phot)

    @classmethod
    def from_photometry(cls, phot):
        return cls(source=None, header=IESHeader.from_photometry(phot), photometry=phot)

    def update(self, **changes):
        if "multiplier" in changes and changes["multiplier"] != 1:
            raise ValueError(
                "IESFile keeps multiplier fixed at 1. " "Use .scale(factor) instead."
            )
        self.header = self.header.update(**changes)
        return self

    def scale_to_max(self, max_val):
        """scale the photometry to a maximum value"""
        self.photometry.scale_to_max(max_val)
        return self

    def scale_to_total(self, total_power):
        """scale the photometry to a total optical power"""
        self.photometry.scale_to_total(total_power)
        return self

    def scale_to_center(self, center_val):
        """scale the photometry to a center value"""
        self.photometry.scale_to_center(center_val)
        return self

    def scale(self, scale_val):
        """scale the photometry by the given value"""
        self.photometry.scale(scale_val)
        return self

    def write(
        self,
        filename=None,
        which="orig",  # orig | full | interp
        interp_args=(181, 361),
        precision=2,
    ):
        """write the selected photometry to a file, or return as bytes"""

        photometry = self._get_photometry(which, interp_args)
        header = self.header.update(
            num_vert_angles=len(photometry.thetas),
            num_horiz_angles=len(photometry.phis),
        )
        # header
        iesdata = header.to_string()
        # thetas and phis
        iesdata += process_row(photometry.thetas)
        iesdata += process_row(photometry.phis)

        # candela values
        candelas = ""
        for row in photometry.values:
            candelas += process_row(row, sigfigs=precision)
        iesdata += candelas

        # write
        if filename is not None:
            with open(filename, "w", encoding="utf-8") as newfile:
                newfile.write(iesdata)
        else:
            return iesdata.encode("utf-8")

    def plot(
        self,
        plot_type="polar",  # polar | cartesian
        which="full",  # orig | full | interp
        interp_args=(181, 361),  # (num_thetas, num_phis)
        **kwargs,
    ):
        """return a polar or 3d cartesian plot of the photometry"""
        photometry = self._get_photometry(which, interp_args)
        if plot_type.lower() == "polar":
            return photometry.plot_polar(**kwargs)
        elif plot_type.lower() == "cartesian":
            return photometry.plot_cartesian(**kwargs)
        else:
            raise ValueError(f"unrecognized plot type {plot_type}")

    # ---------------- Internals -----------------------
    def _get_photometry(self, which, interp_args=(181, 361)):
        if which.lower() == "orig":
            return self.photometry
        elif which.lower() == "full":
            return self.photometry.expanded()
        elif which.lower() == "interp":
            return self.photometry.interpolated(*interp_args)
        raise ValueError(f"Unknown photometry mode {which}", stacklevel=3)

    @staticmethod
    def _check_filename(origin, strict=True):
        if origin.suffix.lower() != ".ies":
            msg = f"Unexpected extension {origin.suffix!s}. Expected .ies"
            if strict:
                raise IESPathError(msg)
            else:
                warnings.warn(msg, stacklevel=3)

    @staticmethod
    def _split_string(string):
        """TODO: tilt handling"""
        lines = string.split("\n")
        lines = [line.strip() for line in lines]
        version = lines[0]
        header = []
        tilt = None
        for i, line in enumerate(lines):
            header.append(line)
            if line.startswith("TILT="):
                if line == "TILT=INCLUDE":
                    tilt = lines[i : i + 5]
                    i = i + 5
                else:
                    tilt = line
                    i = i + 1
                break
        if tilt is None:
            raise IESHeaderError("File is malformed; TILT= line missing")
        data = " ".join(lines[i:]).split()
        numeric = data[0:13]
        blocks = data[13:]
        return version, header, tilt, numeric, blocks
