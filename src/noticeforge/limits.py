from dataclasses import dataclass, fields
from .errors import InputError


@dataclass(frozen=True)
class Limits:
    max_input_bytes: int = 2_097_152
    max_components: int = 256
    max_edges: int = 4096
    max_archive_bytes: int = 67_108_864
    max_zip_members: int = 10_000
    max_uncompressed_bytes: int = 134_217_728
    max_member_bytes: int = 8_388_608
    max_material_bytes: int = 33_554_432
    max_output_bytes: int = 41_943_040

    def validate(self):
        caps = {
            "max_input_bytes": 8_388_608, "max_components": 1000,
            "max_edges": 10_000, "max_archive_bytes": 268_435_456,
            "max_zip_members": 20_000, "max_uncompressed_bytes": 536_870_912,
            "max_member_bytes": 33_554_432, "max_material_bytes": 134_217_728,
            "max_output_bytes": 167_772_160,
        }
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or not 1 <= value <= caps[field.name]:
                raise InputError(f"{field.name} must be an integer in 1..{caps[field.name]}")
        return self
