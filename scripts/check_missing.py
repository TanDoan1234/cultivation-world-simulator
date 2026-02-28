import os
import glob
import re

def parse_po_content(content):
    blocks = content.split('\n\n')
    parsed_blocks = []
    
    for b in blocks:
        if not b.strip():
            continue
        
        lines = b.split('\n')
        msgid = ""
        msgstr = ""
        current_field = None
        header_lines = []
        
        is_header = b.startswith('msgid ""')
        
        if is_header:
            parsed_blocks.append({"type": "header", "raw": b})
            continue

        for line in lines:
            if line.startswith('msgid "'):
                msgid = line[7:-1]
                current_field = 'msgid'
            elif line.startswith('msgstr "'):
                msgstr = line[8:-1]
                current_field = 'msgstr'
            elif line.startswith('"') and current_field:
                if current_field == 'msgid':
                    msgid += line[1:-1]
                else:
                    msgstr += line[1:-1]
            elif not line.startswith('msgid') and not line.startswith('msgstr') and not line.startswith('"'):
                header_lines.append(line)
        
        parsed_blocks.append({
            "type": "entry",
            "header": "\n".join(header_lines),
            "msgid": msgid,
            "msgstr": msgstr,
            "raw": b
        })
    return parsed_blocks

def check_missing_by_comparing_en(lang_code):
    base_dir = os.path.join("static", "locales", lang_code)
    en_base_dir = os.path.join("static", "locales", "en-US")
    
    po_files = glob.glob(os.path.join(base_dir, "modules", "*.po")) + glob.glob(os.path.join(base_dir, "game_configs_modules", "*.po"))
    
    total_missing = 0
    missing_details = []
    
    for fpath in po_files:
        en_fpath = fpath.replace(lang_code, "en-US")
        if not os.path.exists(en_fpath): continue
            
        with open(fpath, "r", encoding="utf-8") as f:
            blocks = parse_po_content(f.read())
        with open(en_fpath, "r", encoding="utf-8") as f:
            en_blocks = parse_po_content(f.read())
            
        en_dict = {b["msgid"]: b["msgstr"] for b in en_blocks if b["type"] == "entry"}
                
        file_missing = 0
        missing_preview = []
        
        for b in blocks:
            if b["type"] != "entry": continue
            
            msgid = b["msgid"]
            msgstr = b["msgstr"]
            en_msgstr = en_dict.get(msgid)
            
            # Detect English in msgstr
            has_english = re.search(r'[a-zA-Z]{4,}', msgstr) # ít nhất 4 chữ cái liên tiếp thường là tiếng Anh
            
            # Cần dịch nếu: rỗng, trùng msgid, trùng en_msgstr, HOẶC vẫn còn chứa nhiều tiếng Anh
            needs_translation = False
            if not msgstr or msgstr == msgid or (en_msgstr and msgstr == en_msgstr):
                if re.search(r'[a-zA-Z]', msgid):
                    needs_translation = True
            elif en_msgstr and en_msgstr in msgstr and len(msgstr) > len(en_msgstr) / 2:
                # Nếu chuỗi tiếng Anh vẫn còn nằm trong chuỗi hiện tại (do bug append lần trước)
                needs_translation = True
            
            if needs_translation:
                file_missing += 1
                total_missing += 1
                preview = msgid[:40] + "..." if len(msgid) > 40 else msgid
                missing_preview.append(preview)
        
        if file_missing > 0:
            missing_details.append(f"{fpath}: Thiếu {file_missing} câu.\n    VD: {', '.join(missing_preview[:3])}")
            
    print(f"Tổng cộng có {total_missing} câu chưa được dịch hoàn toàn.\n")
    for detail in missing_details:
        print(detail)

if __name__ == "__main__":
    check_missing_by_comparing_en("vi-VN")
