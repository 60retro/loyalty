import streamlit as st
import qrcode
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# =================ตั้งค่าระบบ=================
SHEET_NAME = 'Loyalty_Points_Data'

st.set_page_config(page_title="Nami Loyalty", page_icon="☕", layout="centered")

# --- เชื่อมต่อ Google Sheet ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # โหลดจาก Secrets (Cloud) หรือ JSON (Local)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        except:
            st.error("ไม่พบไฟล์ Key (service_account.json) หรือ Secrets")
            st.stop()
            
    client = gspread.authorize(creds)
    return client

try:
    client = init_connection()
    sheet = client.open(SHEET_NAME).sheet1
except Exception as e:
    st.error(f"❌ เชื่อมต่อ Google Sheet ไม่ได้: {e}")
    st.stop()

# ================= ส่วนการทำงานหลัก =================

# เช็ค Mode (ลูกค้า vs ร้านค้า)
query_params = st.query_params
points_param = query_params.get("points", None)

# --- 🟢 โหมดลูกค้า (Customer) ---
if points_param:
    st.markdown("""
        <style>.stApp { background-color: #f0f2f6; } h1 { color: #4CAF50; text-align: center; }</style>
        """, unsafe_allow_html=True)

    st.markdown("<h1>🍃 Nami Member</h1>", unsafe_allow_html=True)
    st.info(f"🎉 คุณได้รับคะแนนสะสม: **{points_param} แต้ม**")
    
    with st.form("customer_form"):
        # เพิ่มช่องกรอกเลขโต๊ะ (ถ้าลูกค้าสแกนที่โต๊ะ)
        table_no = st.text_input("หมายเลขโต๊ะ (Table No.)", placeholder="เช่น 10")
        phone = st.text_input("📱 เบอร์โทรศัพท์สมาชิก", placeholder="กรอกเบอร์โทรศัพท์ 10 หลัก", max_chars=10)
        
        submitted = st.form_submit_button("สะสมแต้มทันที", use_container_width=True)
        
        if submitted:
            if len(phone) < 9:
                st.warning("กรุณากรอกเบอร์โทรศัพท์ให้ถูกต้อง")
            else:
                try:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    # บันทึก: Timestamp, Table, Phone, Points, Status
                    # (ต้องตรงกับลำดับใน Google Sheet A,B,C,D,E)
                    sheet.append_row([timestamp, table_no, phone, points_param, "รอตรวจสอบ"])
                    st.balloons()
                    st.success("✅ บันทึกคะแนนเรียบร้อยแล้ว!")
                    time.sleep(2)
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

# --- 🔵 โหมดร้านค้า (Admin) ---
else:
    st.title("🛡️ Nami Manager Dashboard")
    
    with st.sidebar:
        st.header("Login")
        password = st.text_input("รหัสผ่านร้าน", type="password")
        st.markdown("---")
        base_url = st.text_input("URL ของเว็บนี้", value="https://loyalty.streamlit.app") # <-- แก้เป็นลิงก์จริงของคุณ

    if password != "3457":
        st.warning("กรุณาใส่รหัสผ่านร้าน")
        st.stop()

    tab1, tab2 = st.tabs(["🖨️ สร้าง QR Code", "📋 ตรวจสอบยอด"])

    with tab1:
        st.subheader("สร้าง QR ให้ลูกค้า")
        pts = st.number_input("คะแนนที่จะให้", min_value=1, value=100, step=10)
        if st.button("Generate QR", use_container_width=True):
            clean_url = base_url.rstrip("/")
            target_url = f"{clean_url}?points={pts}"
            
            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(target_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            st.image(img.get_image(), width=300)

    with tab2:
        st.subheader("รายการรอยืนยัน")
        if st.button("🔄 รีเฟรชข้อมูล"):
            st.cache_resource.clear() # ล้าง cache อัตโนมัติเมื่อกดปุ่ม
            st.rerun()

        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
        except:
            st.error("อ่านข้อมูลไม่ได้ ตรวจสอบหัวตาราง Google Sheet")
            st.stop()
            
        # ตรวจสอบว่ามีข้อมูลและมี Column ครบไหม
        required_cols = ['Status', 'Phone', 'Points', 'Table', 'Timestamp']
        # แปลงหัวตารางใน df เป็น set เพื่อเช็ค (เผื่อลำดับสลับกัน)
        missing = [c for c in required_cols if c not in df.columns]

        if missing:
            st.warning(f"⚠️ ไม่พบหัวตาราง: {missing}")
            st.info("คำแนะนำ: ไปที่ Google Sheet แล้วแก้ชื่อหัวตารางให้ตรงเป๊ะๆ (ระวังการเว้นวรรค)")
            st.write("หัวตารางที่โปรแกรมเห็นตอนนี้:", df.columns.tolist())
        
        elif not df.empty:
            df['Status'] = df['Status'].astype(str)
            pending = df[df['Status'].str.upper() != 'TRUE'].copy()
            
            if not pending.empty:
                pending.insert(0, "Approved", False)
                
                # แสดงตารางแบบใหม่ (รองรับช่อง Table)
                edited = st.data_editor(
                    pending,
                    column_config={
                        "Approved": st.column_config.CheckboxColumn("เลือก", default=False),
                        "Timestamp": "เวลา",
                        "Table": "โต๊ะ",    # <--- เพิ่มตรงนี้
                        "Phone": "เบอร์โทร",
                        "Points": "แต้ม",
                        "Status": "สถานะ"
                    },
                    disabled=["Timestamp", "Table", "Phone", "Points", "Status"],
                    hide_index=True,
                    use_container_width=True
                )
                
                if st.button("✅ บันทึกรายการที่เลือก"):
                    to_process = edited[edited['Approved'] == True]
                    count = 0
                    for index, row in to_process.iterrows():
                        real_idx = df.index[df['Timestamp'] == row['Timestamp']].tolist()
                        if real_idx:
                            row_num = real_idx[0] + 2
                            col_idx = df.columns.get_loc("Status") + 1
                            sheet.update_cell(row_num, col_idx, "TRUE")
                            count += 1
                    
                    st.success(f"บันทึกแล้ว {count} รายการ")
                    time.sleep(1)
                    st.rerun()
            else:
                st.info("✅ ไม่มียอดค้าง ตรวจสอบครบแล้ว")
