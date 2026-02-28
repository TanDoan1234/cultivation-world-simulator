import os
import glob
import re
import time
import json
from google import genai

def get_api_key():
    return "AIzaSyCjVk6pkt24aKAhDHuyJGxVrjhtGZ-sY3I"

client = None

def parse_po_content(content):
    blocks = content.split('\n\n')
    parsed_blocks = []
    
    for b in blocks:
        if not b.strip(): continue
        
        lines = b.split('\n')
        msgid_raw = []
        msgstr_raw = []
        msgid = ""
        msgstr = ""
        current_field = None
        header_lines = []
        
        if b.startswith('msgid ""'):
            parsed_blocks.append({"type": "header", "raw": b})
            continue

        for line in lines:
            if line.startswith('msgid "'):
                msgid = line[7:-1]
                msgid_raw.append(line)
                current_field = 'msgid'
            elif line.startswith('msgstr "'):
                msgstr = line[8:-1]
                msgstr_raw.append(line)
                current_field = 'msgstr'
            elif line.startswith('"') and current_field:
                if current_field == 'msgid':
                    msgid += line[1:-1]
                    msgid_raw.append(line)
                else:
                    msgstr += line[1:-1]
                    msgstr_raw.append(line)
            else:
                header_lines.append(line)
        
        parsed_blocks.append({
            "type": "entry",
            "header": header_lines,
            "msgid": msgid,
            "msgstr": msgstr,
            "msgid_raw": msgid_raw,
            "msgstr_raw": msgstr_raw
        })
    return parsed_blocks

def reconstruct_block(block):
    if block["type"] == "header":
        return block["raw"]
    
    lines = []
    if block["header"]:
        lines.extend(block["header"])
    
    lines.extend(block["msgid_raw"])
    
    # Reconstruct msgstr to handle potential long translation
    # For simplicity, we can put it in one msgstr "" followed by lines, 
    # but let's just do one msgstr "..." if it's not too long, or break it.
    new_msgstr = block.get("translated_msgstr", block["msgstr"])
    
    # Standard PO format for multi-line
    # We'll just put it in a single long msgstr "..." for now as it's easier to write
    # and gettext handles it fine.
    lines.append(f'msgstr "{new_msgstr}"')
    
    return "\n".join(lines)

def translate_batch(texts):
    if not texts: return []
    
    prompt = f"""Dịch các mảng câu tiếng Anh sau sang Tiếng Việt phong cách Tiên Hiệp/Tu Tiên Cổ Trang.
Quy định:
- Dịch sát nghĩa, giữ nguyên các biến như {{name}}, {{avatar}} hoặc các thẻ định dạng.
- Trả về bắt buộc là mảng JSON, chuỗi mảng độ dài BẰNG ĐÚNG INPUT, KHÔNG THÊM BẤT CỨ VĂN BẢN NÀO KHÁC BÊN NGOÀI.

Input:
{json.dumps(texts, ensure_ascii=False)}
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        res_text = response.text
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].strip()
            
        print("Raw Output:", res_text[:100], "...")
        translated = json.loads(res_text)
        return translated
    except Exception as e:
        print(f"Lỗi khi dịch: {e}")
        return texts

def process_po_file(filepath):
    print(f"Đang xử lý {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    en_filepath = filepath.replace("vi-VN", "en-US")
    en_dict = {}
    if os.path.exists(en_filepath):
        with open(en_filepath, "r", encoding="utf-8") as f:
            en_blocks = parse_po_content(f.read())
            en_dict = {b["msgid"]: b["msgstr"] for b in en_blocks if b["type"] == "entry"}
            
    blocks = parse_po_content(content)
    
    to_translate = []
    indices = []
    
    for i, b in enumerate(blocks):
        if b["type"] != "entry": continue
        
        msgid = b["msgid"]
        msgstr = b["msgstr"]
        en_msgstr = en_dict.get(msgid)
        
        needs_definitely = False
        if not msgstr or msgstr == msgid or (en_msgstr and msgstr == en_msgstr):
            if re.search(r'[a-zA-Z]', msgid):
                needs_definitely = True
        elif en_msgstr and en_msgstr in msgstr and len(msgstr) > len(en_msgstr) / 2:
            # Check for partial translation from previous bug
            needs_definitely = True
            
        if needs_definitely:
            # Use original English msgstr as source for long descriptions
            source = en_msgstr if en_msgstr else msgid
            to_translate.append(source)
            indices.append(i)
            
    if not to_translate:
        print("-> Đã dịch hết.")
        return False
        
    print(f"-> Cần dịch {len(to_translate)} câu...")
    batch_size = 10
    for i in range(0, len(to_translate), batch_size):
        batch = to_translate[i:i+batch_size]
        results = translate_batch(batch)
        for j, res in enumerate(results):
            if j < len(batch):
                idx = indices[i+j]
                blocks[idx]["translated_msgstr"] = res
        time.sleep(1)
        
    new_content = "\n\n".join([reconstruct_block(b) for b in blocks])
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"-> Đã dịch và lưu {len(to_translate)} item.")
    return True

if __name__ == "__main__":
    api_key = get_api_key()
    client = genai.Client(api_key=api_key)
    po_files = glob.glob('static/locales/vi-VN/game_configs_modules/*.po') + glob.glob('static/locales/vi-VN/modules/*.po')
    for f in po_files:
        process_po_file(f)
