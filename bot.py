import os
import json
import gspread
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
import threading
from flask import Flask

# Tạo 1 web giả để Render tưởng bot có cổng
app_web = Flask(__name__)
@app_web.route('/')
def home():
    return "Bot đang chạy!"

def run_web():
    import os
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.environ.get("TOKEN")
SHEET_ID = os.environ.get("SHEET_ID")
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
gc = gspread.service_account_from_dict(creds_dict)
sh = gc.open_by_key(SHEET_ID)

MAP_KHO = {"TA":"Kho_TA","VT":"Kho_VT","TY":"Kho_TY","MM":"Kho_MM","U":"Kho_U","NL":"Kho_NL"}

# Data chốt sổ - ĐÃ NẠP SẴN 51 MÃ CỦA BẠN
SEED = {
 "Kho_TA": [["TA-CAM","Cám chăn nuôi","Bao",75,20],["TA-MATRI","Mật rỉ đường","Can",9,2],["TA-MENRUOU","Men rượu","Kg",10,2]],
 "Kho_VT": [["VT-NPK-8103","Phân bón NPK 8-10-3","Bao",350,50],["VT-NPK-5103","Phân bón NPK 5-10-3+8S","Bao",184,50],["VT-HUUCO","Phân hữu cơ vi sinh phân gà","Bao",431,50],["VT-NGO511","Hạt giống ngô 511","Bao",4,1],["VT-NGOGIONG","Ngô giống","Bao",5,1],["VT-MOBASSA","Hạt giống cỏ Mobassa","Bao",10,2],["VT-SUDAN","Hạt giống cỏ Sudan lai","Bao",7,2],["VT-BAOTAI","Bao tải trống","Cái",100,20],["VT-DAYROM","Dây buộc cuộn rơm","Cuộn",2,1]],
 "Kho_NL": [["NL-DAUDO","Dầu DO","Lít",460,100]],
 "Kho_U": [["U-JUMBO","Bao jumbo ủ chua","Bao",10,2],["U-PHI-RONG","Phi ủ chua vỏ rỗng","Phi",76,10]],
 "Kho_MM": [["MM-MAYMUC","Máy múc","Chiếc",1],["MM-CAYLON","Máy cày lớn","Chiếc",1],["MM-CAYNHO","Máy cày nhỏ","Chiếc",1],["MM-OTOTAI","Ô tô tải","Chiếc",2],["MM-TRON3K","Máy trộn 3 khối","Chiếc",1],["MM-CUAMAY-L","Cưa máy lớn","Chiếc",1],["MM-CUAMAY-N","Cưa máy nhỏ","Chiếc",1],["MM-CATCO","Máy cắt cỏ","Chiếc",3],["MM-KHOANDAT","Máy khoan đất","Chiếc",1],["MM-BOMDAU","Máy bơm dầu","Chiếc",1],["MM-HAN","Máy hàn","Chiếc",1],["MM-CATSAT","Máy cắt sắt","Chiếc",1],["MM-CATNHO","Máy cắt nhỏ","Chiếc",1],["MM-KHOANPIN","Máy khoan pin","Chiếc",2],["MM-KHOANDIEN","Khoan điện","Chiếc",1],["MM-CANDT","Cân điện tử","Chiếc",1],["MM-CANBAN","Cân bàn","Chiếc",1],["MM-BEPDOT","Bếp đốt công nghiệp","Chiếc",2],["MM-GIEONGO","Máy gieo ngô","Cái",4],["MM-XERUA","Xe rùa","Cái",3],["MM-CUOC","Cuốc","Cái",4],["MM-XENG","Xẻng","Cái",4],["MM-CAO","Cào 3 răng","Cái",2],["MM-BUA","Búa","Cái",5],["MM-BAT","Bạt","Cái",2],["MM-PHUN","Bình phun tay","Cái",1],["MM-TUOIRAU","Bình tưới rau","Cái",5],["MM-XOLON","Xô lớn","Cái",5],["MM-XONHO","Xô nhỏ","Cái",5],["MM-CHOI","Chổi xương","Cái",4],["MM-DONGHE","Bộ đồ nghề","Bộ",1],["MM-LUOICAY","Lưỡi cày nhỏ","Cái",1]],
}

def seed():
    for tab, rows in SEED.items():
        ws = sh.worksheet(tab)
        if len(ws.get_all_values()) <= 1:
            ws.append_rows(rows)
    print("Đã nạp xong 6 kho!")

async def nhap_xuat(update: Update, context: ContextTypes.DEFAULT_TYPE, loai: str):
    # Dùng: /nhap VT-NPK-8103 10 Lo ngo 01  |  /xuat NL-DAUDO 200 May muc
    try:
        ma = context.args[0].upper(); sl = int(context.args[1]); ghichu = " ".join(context.args[2:])
        kho = ma.split("-")[0]; tab = MAP_KHO[kho]
        ws = sh.worksheet(tab); ws_ls = sh.worksheet("NhatKy")
        data = ws.get_all_records()
        for i, r in enumerate(data, start=2):
            if str(r['MaHang']).upper() == ma:
                # Kiểm tra bắt buộc theo 6 kho
                if kho=="NL" and not ghichu: await update.message.reply_text("⚠️ NL bắt buộc ghi máy nhận! VD: /xuat NL-DAUDO 200 May muc"); return
                if kho=="VT" and not ghichu: await update.message.reply_text("⚠️ VT bắt buộc ghi lô đất! VD: /xuat VT-NPK-8103 38 Lo ngo 01"); return
                ton_moi = r['TonKho'] + sl if loai=="NHAP" else r['TonKho'] - sl
                ws.update_cell(i, 4, ton_moi)
                ws_ls.append_row([datetime.now().strftime("%d/%m/%Y %H:%M"), kho, loai, ma, sl, ghichu, update.effective_user.first_name])
                msg = f"✅ {loai} {sl} {r['DonVi']} {r['TenHang']} ({ma})\nKho {kho} - Tồn mới: {ton_moi}"
                if 'TonToiThieu' in r and ton_moi <= r['TonToiThieu']: msg += f"\n⚠️ SẮP HẾT!"
                await update.message.reply_text(msg); return
        await update.message.reply_text(f"Không thấy mã {ma}")
    except: await update.message.reply_text("Sai cú pháp! VD: /nhap TA-CAM 29 Cho dan bo")

async def muon_tra(update: Update, context: ContextTypes.DEFAULT_TYPE, loai: str):
    ma = context.args[0].upper(); nguoi = " ".join(context.args[1:])
    ws = sh.worksheet("Kho_MM"); data = ws.get_all_records()
    for i, r in enumerate(data, start=2):
        if str(r['MaHang']).upper() == ma:
            ws.update_cell(i, 5, "Đang mượn" if loai=="MUON" else "Trong kho")
            ws.update_cell(i, 6, nguoi if loai=="MUON" else "")
            await update.message.reply_text(f"✅ {loai} {r['TenHang']} - {nguoi if loai=='MUON' else 'Đã trả'}"); return

async def tonkho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kho = context.args[0].upper() if context.args else "ALL"
    if kho=="ALL":
        await update.message.reply_text("Gõ: /tonkho TA  hoặc  /tonkho VT  /tonkho NL  /tonkho MM  /tonkho U  /tonkho TY"); return
    ws = sh.worksheet(MAP_KHO[kho]); txt = f"📦 TỒN KHO {kho}:\n"
    for r in ws.get_all_records(): txt += f"{r['MaHang']} - {r['TenHang']}: {r.get('TonKho', r.get('SoLuong'))} {r['DonVi']}\n"
    await update.message.reply_text(txt)

seed()
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("nhap", lambda u,c: nhap_xuat(u,c,"NHAP")))
app.add_handler(CommandHandler("xuat", lambda u,c: nhap_xuat(u,c,"XUAT")))
app.add_handler(CommandHandler("muon", lambda u,c: muon_tra(u,c,"MUON")))
app.add_handler(CommandHandler("tra", lambda u,c: muon_tra(u,c,"TRA")))
app.add_handler(CommandHandler("tonkho", tonkho))
app.run_polling()
