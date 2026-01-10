from mht_parser.structure_parser import parse_mht_to_structure

if __name__ == "__main__":
    parts = parse_mht_to_structure(
        "大宽基地成就馆升级.mht",
        dump_dir="结构目录_大宽基地成就馆升级",
    )
    print("parts:", len(parts))
    print("first part:", parts[0])