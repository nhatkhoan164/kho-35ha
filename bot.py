
import os
import json
import gspread
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
import threading
from flask import Flask

# --- Web giả cho Render ---
app_web = Flask(__name__)
@app_web.route('/')
def home():
    return "Bot đang chạy!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port, use_reloader=False)

threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.environ.get("TOKEN")
SHEET_ID = os.environ.get("SHEET_ID")
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
gc = gspread.service_account_from_dict(creds_dict)
sh = gc.open_by_key(SHEET_ID)

MAP_KHO = {"TA":"Kho_TA","VT":"Kho_VT","TY":"Kho_TY","MM":"Kho_MM","U":"Kho_U","NL":"Kho_NL"}

# --- BƯỚC 3: KHÓA BOT - CHỈ NGƯỜI CÓ ID MỚI XÀI ĐƯỢC ---
# Lấy từ Environment trên Render: ALLOWED_IDS = 123456789,987654321
ALLOWED_IDS = os.environ.get("ALLOWED_IDS", "")
ALLOWED_SET = set(x.strip() for x in ALLOWED_IDS.split(",") if x.strip())

async def check_quyen(update: Update):
    user_id = str(update.effective_user.id)
    # Nếu chưa cài ALLOWED_IDS thì cho tất cả xài (để test lần đầu)
    # Nếu đã cài rồi mà không có trong danh sách thì chặn
    if ALLOWED_SET and user_id not in ALLOWED_SET:
        await update.message.reply_text(f"⛔ Bạn không có quyền dùng bot này!\nID của bạn là: {user_id}\nGửi ID này cho quản lý để được cấp quyền.")
        return False
    return True

def get_col_index(ws, ten_cot):
    headers = ws.row_values(1)
    for idx, h in enumerate(headers, start=1):
        if h.strip().lower() == ten_cot.lower():
            return idx
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_quyen(update): return
    await update.message.reply_text("Bot kho đã chạy!\n/tonkho TA - Xem tồn kho\n/nhap TA-CAM 29 Cho dan bo\n/xuat NL-DAUDO 200 May muc")

# --- LOGIC NHẬP / XUẤT - DÙNG SỐ HIỆN TẠI TRÊN SHEET ---
async def nhap_xuat(update: Update, context: ContextTypes.DEFAULT_TYPE, loai: str):
    if not await check_quyen(update): return
    try:
        if len(context.args) < 2:
            await update.message.reply_text("Sai cú pháp! VD: /nhap TA-CAM 29 Cho dan bo"); return

        ma = context.args[0].upper()
        sl = int(context.args[1])
        ghichu = " ".join(context.args[2:])
        kho = ma.split("-")[0]

        if kho not in MAP_KHO:
            await update.message.reply_text(f"Không có kho {kho}! Kho có: TA, VT, TY, MM, U, NL"); return

        tab = MAP_KHO[kho]
        ws = sh.worksheet(tab)
        ws_ls = sh.worksheet("NhatKy")

        all_data = ws.get_all_values()
        headers = all_data[0]
        col_ma = get_col_index(ws, "MaHang")
        col_ton = get_col_index(ws, "TonKho")
        if not col_ton:
            col_ton = get_col_index(ws, "SoLuong")
        col_ten = get_col_index(ws, "TenHang")
        col_dv = get_col_index(ws, "DonVi")
        col_min = get_col_index(ws, "TonToiThieu")

        for i, row in enumerate(all_data[1:], start=2):
            if len(row) < col_ma: continue
            if str(row[col_ma-1]).strip().upper() == ma:
                if kho == "NL" and not ghichu:
                    await update.message.reply_text("⚠️ NL bắt buộc ghi máy nhận! VD: /xuat NL-DAUDO 200 May muc"); return
                if kho == "VT" and not ghichu:
                    await update.message.reply_text("⚠️ VT bắt buộc ghi lô đất! VD: /xuat VT-NPK-8103 38 Lo ngo 01"); return

                ton_hien_tai_str = row[col_ton-1] if len(row) >= col_ton else "0"
                try:
                    ton_hien_tai = float(ton_hien_tai_str) if ton_hien_tai_str else 0
                except:
                    ton_hien_tai = 0

                if loai == "NHAP":
                    ton_moi = ton_hien_tai + sl
                else:
                    ton_moi = ton_hien_tai - sl
                    if ton_moi < 0:
                        await update.message.reply_text(f"❌ Không đủ hàng! Tồn hiện tại chỉ có {int(ton_hien_tai)}, bạn đòi xuất {sl}"); return

                if ton_moi == int(ton_moi):
                    ton_moi = int(ton_moi)
                ws.update_cell(i, col_ton, ton_moi)

                ten_hang = row[col_ten-1] if col_ten and len(row) >= col_ten else ma
                don_vi = row[col_dv-1] if col_dv and len(row) >= col_dv else ""
                ws_ls.append_row([datetime.now().strftime("%d/%m/%Y %H:%M"), kho, loai, ma, sl, ghichu, update.effective_user.first_name, ton_hien_tai, ton_moi])

                msg = f"✅ {loai} {sl} {don_vi} {ten_hang} ({ma})\nTồn cũ: {int(ton_hien_tai) if isinstance(ton_hien_tai,float) else ton_hien_tai} -> Tồn mới: {ton_moi}"

                if col_min and len(row) >= col_min and row[col_min-1]:
                    try:
                        ton_min = float(row[col_min-1])
                        if ton_moi <= ton_min:
                            msg += f"\n⚠️ SẮP HẾT! Dưới mức tối thiểu {int(ton_min)}"
                    except: pass

                await update.message.reply_text(msg)
                return

        await update.message.reply_text(f"Không thấy mã {ma} trong kho {kho}")
    except ValueError:
        await update.message.reply_text("Số lượng phải là số! VD: /nhap TA-CAM 29")
    except Exception as e:
        print(f"Lỗi nhap_xuat: {e}", flush=True)
        await update.message.reply_text(f"Lỗi: {e}")

async def nhap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await nhap_xuat(update, context, "NHAP")

async def xuat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await nhap_xuat(update, context, "XUAT")

async def muon_tra(update: Update, context: ContextTypes.DEFAULT_TYPE, loai: str):
    if not await check_quyen(update): return
    try:
        ma = context.args[0].upper(); nguoi = " ".join(context.args[1:])
        ws = sh.worksheet("Kho_MM")
        all_data = ws.get_all_values()
        col_ma = get_col_index(ws, "MaHang")
        col_tt = get_col_index(ws, "TrangThai")
        col_nguoi = get_col_index(ws, "NguoiMuon")
        for i, row in enumerate(all_data[1:], start=2):
            if str(row[col_ma-1]).strip().upper() == ma:
                ws.update_cell(i, col_tt, "Đang mượn" if loai=="MUON" else "Trong kho")
                if col_nguoi:
                    ws.update_cell(i, col_nguoi, nguoi if loai=="MUON" else "")
                await update.message.reply_text(f"✅ {loai} {ma} - {nguoi if loai=='MUON' else 'Đã trả'}"); return
    except Exception as e:
        print(f"Lỗi muon_tra: {e}", flush=True)
        await update.message.reply_text("Sai cú pháp! VD: /muon MM-CUOC Anh Ba")

async def muon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await muon_tra(update, context, "MUON")

async def tra_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await muon_tra(update, context, "TRA")

async def tonkho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_quyen(update): return
    try:
        kho = context.args[0].upper() if context.args else "ALL"
        if kho == "ALL":
            await update.message.reply_text("Gõ: /tonkho TA  hoặc  /tonkho VT  /tonkho NL  /tonkho MM  /tonkho U  /tonkho TY"); return
        ws = sh.worksheet(MAP_KHO[kho])
        txt = f"📦 TỒN KHO {kho}:\n"
        for r in ws.get_all_records():
            txt += f"{r['MaHang']} - {r['TenHang']}: {r.get('TonKho', r.get('SoLuong'))} {r['DonVi']}\n"
        await update.message.reply_text(txt)
    except Exception as e:
        print(f"Lỗi tonkho: {e}", flush=True)
        await update.message.reply_text("Không thấy kho đó! Gõ /tonkho TA")

if __name__ == "__main__":
    print("Bot đang chạy, không nạp lại SEED - dùng số trên Sheet!", flush=True)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nhap", nhap_cmd))
    app.add_handler(CommandHandler("xuat", xuat_cmd))
    app.add_handler(CommandHandler("muon", muon_cmd))
    app.add_handler(CommandHandler("tra", tra_cmd))
    app.add_handler(CommandHandler("tonkho", tonkho))
    print("Bot đang chạy polling...", flush=True)
    app.run_polling(drop_pending_updates=True)
