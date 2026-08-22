import re
import json
import os

DUMP_FILE = "../../dump/com.mobile.legends_64bit.cs"
OUTPUT_DIR = "../../knowledge/schemas"

TARGET_CLASSES = [
    "CData_Hero_Element",
    "CData_Skill_Element",
    "CData_SkillType_Element",
    "CData_Effect_Element",
    "CData_EquipBase_Element",
    "CData_Monster_Element",
    "CData_MonsterAttribute_Element",
    "CData_Formula_Element",
    "CData_Emblem_2023_Element",
    "CData_EmblemGift_2023_Element",
    "CData_Bullet_Element",
    "CData_HeroLevelUpgradeAttr_Element"
]

def parse_all_schemas():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dump_path = os.path.normpath(os.path.join(current_dir, DUMP_FILE))
    out_dir = os.path.normpath(os.path.join(current_dir, OUTPUT_DIR))

    if not os.path.exists(dump_path):
        print(f"Error: Dump file {dump_path} not found.")
        return

    os.makedirs(out_dir, exist_ok=True)
    field_re = re.compile(r"^\s*public\s+([\w\[\]`]+)\s+([\w_]+);\s*//\s*(0x[0-9a-f]+)")

    for target_class in TARGET_CLASSES:
        schema = {
            "class_name": target_class,
            "fields": {}
        }

        class_start_re = re.compile(rf"public class {target_class}\b")
        in_class = False

        with open(dump_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not in_class:
                    if class_start_re.search(line):
                        in_class = True
                else:
                    if "{" in line and not "}" in line:
                        continue
                    if "}" in line and not "{" in line:
                        if line.strip() == "}":
                            break
                    if "// Properties" in line or "// Methods" in line:
                        break

                    match = field_re.search(line)
                    if match:
                        field_type = match.group(1)
                        field_name = match.group(2)
                        offset_hex = match.group(3)
                        
                        schema["fields"][field_name] = {
                            "type": field_type,
                            "offset": int(offset_hex, 16)
                        }

        out_path = os.path.join(out_dir, f"{target_class}.json")
        with open(out_path, "w") as f:
            json.dump(schema, f, indent=4)
        print(f"Extracted {len(schema['fields']):>3} fields for {target_class:<35} -> {out_path}")

if __name__ == "__main__":
    parse_all_schemas()
