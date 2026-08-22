import os
import sys
import json
import struct

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from perception.memory_reader import DaemonMemoryReader

def read_string(reader, addr):
    if addr == 0 or addr < 0x10000000:
        return ""
    try:
        length_bytes = reader.read_bytes(addr + 0x10, 4)
        if not length_bytes:
            return ""
        length = int.from_bytes(length_bytes, 'little')
        if length <= 0 or length > 1000:
            return ""
        chars = reader.read_bytes(addr + 0x14, length * 2)
        return chars.decode('utf-16le', errors='ignore')
    except Exception:
        return ""

def read_array(reader, addr, element_type):
    if addr == 0 or addr < 0x10000000:
        return []
    try:
        # In IL2CPP 64-bit, length is at +0x18
        len_bytes = reader.read_bytes(addr + 0x18, 4)
        if not len_bytes:
            return []
        length = int.from_bytes(len_bytes, 'little')
        if length <= 0 or length > 1000:
            return []

        data_start = addr + 0x20
        results = []

        if element_type == "int":
            raw = reader.read_bytes(data_start, length * 4)
            for i in range(length):
                chunk = raw[i*4 : (i+1)*4]
                results.append(int.from_bytes(chunk, 'little', signed=True))
        elif element_type == "float":
            raw = reader.read_bytes(data_start, length * 4)
            for i in range(length):
                chunk = raw[i*4 : (i+1)*4]
                results.append(struct.unpack('f', chunk)[0])
        elif element_type == "string":
            raw = reader.read_bytes(data_start, length * 8)
            for i in range(length):
                ptr_val = int.from_bytes(raw[i*8 : (i+1)*8], 'little')
                results.append(read_string(reader, ptr_val))
        elif element_type == "int[]":
            # Jagged array int[][]
            raw = reader.read_bytes(data_start, length * 8)
            for i in range(length):
                sub_arr_ptr = int.from_bytes(raw[i*8 : (i+1)*8], 'little')
                results.append(read_array(reader, sub_arr_ptr, "int"))
        else:
            return f"UNHANDLED_ARRAY_TYPE_{element_type}"

        return results
    except Exception as e:
        return []

def read_cdata_struct(reader, ptr_val, schema):
    raw_data = {}
    for field_name, field_info in schema["fields"].items():
        offset = field_info["offset"]
        ftype = field_info["type"]
        
        try:
            if ftype == "int" or ftype == "uint" or ftype.endswith("Enum"):
                val_bytes = reader.read_bytes(ptr_val + offset, 4)
                raw_data[field_name] = int.from_bytes(val_bytes, 'little', signed=(ftype=="int")) if val_bytes else 0
            elif ftype == "long" or ftype == "ulong":
                val_bytes = reader.read_bytes(ptr_val + offset, 8)
                raw_data[field_name] = int.from_bytes(val_bytes, 'little', signed=(ftype=="long")) if val_bytes else 0
            elif ftype == "float":
                val_bytes = reader.read_bytes(ptr_val + offset, 4)
                raw_data[field_name] = struct.unpack('f', val_bytes)[0] if val_bytes else 0.0
            elif ftype == "double":
                val_bytes = reader.read_bytes(ptr_val + offset, 8)
                raw_data[field_name] = struct.unpack('d', val_bytes)[0] if val_bytes else 0.0
            elif ftype == "string":
                str_ptr_bytes = reader.read_bytes(ptr_val + offset, 8)
                str_ptr = int.from_bytes(str_ptr_bytes, 'little') if str_ptr_bytes else 0
                raw_data[field_name] = read_string(reader, str_ptr)
            elif ftype == "bool":
                val_bytes = reader.read_bytes(ptr_val + offset, 1)
                raw_data[field_name] = bool(val_bytes[0]) if val_bytes else False
            elif ftype == "int[]" or ftype == "uint[]":
                arr_ptr = int.from_bytes(reader.read_bytes(ptr_val + offset, 8), 'little')
                raw_data[field_name] = read_array(reader, arr_ptr, "int")
            elif ftype == "float[]":
                arr_ptr = int.from_bytes(reader.read_bytes(ptr_val + offset, 8), 'little')
                raw_data[field_name] = read_array(reader, arr_ptr, "float")
            elif ftype == "string[]":
                arr_ptr = int.from_bytes(reader.read_bytes(ptr_val + offset, 8), 'little')
                raw_data[field_name] = read_array(reader, arr_ptr, "string")
            elif ftype == "int[][]":
                arr_ptr = int.from_bytes(reader.read_bytes(ptr_val + offset, 8), 'little')
                raw_data[field_name] = read_array(reader, arr_ptr, "int[]")
            else:
                raw_data[field_name] = f"TYPE_{ftype}"
        except Exception as e:
            raw_data[field_name] = None

    return raw_data

def dump_live_hero_full():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.normpath(os.path.join(current_dir, "../../knowledge/schemas/CData_Hero_Element.json"))
    out_path = os.path.normpath(os.path.join(current_dir, "../../knowledge/raw/heroes.json"))

    with open(schema_path, "r") as f:
        schema = json.load(f)

    reader = DaemonMemoryReader(host="127.0.0.1", port=9999)
    if not reader.connect():
        print("Error: Could not connect to daemon")
        return

    hero_info = reader.scan_hero()
    if hero_info.get("status") != "ok" or not hero_info.get("hero_ptr"):
        print("No live hero found")
        return

    hero_ptr = int(hero_info["hero_ptr"], 16)
    config_ptr = int.from_bytes(reader.read_bytes(hero_ptr + 0xc78, 8), 'little')
    print(f"Reading CData_Hero_Element at {hex(config_ptr)}")

    raw_record = read_cdata_struct(reader, config_ptr, schema)
    
    all_heroes = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, "r") as f:
                all_heroes = json.load(f)
        except:
            pass

    hero_id = str(raw_record.get("m_ID", "unknown"))
    all_heroes[hero_id] = raw_record

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_heroes, f, indent=4)

    print(f"Dumped Hero {hero_id} ({raw_record.get('m_mName')}) with full array dereferencing!")
    print(f"SkillList: {raw_record.get('m_SkillList')}")
    print(f"CostType: {raw_record.get('m_CostType')}")
    print(f"RecommendEquip: {raw_record.get('m_RecommendEquip')}")

if __name__ == "__main__":
    dump_live_hero_full()
