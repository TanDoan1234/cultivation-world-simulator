import os
import glob
import subprocess

def compile_po_to_mo(lang_code):
    base_dir = os.path.join("static", "locales", lang_code)
    lc_messages_dir = os.path.join(base_dir, "LC_MESSAGES")
    
    # Đảm bảo thư mục tồn tại
    os.makedirs(lc_messages_dir, exist_ok=True)
    
    # 1. Gom các file trong game_configs_modules -> game_configs.po
    game_configs_po = os.path.join(lc_messages_dir, "game_configs.po")
    game_configs_mo = os.path.join(lc_messages_dir, "game_configs.mo")
    
    with open(game_configs_po, "w", encoding="utf-8") as outfile:
        # Ghi header tĩnh
        outfile.write('#\nmsgid ""\nmsgstr ""\n"Project-Id-Version: cultivation-world-simulator 1.0\\n"\n"Report-Msgid-Bugs-To: \\n"\n"POT-Creation-Date: 2024-01-20 00:00+0000\\n"\n"PO-Revision-Date: 2024-01-20 00:00+0000\\n"\n"Last-Translator: \\n"\n"Language-Team: English\\n"\n"Language: vi_VN\\n"\n"MIME-Version: 1.0\\n"\n"Content-Type: text/plain; charset=UTF-8\\n"\n"Content-Transfer-Encoding: 8bit\\n"\n\n')
        
        for f_path in glob.glob(os.path.join(base_dir, "game_configs_modules", "*.po")):
            with open(f_path, "r", encoding="utf-8") as infile:
                content = infile.read()
                # Bỏ qua phần header của các file con để tránh lỗi Duplicate
                parts = content.split('\n\n', 1)
                if len(parts) > 1:
                    outfile.write(parts[1] + "\n\n")
                else:
                    outfile.write(content + "\n\n")
                    
    print(f"Bắt đầu biên dịch {game_configs_po} -> {game_configs_mo}")
    subprocess.run(["python", "scripts/msgfmt.py", "-o", game_configs_mo, game_configs_po], check=True)
    
    # 2. Gom các file trong modules -> messages.po
    messages_po = os.path.join(lc_messages_dir, "messages.po")
    messages_mo = os.path.join(lc_messages_dir, "messages.mo")
    
    with open(messages_po, "w", encoding="utf-8") as outfile:
        # Ghi header tĩnh
        outfile.write('#\nmsgid ""\nmsgstr ""\n"Project-Id-Version: cultivation-world-simulator 1.0\\n"\n"Report-Msgid-Bugs-To: \\n"\n"POT-Creation-Date: 2024-01-20 00:00+0000\\n"\n"PO-Revision-Date: 2024-01-20 00:00+0000\\n"\n"Last-Translator: \\n"\n"Language-Team: English\\n"\n"Language: vi_VN\\n"\n"MIME-Version: 1.0\\n"\n"Content-Type: text/plain; charset=UTF-8\\n"\n"Content-Transfer-Encoding: 8bit\\n"\n\n')
        
        for f_path in glob.glob(os.path.join(base_dir, "modules", "*.po")):
            with open(f_path, "r", encoding="utf-8") as infile:
                content = infile.read()
                parts = content.split('\n\n', 1)
                if len(parts) > 1:
                    outfile.write(parts[1] + "\n\n")
                else:
                    outfile.write(content + "\n\n")
                    
    print(f"Bắt đầu biên dịch {messages_po} -> {messages_mo}")
    subprocess.run(["python", "scripts/msgfmt.py", "-o", messages_mo, messages_po], check=True)
    
    print("Hoàn tất quy trình Build PO/MO!")

if __name__ == "__main__":
    compile_po_to_mo("vi-VN")
