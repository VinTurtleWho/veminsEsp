"""
Declarative Field Schema & Generic Reader for MLBB Perception.
Allows dynamic field decoding, validation, and schema registry management.
"""

from dataclasses import dataclass, field
import json
import os
import struct
from typing import Any, Dict, List, Optional, Tuple, Union

from perception.memory_reader import MemoryReader

# Type format mappings for struct unpack
TYPE_FORMATS = {
    "uint8": ("<B", 1),
    "int8": ("<b", 1),
    "bool": ("<?", 1),
    "uint16": ("<H", 2),
    "int16": ("<h", 2),
    "uint32": ("<I", 4),
    "int32": ("<i", 4),
    "uint64": ("<Q", 8),
    "int64": ("<q", 8),
    "float": ("<f", 4),
    "double": ("<d", 8),
}


@dataclass(frozen=True)
class FieldDefinition:
    field_name: str
    offset: int
    data_type: str
    semantic: str
    confidence: str
    required: bool = False
    validation_rules: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldDefinition":
        offset_val = int(data["offset"], 16) if isinstance(data["offset"], str) else int(data["offset"])
        return cls(
            field_name=data["field"],
            offset=offset_val,
            data_type=data["type"],
            semantic=data.get("semantic", data["field"]),
            confidence=data.get("confidence", "UNPROVEN"),
            required=data.get("required", False),
            validation_rules=data.get("validation", {})
        )

    def decode_from_buffer(self, buffer: bytes) -> Tuple[bool, Any, str]:
        """Decodes the field value from a byte buffer."""
        if self.data_type not in TYPE_FORMATS:
            return False, None, f"Unsupported data type: {self.data_type}"

        fmt, size = TYPE_FORMATS[self.data_type]
        if len(buffer) < self.offset + size:
            return False, None, f"Buffer underflow (size={len(buffer)}, need={self.offset + size})"

        try:
            val = struct.unpack_from(fmt, buffer, self.offset)[0]
            if self.data_type == "uint8" and self.semantic.startswith("is_"):
                val = bool(val)

            # Apply validation rules if defined
            if "min" in self.validation_rules and val < self.validation_rules["min"]:
                return False, val, f"Value {val} below minimum {self.validation_rules['min']}"
            if "max" in self.validation_rules and val > self.validation_rules["max"]:
                return False, val, f"Value {val} above maximum {self.validation_rules['max']}"
            if "allowed" in self.validation_rules and val not in self.validation_rules["allowed"]:
                return False, val, f"Value {val} not in allowed set {self.validation_rules['allowed']}"

            return True, val, "OK"
        except Exception as e:
            return False, None, str(e)


@dataclass
class ClassSchema:
    class_name: str
    vtable_signature: int
    inheritance: List[str]
    fields: Dict[str, FieldDefinition]

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "ClassSchema":
        raw_vt = data.get("vtable_signature", 0)
        vtable = int(raw_vt, 16) if isinstance(raw_vt, str) else int(raw_vt)
        fields = {
            f["field"]: FieldDefinition.from_dict(f)
            for f in data.get("fields", [])
        }
        return cls(
            class_name=name,
            vtable_signature=vtable,
            inheritance=data.get("inheritance", []),
            fields=fields
        )


class FieldRegistry:
    """Registry that holds declarative field schemas for all game classes."""

    def __init__(self):
        self._classes: Dict[str, ClassSchema] = {}
        self._vtable_map: Dict[int, ClassSchema] = {}

    @classmethod
    def load_from_file(cls, path: Optional[str] = None) -> "FieldRegistry":
        registry = cls()
        if path is None:
            path = os.path.join(os.path.dirname(__file__), "field_schema.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            for cname, cdata in data.get("classes", {}).items():
                schema = ClassSchema.from_dict(cname, cdata)
                registry._classes[cname] = schema
                if schema.vtable_signature > 0:
                    registry._vtable_map[schema.vtable_signature] = schema
        return registry

    def get_by_name(self, name: str) -> Optional[ClassSchema]:
        return self._classes.get(name)

    def get_by_vtable(self, vtable: int) -> Optional[ClassSchema]:
        return self._vtable_map.get(vtable)

    def register_schema(self, schema: ClassSchema):
        self._classes[schema.class_name] = schema
        if schema.vtable_signature > 0:
            self._vtable_map[schema.vtable_signature] = schema

    def register_vtable(self, vtable: int, class_name: str) -> bool:
        """Dynamically registers a runtime ASLR-relocated vtable for a known class."""
        if vtable <= 0 or class_name not in self._classes:
            return False
        self._vtable_map[vtable] = self._classes[class_name]
        return True


class GenericFieldReader:
    """Generic reader that unpacks any entity dynamically using its schema."""

    def __init__(self, reader: MemoryReader, registry: Optional[FieldRegistry] = None):
        self.reader = reader
        self.registry = registry or FieldRegistry.load_from_file()

    def read_cstr(self, address: int, max_len: int = 64) -> str:
        """Reads a null-terminated ASCII/UTF-8 C-string from memory."""
        if address < 0x10000000 or address >= 0x8000000000:
            return ""
        raw = self.reader.read_bytes(address, max_len)
        if not raw:
            return ""
        null_idx = raw.find(b"\x00")
        if null_idx >= 0:
            raw = raw[:null_idx]
        return raw.decode("utf-8", errors="ignore")

    def resolve_il2cpp_descriptor(self, vtable_addr: int) -> Tuple[str, str]:
        """
        Reads Il2CppClass descriptor metadata at vtable_addr.
        Layout in 64-bit IL2CPP:
          vtable_addr + 0x10 -> const char* name
          vtable_addr + 0x18 -> const char* namespaze
        Returns (namespace, name) or ('', '') if unreadable/invalid.
        """
        if vtable_addr < 0x10000000 or vtable_addr >= 0x8000000000:
            return "", ""
        raw = self.reader.read_bytes(vtable_addr, 0x28)
        if len(raw) < 0x20:
            return "", ""
        p_name, p_ns = struct.unpack_from("<QQ", raw, 0x10)
        c_name = self.read_cstr(p_name)
        c_ns = self.read_cstr(p_ns)
        return c_ns, c_name

    def read_entity(
        self,
        address: int,
        confidence_policy: str = "PROVEN",
        buffer_size: int = 0x1000,
        expected_class: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if address <= 0:
            return None

        # Read object memory buffer
        raw = self.reader.read_bytes(address, buffer_size)
        if len(raw) < 8:
            return None

        # Resolve runtime VTable
        vtable = struct.unpack_from("<Q", raw, 0)[0]
        schema = self.registry.get_by_vtable(vtable)

        # Verified IL2CPP class descriptor identity resolution (ASLR relocation)
        if not schema and 0x10000000 <= vtable < 0x8000000000:
            c_ns, c_name = self.resolve_il2cpp_descriptor(vtable)
            if c_name:
                full_name = f"{c_ns}.{c_name}" if c_ns else c_name
                # Check expected_class match
                if expected_class and (expected_class == full_name or expected_class == c_name or expected_class.endswith(f".{c_name}")):
                    schema = self.registry.get_by_name(expected_class)
                # Otherwise search in registry classes
                if not schema:
                    schema = self.registry.get_by_name(full_name) or self.registry.get_by_name(c_name)
                # Register verified VTable
                if schema:
                    self.registry.register_vtable(vtable, schema.class_name)

        if not schema:
            return None

        result: Dict[str, Any] = {
            "address": address,
            "_class": schema.class_name,
            "_vtable": vtable
        }

        # Policy threshold ranking
        policy_rank = {"PROVEN": 3, "VALIDATED": 2, "SUPPORTED": 1, "UNPROVEN": 0}
        min_rank = policy_rank.get(confidence_policy, 3)

        for fname, fdef in schema.fields.items():
            f_rank = policy_rank.get(fdef.confidence, 0)
            if f_rank < min_rank:
                continue

            success, val, err = fdef.decode_from_buffer(raw)
            if success:
                result[fdef.semantic] = val
            elif fdef.required:
                # Required field failed validation -> invalid object
                return None

        return result
