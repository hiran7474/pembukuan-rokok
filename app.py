import pandas as pd
import sqlite3
import streamlit as st

# ---------------------------------------------------------
# SETUP HALAMAN & KONFIGURASI TOKO
# ---------------------------------------------------------
st.set_page_config(page_title="Pembukuan Penjualan Rokok (Online/SQLite)", layout="wide")

NAMA_TOKO = "BAF Koperasi"
ALAMAT_TOKO = "Jl. Baturraden Timur"
DB_FILE = "toko_rokok.db"

# ---------------------------------------------------------
# Koneksi & Inisialisasi Database SQLite
# ---------------------------------------------------------
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
  conn = get_connection()
  cursor = conn.cursor()

  # Tabel Barang
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang (
            KODE TEXT PRIMARY KEY,
            Nama_Barang TEXT,
            Kategori TEXT,
            Harga_Beli INTEGER,
            Harga_Jual INTEGER,
            Stok_Awal INTEGER,
            Total_Restok INTEGER,
            Total_Keluar INTEGER,
            Satuan TEXT
        )
    """)

  # Tabel Riwayat Penjualan
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS riwayat_penjualan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Tanggal TEXT,
            Kode TEXT,
            Nama_Barang TEXT,
            Jumlah INTEGER,
            Total_Harga INTEGER
        )
    """)

  conn.commit()
  conn.close()

init_db()

# ---------------------------------------------------------
# FUNGSI LOAD & SAVE DATA (DATABASE SQLITE)
# ---------------------------------------------------------
def load_data():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM barang", conn)
        conn.close()
        
        if df.empty:
            return pd.DataFrame(columns=[
                "Kode", "Nama Barang", "Kategori", "Harga Beli", 
                "Harga Jual", "Stok Awal", "Total Restok", "Total Keluar", "Satuan"
            ])
        
        # Urutkan berdasarkan nomor pada kode jika ada
        if "Kode" in df.columns:
            df["Temp_Nomor"] = df["Kode"].astype(str).str.extract(r'(\d+)').fillna(0).astype(int)
            df = df.sort_values(by="Temp_Nomor", ascending=True).drop(columns=["Temp_Nomor"]).reset_index(drop=True)
            
        return df
    except Exception as e:
        conn.close()
        st.error(f"Gagal membaca database barang: {e}")
        return pd.DataFrame(columns=[
            "Kode", "Nama Barang", "Kategori", "Harga Beli", 
            "Harga Jual", "Stok Awal", "Total Restok", "Total Keluar", "Satuan"
        ])

if 'data_barang' not in st.session_state:
    st.session_state.data_barang = load_data()

df_barang = st.session_state.data_barang
df = df_barang.copy()

def save_data(df_to_save):
    conn = get_connection()
    try:
        if "Kode" in df_to_save.columns:
            df_to_save = df_to_save.dropna(subset=["Kode"], how="any")
        df_to_save = df_to_save.fillna("")
        
        # Timpa seluruh tabel barang dengan data terbaru
        df_to_save.to_sql("barang", conn, if_exists="replace", index=False)
        conn.close()
        
        st.session_state.data_barang = df_to_save.copy()
        return True
    except Exception as e:
        conn.close()
        st.error(f"Gagal menyimpan ke database: {e}")
        return False

# ---------------------------------------------------------
# FUNGSI RIWAYAT PENJUALAN (LOG HARIAN SQLITE)
# ---------------------------------------------------------
def load_riwayat():
    conn = get_connection()
    try:
        df_r = pd.read_sql("SELECT No_Struk, Tanggal, Nama_Barang AS 'Nama Barang', Jumlah_Keluar AS 'Jumlah Keluar', Satuan, Status FROM riwayat_penjualan", conn)
        conn.close()
        if df_r.empty:
            return pd.DataFrame(columns=["No_Struk", "Tanggal", "Nama Barang", "Jumlah Keluar", "Satuan", "Status"])
        return df_r
    except Exception:
        conn.close()
        return pd.DataFrame(columns=["No_Struk", "Tanggal", "Nama Barang", "Jumlah Keluar", "Satuan", "Status"])

def save_riwayat_db(list_baru_dicts):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for item in list_baru_dicts:
            cursor.execute("""
                INSERT INTO riwayat_penjualan (No_Struk, Tanggal, Nama_Barang, Jumlah_Keluar, Satuan, Status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item["No_Struk"], item["Tanggal"], item["Nama Barang"], item["Jumlah Keluar"], item["Satuan"], item["Status"]))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        st.error(f"Gagal menyimpan riwayat ke database: {e}")
        return False

def update_or_delete_riwayat(df_r_new):
    conn = get_connection()
    try:
        # Ubah nama kolom kembali agar sesuai dengan struktur database sql (tanpa spasi)
        df_db = df_r_new.rename(columns={"Nama Barang": "Nama_Barang", "Jumlah Keluar": "Jumlah_Keluar"})
        df_db.to_sql("riwayat_penjualan", conn, if_exists="replace", index=False)
        conn.close()
        return True
    except Exception as e:
        conn.close()
        st.error(f"Gagal memperbarui riwayat database: {e}")
        return False

if 'riwayat_jual' not in st.session_state:
    st.session_state.riwayat_jual = load_riwayat()

if 'keranjang' not in st.session_state:
    st.session_state.keranjang = []

# ---------------------------------------------------------
# FUNGSI CETAK STRUK MULTI-ITEM
# ---------------------------------------------------------
def buat_tampilan_struk_multi(no_struk, tgl, list_items, status):
    label_total = "TOTAL" if "Lunas" in str(status) or "Tunai" in str(status) else "TOTAL HUTANG/BON"
    
    rows_html = ""
    grand_total = 0
    for item in list_items:
        nama_b = item["nama"]
        jml_b = item["jml"]
        sat_b = item["satuan"]
        h_jual_b = item["h_jual"]
        subtotal = jml_b * h_jual_b
        grand_total += subtotal
        
        rows_html += f"<tr><td colspan='2' style='font-weight: bold; padding-top: 4px;'>{nama_b}</td></tr>"
        rows_html += f"<tr><td>{jml_b} {sat_b} x Rp {h_jual_b:,.0f}</td><td style='text-align: right;'>Rp {subtotal:,.0f}</td></tr>"

    struk_html = f"""<style>@media print {{ body * {{ visibility: hidden; }} #area-struk-print, #area-struk-print * {{ visibility: visible; }} #area-struk-print {{ position: absolute; left: 0; top: 0; width: 58mm !important; margin: 0 !important; padding: 0 !important; }} .no-print {{ display: none !important; }} @page {{ size: 58mm auto; margin: 0mm; }} }}</style><div id="area-struk-print" style="font-family: 'Courier New', Courier, monospace; width: 250px; padding: 10px; border: 1px dashed #333; background-color: #fff; color: #000; margin: auto; border-radius: 5px;"><h3 style="text-align: center; margin: 0; font-size: 15px;">{NAMA_TOKO}</h3><p style="text-align: center; margin: 2px 0; font-size: 10px;">{ALAMAT_TOKO}</p><p style="text-align: center; margin: 2px 0; font-size: 10px;">--------------------------------</p><p style="margin: 2px 0; font-size: 10px;">No. Struk: {no_struk}</p><p style="margin: 2px 0; font-size: 10px;">Tanggal  : {tgl}</p><p style="margin: 2px 0; font-size: 10px;">Status   : <b>{status}</b></p><p style="text-align: center; margin: 2px 0; font-size: 10px;">--------------------------------</p><table style="width: 100%; font-size: 11px; border-collapse: collapse;">{rows_html}</table><p style="text-align: center; margin: 2px 0; font-size: 10px;">--------------------------------</p><table style="width: 100%; font-size: 11px; font-weight: bold;"><tr><td>{label_total}</td><td style="text-align: right;">Rp {grand_total:,.0f}</td></tr></table><p style="text-align: center; margin: 2px 0; font-size: 10px;">--------------------------------</p><p style="text-align: center; margin: 5px 0 0 0; font-size: 10px;">Terima Kasih Atas Kunjungan Anda!</p><p style="text-align: center; margin: 2px 0; font-size: 9px; color: #555;">Pengelola: Hiran</p><div class="no-print" style="text-align: center; margin-top: 15px;"><button onclick="window.print()" style="background-color: #008CBA; color: white; padding: 10px 18px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px;">🖨️ Kirim ke Printer 58mm</button></div></div>"""
    
    return struk_html

# ---------------------------------------------------------
# KALKULASI FINANSIAL & STOK
# ---------------------------------------------------------
if not df.empty and "Stok Awal" in df.columns:
    df["Sisa Stok"] = df["Stok Awal"] + df["Total Restok"] - df["Total Keluar"]
    df["Total Omset"] = df["Total Keluar"] * df["Harga Jual"]
    df["Total HPP (Modal)"] = df["Total Keluar"] * df["Harga Beli"]
    df["Laba Kotor Total"] = df["Total Omset"] - df["Total HPP (Modal)"]

    if 'riwayat_jual' in st.session_state and not st.session_state.riwayat_jual.empty:
        df_riw_calc = st.session_state.riwayat_jual
        if "Status" in df_riw_calc.columns:
            df_lunas = df_riw_calc[df_riw_calc["Status"].astype(str).str.contains("Tunai|Lunas", case=False, na=False)]
        else:
            df_lunas = pd.DataFrame(columns=["Nama Barang", "Jumlah Keluar"])
    else:
        df_lunas = pd.DataFrame(columns=["Nama Barang", "Jumlah Keluar"])

    total_cash_omset = 0
    total_modal_hpp = 0
    
    if not df_lunas.empty:
        for _, row_lunas in df_lunas.iterrows():
            nama_Rokok = row_lunas["Nama Barang"]
            jml_lunas = row_lunas["Jumlah Keluar"]
            
            match_barang = df[df["Nama Barang"] == nama_Rokok]
            if not match_barang.empty:
                h_jual = match_barang.iloc[0]["Harga Jual"]
                h_beli = match_barang.iloc[0]["Harga Beli"]
                total_cash_omset += (jml_lunas * h_jual)
                total_modal_hpp += (jml_lunas * h_beli)

    total_laba_kotor = total_cash_omset - total_modal_hpp
    bagi_hasil = total_laba_kotor * 0.50
    setoran_pemilik = total_modal_hpp + bagi_hasil
    bagian_pengelola = bagi_hasil
else:
    total_cash_omset = total_modal_hpp = total_laba_kotor = 0
    bagi_hasil = setoran_pemilik = bagian_pengelola = 0

# ---------------------------------------------------------
# SIDEBAR MENU
# ---------------------------------------------------------
st.sidebar.title("📦 Menu Utama")

fitur = st.sidebar.radio(
    "Pilih Fitur:",
    [
        "📊 Dashboard & Laporan Setoran", 
        "➕ Restok (Barang Masuk)", 
        "🛒 Penjualan (Barang Keluar)", 
        "⚙️ Kelola Master Barang", 
        "🛠️ Edit / Hapus Barang & Reset"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("👨‍💻 **Pengelola:** Hiran")

# ---------------------------------------------------------
# 1. HALAMAN DASHBOARD
# ---------------------------------------------------------
if fitur == "📊 Dashboard & Laporan Setoran":
    tab_dash1, tab_dash2 = st.tabs(["📊 Ringkasan Kas & Laporan", "📑 Rekap Rinci Per Produk (Setoran & Pengelola)"])
    
    with tab_dash1:
        st.subheader("💰 Ringkasan Uang Penjualan Terkumpul")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Cash Omset Penjualan", f"Rp {total_cash_omset:,.0f}".replace(",", "."))
        m2.metric("Pengembalian Modal (HPP)", f"Rp {total_modal_hpp:,.0f}".replace(",", "."))
        m3.metric("Total Laba Bersih/Kotor", f"Rp {total_laba_kotor:,.0f}".replace(",", "."))
        
        st.markdown("---")
        st.subheader("📋 Laporan Detail Stok & Penjualan Per Produk")
        
        if not df.empty and "Nama Barang" in df.columns:
            tabel_tampil = df[[
                "Kode", "Nama Barang", "Kategori", "Harga Beli", "Harga Jual", 
                "Stok Awal", "Total Restok", "Total Keluar", "Sisa Stok", 
                "Total Omset", "Total HPP (Modal)", "Laba Kotor Total", "Satuan"
            ]].copy()
            
            tabel_formatted = tabel_tampil.copy()
            for col in ["Harga Beli", "Harga Jual", "Total Omset", "Total HPP (Modal)", "Laba Kotor Total"]:
                tabel_formatted[col] = tabel_formatted[col].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            
            st.dataframe(tabel_formatted, use_container_width=True)
            
            csv_data = tabel_tampil.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Unduh Laporan Stok & Keuangan (CSV)",
                data=csv_data,
                file_name='Laporan_Pembukuan_Rokok.csv',
                mime='text/csv',
                key="download_laporan_stok"
            )
        else:
            st.warning("Belum ada data barang di database.")

    with tab_dash2:
        st.subheader("📑 Rekap Rinci Setoran & Bagian Admin Per Rokok")
        st.caption("Tabel ini merinci berapa bungkus yang laku, berapa setoran ke pemilik, dan bagian pengelola untuk setiap merek rokok (hanya menghitung transaksi Tunai/Lunas).")
        
        if not df.empty and "Nama Barang" in df.columns:
            df_rekap = df.copy()
            
            if 'riwayat_jual' in st.session_state and not st.session_state.riwayat_jual.empty:
                df_riw_rekap = st.session_state.riwayat_jual
                if "Status" in df_riw_rekap.columns:
                    df_lunas_rekap = df_riw_rekap[df_riw_rekap["Status"].astype(str).str.contains("Tunai|Lunas", case=False, na=False)]
                    lunas_counts = df_lunas_rekap.groupby("Nama Barang")["Jumlah Keluar"].sum().to_dict()
                else:
                    lunas_counts = {}
            else:
                lunas_counts = {}
                
            df_rekap["Bungkus Lunas"] = df_rekap["Nama Barang"].map(lunas_counts).fillna(0).astype(int)
            df_rekap["Total Omset Lunas"] = df_rekap["Bungkus Lunas"] * df_rekap["Harga Jual"]
            df_rekap["Modal Lunas"] = df_rekap["Bungkus Lunas"] * df_rekap["Harga Beli"]
            df_rekap["Laba Kotor Lunas"] = df_rekap["Total Omset Lunas"] - df_rekap["Modal Lunas"]
            df_rekap["Bagi Hasil Lunas (50%)"] = df_rekap["Laba Kotor Lunas"] * 0.50
            df_rekap["Setoran ke Pemilik"] = df_rekap["Modal Lunas"] + df_rekap["Bagi Hasil Lunas (50%)"]
            df_rekap["Bagian Pengelola"] = df_rekap["Bagi Hasil Lunas (50%)"]
            
            tabel_rekap_produk = df_rekap[[
                "Nama Barang", "Total Keluar", "Bungkus Lunas", "Satuan", "Total Omset Lunas", 
                "Modal Lunas", "Laba Kotor Lunas", "Setoran ke Pemilik", "Bagian Pengelola"
            ]].copy()
            
            total_bungkus_fisik = tabel_rekap_produk["Total Keluar"].sum()
            total_bungkus_lunas = tabel_rekap_produk["Bungkus Lunas"].sum()
            total_omset_all = tabel_rekap_produk["Total Omset Lunas"].sum()
            total_modal_all = tabel_rekap_produk["Modal Lunas"].sum()
            total_laba_all = tabel_rekap_produk["Laba Kotor Lunas"].sum()
            total_setor_all = tabel_rekap_produk["Setoran ke Pemilik"].sum()
            total_pengelola_all = tabel_rekap_produk["Bagian Pengelola"].sum()
            
            baris_total = pd.DataFrame([{
                "Nama Barang": "📌 TOTAL KESELURUHAN",
                "Total Keluar": total_bungkus_fisik,
                "Bungkus Lunas": total_bungkus_lunas,
                "Satuan": "Bungkus",
                "Total Omset Lunas": total_omset_all,
                "Modal Lunas": total_modal_all,
                "Laba Kotor Lunas": total_laba_all,
                "Setoran ke Pemilik": total_setor_all,
                "Bagian Pengelola": total_pengelola_all
            }])
            
            tabel_rekap_produk = pd.concat([tabel_rekap_produk, baris_total], ignore_index=True)
            tabel_rekap_formatted = tabel_rekap_produk.copy()
            for col in ["Total Omset Lunas", "Modal Lunas", "Laba Kotor Lunas", "Setoran ke Pemilik", "Bagian Pengelola"]:
                tabel_rekap_formatted[col] = tabel_rekap_formatted[col].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            
            tabel_rekap_formatted.columns = [
                "Nama Rokok", "Keluar Fisik", "Terjual Lunas", "Satuan", "Total Omset", 
                "Modal (HPP)", "Laba Kotor", "Setoran ke Pemilik", "Bagian Pengelola"
            ]
            
            st.dataframe(tabel_rekap_formatted, use_container_width=True)
            
            csv_rekap = tabel_rekap_produk.iloc[:-1].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Unduh Rekap Rinci Per Rokok (CSV)",
                data=csv_rekap,
                file_name='Rekap_Rinci_Per_Rokok.csv',
                mime='text/csv',
                key="download_rekap_rinci"
            )
        else:
            st.warning("Belum ada data barang untuk direkap.") 

# ---------------------------------------------------------
# 2. RESTOK (BARANG MASUK)
# ---------------------------------------------------------
elif fitur == "➕ Restok (Barang Masuk)":
    st.title("➕ Input Restok Barang Masuk")
    if not df.empty and "Nama Barang" in df.columns:
        pilihan_barang = st.selectbox("Pilih Barang:", df["Nama Barang"].tolist())
        jumlah_masuk = st.number_input("Jumlah Masuk (Bungkus):", min_value=1, step=1)
        
        if st.button("Simpan Restok"):
            idx = df[df["Nama Barang"] == pilihan_barang].index[0]
            df.at[idx, "Total Restok"] += jumlah_masuk
            
            if save_data(df[["Kode", "Nama Barang", "Kategori", "Harga Beli", "Harga Jual", "Stok Awal", "Total Restok", "Total Keluar", "Satuan"]]):
                st.success(f"Berhasil menambahkan restok {jumlah_masuk} Bungkus untuk {pilihan_barang}!")
                st.rerun()
    else:
        st.warning("Belum ada data barang di database.")

# ---------------------------------------------------------
# 3. PENJUALAN (KERANJANG / MULTI-ITEM) & CETAK STRUK
# ---------------------------------------------------------
elif fitur == "🛒 Penjualan (Barang Keluar)":
    st.title("🛒 Input Penjualan & Pengelolaan Hutang")
    
    tab_jual1, tab_jual2 = st.tabs(["➕ Kasir (Keranjang Belanja)", "📅 Riwayat & Lunasi Hutang"])
    
    with tab_jual1:
        col_form, col_struk = st.columns([1.3, 1])
        
        with col_form:
            st.subheader("🛒 Tambah Item ke Keranjang")
            if not df.empty and "Nama Barang" in df.columns:
                tanggal_transaksi = st.date_input("Tanggal Transaksi Penjualan:")
                
                c_item1, c_item2, c_item3 = st.columns([2, 1, 1])
                with c_item1:
                    pilihan_barang = st.selectbox("Pilih Barang:", df["Nama Barang"].tolist(), key="select_brg_kasir")
                with c_item2:
                    jumlah_keluar = st.number_input("Jumlah:", min_value=1, step=1, key="num_brg_kasir")
                with c_item3:
                    st.write(" ")
                    st.write(" ")
                    tambah_item = st.button("➕ Tambah Item")
                
                if tambah_item:
                    idx = df[df["Nama Barang"] == pilihan_barang].index[0]
                    satuan_b = df.loc[idx, "Satuan"]
                    h_jual_b = int(df.loc[idx, "Harga Jual"])
                    
                    st.session_state.keranjang.append({
                        "nama": pilihan_barang,
                        "jml": int(jumlah_keluar),
                        "satuan": satuan_b,
                        "h_jual": h_jual_b,
                        "subtotal": int(jumlah_keluar) * h_jual_b
                    })
                    st.toast(f"Ditambahkan: {pilihan_barang} ({jumlah_keluar} {satuan_b})")
                
                st.markdown("---")
                st.subheader("📋 Keranjang Belanja Saat Ini")
                
                if st.session_state.keranjang:
                    df_krj = pd.DataFrame(st.session_state.keranjang)
                    df_krj_tampil = df_krj[["nama", "jml", "satuan", "h_jual", "subtotal"]].copy()
                    df_krj_tampil.columns = ["Nama Barang", "Qty", "Satuan", "Harga @", "Subtotal"]
                    
                    df_krj_formatted = df_krj_tampil.copy()
                    df_krj_formatted["Harga @"] = df_krj_formatted["Harga @"].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                    df_krj_formatted["Subtotal"] = df_krj_formatted["Subtotal"].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                    
                    st.dataframe(df_krj_formatted, use_container_width=True)
                    
                    total_belanja = df_krj["subtotal"].sum()
                    st.markdown(f"### 💰 **Total Belanja: Rp {total_belanja:,.0f}**".replace(",", "."))
                    
                    c_act1, c_act2 = st.columns([1, 1])
                    with c_act1:
                        if st.button("🗑️ Kosongkan Keranjang"):
                            st.session_state.keranjang = []
                            st.rerun()
                            
                    status_pembayaran = st.radio("Status Pembayaran Transaksi Ini:", ["Tunai (Lunas)", "Hutang (Belum Bayar)"], horizontal=True, key="radio_status_kasir")
                    
                    if st.button("💾 SIMPAN TRANSAKSI & CETAK STRUK", type="primary", use_container_width=True):
                        no_struk = f"STR-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
                        
                        list_baru_riw = []
                        for item in st.session_state.keranjang:
                            nm = item["nama"]
                            jml = item["jml"]
                            sat = item["satuan"]
                            
                            if nm in df["Nama Barang"].values:
                                idx_m = df[df["Nama Barang"] == nm].index[0]
                                df.at[idx_m, "Total Keluar"] += jml
                            
                            list_baru_riw.append({
                                "No_Struk": no_struk,
                                "Tanggal": str(tanggal_transaksi),
                                "Nama Barang": nm,
                                "Jumlah Keluar": jml,
                                "Satuan": sat,
                                "Status": status_pembayaran
                            })
                        
                        save_data(df[["Kode", "Nama Barang", "Kategori", "Harga Beli", "Harga Jual", "Stok Awal", "Total Restok", "Total Keluar", "Satuan"]])
                        save_riwayat_db(list_baru_riw)
                        
                        st.session_state.riwayat_jual = load_riwayat()
                        st.session_state.last_struk = {
                            "no_struk": no_struk,
                            "tgl": str(tanggal_transaksi),
                            "items": st.session_state.keranjang.copy(),
                            "status": status_pembayaran
                        }
                        
                        st.session_state.keranjang = []
                        st.success(f"Transaksi {no_struk} Berhasil Disimpan!")
                        st.rerun()
                else:
                    st.info("Keranjang belanja masih kosong. Silakan pilih barang di atas lalu klik **➕ Tambah Item**.")
            else:
                st.warning("Belum ada data barang di database.")

        with col_struk:
            st.subheader("🖨️ Struk Pembelian (1 Struk Multi-Item)")
            if 'last_struk' in st.session_state:
                ls = st.session_state.last_struk
                struk_html = buat_tampilan_struk_multi(ls['no_struk'], ls['tgl'], ls['items'], ls['status'])
                st.markdown(struk_html, unsafe_allow_html=True)
                st.caption("💡 Petunjuk Cetak: Anda bisa menekan tombol cetak biru di atas atau tombol `Ctrl + P`.")
            else:
                st.info("Struk transaksi belanja akan muncul di sini setelah Anda menyimpan transaksi.")

    with tab_jual2:
        st.subheader("📅 Log Riwayat Transaksi & Pelunasan Hutang")
        st.caption("Daftar transaksi di bawah ini otomatis diurutkan dari tanggal terbaru agar mudah dilacak.")
        
        df_riwayat_tampil = st.session_state.riwayat_jual.copy()
        
        if "No_Struk" not in df_riwayat_tampil.columns:
            df_riwayat_tampil["No_Struk"] = "-"
        if "Status" not in df_riwayat_tampil.columns:
            df_riwayat_tampil["Status"] = "Tunai (Lunas)"
        
        if not df_riwayat_tampil.empty:
            df_riwayat_tampil["_index_asli"] = df_riwayat_tampil.index
            
            try:
                df_riwayat_tampil["Tanggal_Sort"] = pd.to_datetime(df_riwayat_tampil["Tanggal"])
                df_riwayat_tampil = df_riwayat_tampil.sort_values(by="Tanggal_Sort", ascending=False).drop(columns=["Tanggal_Sort"])
                df_riwayat_tampil = df_riwayat_tampil.reset_index(drop=True)
            except Exception:
                pass
            
            st.dataframe(df_riwayat_tampil.drop(columns=["_index_asli"]), use_container_width=True)
            st.markdown("---")
            
            st.subheader("🖨️ Cetak Ulang Struk Transaksi Lama")
            subtab_cetak1, subtab_cetak2, subtab_cetak3 = st.tabs([
                "🛒 Pilih Bebas Beberapa Baris (Multi-Item)", 
                "🏷️ Berdasarkan Nomor Struk", 
                "📄 Satuan (Per Baris)"
            ])
            
            with subtab_cetak1:
                df_riwayat_tampil["label_pilihan"] = (
                    "Baris ke-" + df_riwayat_tampil.index.astype(str) + 
                    " | Tgl: " + df_riwayat_tampil["Tanggal"].astype(str) + 
                    " | Rokok: " + df_riwayat_tampil["Nama Barang"].astype(str) + 
                    " (" + df_riwayat_tampil["Jumlah Keluar"].astype(str) + " " + df_riwayat_tampil["Satuan"].astype(str) + ")" +
                    " | Status: " + df_riwayat_tampil["Status"].astype(str)
                )
                
                selected_indices = st.multiselect(
                    "Pilih Item Transaksi yang Ingin Digabung ke Struk:",
                    options=df_riwayat_tampil.index.tolist(),
                    format_func=lambda x: df_riwayat_tampil.loc[x, "label_pilihan"],
                    key="multiselect_cetak_gabungan"
                )
                
                if st.button("🖨️ Tampilkan Struk Gabungan Terpilih", type="primary", key="btn_cetak_multi_custom"):
                    if selected_indices:
                        df_selected = df_riwayat_tampil.loc[selected_indices]
                        tgl_c = df_selected.iloc[0]["Tanggal"]
                        status_c = df_selected.iloc[0]["Status"]
                        no_str_c = df_selected.iloc[0]["No_Struk"]
                        
                        if str(no_str_c) in ["-", "nan", "None", ""]:
                            no_str_c = f"STR-MANUAL-{str(tgl_c).replace('-','')}"
                            
                        items_c = []
                        for _, r_sub in df_selected.iterrows():
                            nm_c = r_sub["Nama Barang"]
                            jml_c = int(r_sub["Jumlah Keluar"])
                            sat_c = r_sub["Satuan"]
                            match_b = df[df["Nama Barang"] == nm_c]
                            hj_c = int(match_b.iloc[0]["Harga Jual"]) if not match_b.empty else 0
                            items_c.append({"nama": nm_c, "jml": jml_c, "satuan": sat_c, "h_jual": hj_c})
                            
                        struk_html = buat_tampilan_struk_multi(no_str_c, tgl_c, items_c, status_c)
                        st.markdown(struk_html, unsafe_allow_html=True)
                    else:
                        st.warning("Pilih minimal satu baris item terlebih dahulu.")
                        
            with subtab_cetak2:
                unique_struks = [s for s in df_riwayat_tampil["No_Struk"].unique().tolist() if str(s) not in ["-", "nan", "None", ""]]
                if unique_struks:
                    pilihan_struk_cetak = st.selectbox(
                        "Pilih Transaksi (Nomor Struk Gabungan):",
                        options=unique_struks,
                        format_func=lambda x: f"No. Struk: {x} | Tgl: {df_riwayat_tampil[df_riwayat_tampil['No_Struk']==x].iloc[0]['Tanggal']} | ({len(df_riwayat_tampil[df_riwayat_tampil['No_Struk']==x])} Merek) | Status: {df_riwayat_tampil[df_riwayat_tampil['No_Struk']==x].iloc[0]['Status']}",
                        key="select_cetak_no_struk"
                    )
                    
                    if st.button("🖨️ Tampilkan Struk Nomor Ini", type="primary", key="btn_cetak_gabungan"):
                        df_sub = df_riwayat_tampil[df_riwayat_tampil["No_Struk"] == pilihan_struk_cetak]
                        tgl_c = df_sub.iloc[0]["Tanggal"]
                        status_c = df_sub.iloc[0]["Status"]
                        
                        items_c = []
                        for _, r_sub in df_sub.iterrows():
                            nm_c = r_sub["Nama Barang"]
                            jml_c = int(r_sub["Jumlah Keluar"])
                            sat_c = r_sub["Satuan"]
                            match_b = df[df["Nama Barang"] == nm_c]
                            hj_c = int(match_b.iloc[0]["Harga Jual"]) if not match_b.empty else 0
                            items_c.append({"nama": nm_c, "jml": jml_c, "satuan": sat_c, "h_jual": hj_c})
                        
                        struk_html = buat_tampilan_struk_multi(pilihan_struk_cetak, tgl_c, items_c, status_c)
                        st.markdown(struk_html, unsafe_allow_html=True)
                else:
                    st.info("Belum ada transaksi dengan Nomor Struk otomatis.")

            with subtab_cetak3:
                pilihan_cetak_idx = st.selectbox(
                    "Pilih Baris Transaksi Satuan:",
                    options=df_riwayat_tampil.index.tolist(),
                    format_func=lambda x: f"Baris ke-{x} | Tanggal: {df_riwayat_tampil.loc[x, 'Tanggal']} | Rokok: {df_riwayat_tampil.loc[x, 'Nama Barang']} ({df_riwayat_tampil.loc[x, 'Jumlah Keluar']} {df_riwayat_tampil.loc[x, 'Satuan']}) | Status: {df_riwayat_tampil.loc[x, 'Status']}",
                    key="subtab_select_cetak_satuan"
                )
                
                if st.button("🖨️ Tampilkan Struk Baris Ini", key="btn_cetak_satuan"):
                    tgl_c = df_riwayat_tampil.loc[pilihan_cetak_idx, 'Tanggal']
                    nama_c = df_riwayat_tampil.loc[pilihan_cetak_idx, 'Nama Barang']
                    jml_c = int(df_riwayat_tampil.loc[pilihan_cetak_idx, 'Jumlah Keluar'])
                    satuan_c = df_riwayat_tampil.loc[pilihan_cetak_idx, 'Satuan']
                    status_c = df_riwayat_tampil.loc[pilihan_cetak_idx, 'Status']
                    
                    no_str_c = df_riwayat_tampil.loc[pilihan_cetak_idx, 'No_Struk'] if 'No_Struk' in df_riwayat_tampil.columns else "-"
                    if str(no_str_c) in ["-", "nan", "None", ""]:
                        no_str_c = f"STR-{str(tgl_c).replace('-','')}-{pilihan_cetak_idx}"
                    
                    match_b = df[df["Nama Barang"] == nama_c]
                    h_jual_c = int(match_b.iloc[0]["Harga Jual"]) if not match_b.empty else 0
                    
                    items_c = [{
                        "nama": nama_c,
                        "jml": jml_c,
                        "satuan": satuan_c,
                        "h_jual": h_jual_c
                    }]
                    
                    struk_html = buat_tampilan_struk_multi(no_str_c, tgl_c, items_c, status_c)
                    st.markdown(struk_html, unsafe_allow_html=True)
            
            st.markdown("---")
            st.subheader("💵 Kelola Status Pembayaran (Lunas / Hutang)")
            
            pilihan_status_idx = st.selectbox(
                "Pilih Baris Transaksi yang Ingin Diubah Statusnya:",
                options=df_riwayat_tampil.index.tolist(),
                format_func=lambda x: f"Baris ke-{x} | Tgl: {df_riwayat_tampil.loc[x, 'Tanggal']} | Rokok: {df_riwayat_tampil.loc[x, 'Nama Barang']} ({df_riwayat_tampil.loc[x, 'Jumlah Keluar']} {df_riwayat_tampil.loc[x, 'Satuan']}) | Status Saat Ini: {df_riwayat_tampil.loc[x, 'Status']}",
                key="select_ubah_status_riwayat"
            )
            
            statusBaru = st.radio(
                "Ubah Status Pembayaran Menjadi:",
                ["Tunai (Lunas)", "Hutang (Belum Bayar)"],
                horizontal=True,
                key="radio_ubah_status_baru"
            )
            
            if st.button("🔄 Perbarui Status Pembayaran", type="primary"):
                idx_asli = df_riwayat_tampil.loc[pilihan_status_idx, "_index_asli"]
                st.session_state.riwayat_jual.at[idx_asli, "Status"] = statusBaru
                update_or_delete_riwayat(st.session_state.riwayat_jual)
                st.success(f"Status pembayaran berhasil diubah menjadi: {statusBaru}!")
                st.rerun()
                
            st.markdown("---")
            st.subheader("🗑️ Hapus Baris Riwayat Transaksi")
            st.warning("⚠️ Menghapus riwayat transaksi **TIDAK** otomatis mengembalikan stok fisik.")
            
            pilihan_hapus_idx = st.selectbox(
                "Pilih Baris Riwayat yang Ingin Dihapus:",
                options=df_riwayat_tampil.index.tolist(),
                format_func=lambda x: f"Baris ke-{x} | Tgl: {df_riwayat_tampil.loc[x, 'Tanggal']} | Rokok: {df_riwayat_tampil.loc[x, 'Nama Barang']} ({df_riwayat_tampil.loc[x, 'Jumlah Keluar']} {df_riwayat_tampil.loc[x, 'Satuan']})",
                key="select_hapus_riwayat"
            )
            
            if st.button("❌ Hapus Baris Riwayat Terpilih", type="secondary"):
                idx_asli = df_riwayat_tampil.loc[pilihan_hapus_idx, "_index_asli"]
                df_new = st.session_state.riwayat_jual.drop(index=idx_asli).reset_index(drop=True)
                st.session_state.riwayat_jual = df_new
                update_or_delete_riwayat(df_new)
                st.success("Baris riwayat berhasil dihapus!")
                st.rerun()
        else:
            st.info("Belum ada riwayat transaksi penjualan.")

# ---------------------------------------------------------
# 4. KELOLA MASTER BARANG (TAMBAH BARANG BARU)
# ---------------------------------------------------------
elif fitur == "⚙️ Kelola Master Barang":
    st.title("⚙️ Tambah Barang / Merek Rokok Baru")
    
    with st.form("form_tambah_barang"):
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            kode_barang = st.text_input("Kode Barang (Contoh: R01, R02):")
            nama_barang = st.text_input("Nama Barang / Merek Rokok:")
            kategori_barang = st.text_input("Kategori (Contoh: SKM, SKT, SPM):", value="Rokok")
            satuan_barang = st.text_input("Satuan:", value="Bungkus")
        with c_f2:
            harga_beli = st.number_input("Harga Beli / Modal (Rp):", min_value=0, step=500)
            harga_jual = st.number_input("Harga Jual (Rp):", min_value=0, step=500)
            stok_awal = st.number_input("Stok Awal:", min_value=0, step=1)
            
        submit_barang = st.form_submit_button("💾 Simpan Barang Baru")
        
        if submit_barang:
            if not kode_barang or not nama_barang:
                st.error("Kode Barang dan Nama Barang wajib diisi!")
            elif not df.empty and kode_barang in df["Kode"].values:
                st.error(f"Kode barang '{kode_barang}' sudah ada di database!")
            elif not df.empty and nama_barang in df["Nama Barang"].values:
                st.error(f"Nama barang '{nama_barang}' sudah ada di database!")
            else:
                row_baru = {
                    "Kode": str(kode_barang).strip(),
                    "Nama Barang": str(nama_barang).strip(),
                    "Kategori": str(kategori_barang).strip(),
                    "Harga Beli": int(harga_beli),
                    "Harga Jual": int(harga_jual),
                    "Stok Awal": int(stok_awal),
                    "Total Restok": 0,
                    "Total Keluar": 0,
                    "Satuan": str(satuan_barang).strip()
                }
                
                df_baru = pd.concat([df, pd.DataFrame([row_baru])], ignore_index=True)
                if save_data(df_baru):
                    st.success(f"Berhasil menambahkan barang baru: {nama_barang}!")
                    st.rerun()

# ---------------------------------------------------------
# 5. EDIT / HAPUS BARANG & RESET
# ---------------------------------------------------------
elif fitur == "🛠️ Edit / Hapus Barang & Reset":
    st.title("🛠️ Edit, Hapus Data Barang & Reset Sistem")
    
    tab_edit1, tab_edit2 = st.tabs(["✏️ Edit Harga / Data Barang", "🗑️ Hapus Barang / Reset Data"])
    
    with tab_edit1:
        st.subheader("✏️ Perbarui Harga atau Informasi Rokok")
        if not df.empty and "Nama Barang" in df.columns:
            pilih_edit = st.selectbox("Pilih Barang yang Ingin Diedit:", df["Nama Barang"].tolist(), key="select_edit_brg")
            row_data = df[df["Nama Barang"] == pilih_edit].iloc[0]
            
            with st.form("form_edit_barang"):
                e_kode = st.text_input("Kode Barang:", value=str(row_data["Kode"]))
                e_nama = st.text_input("Nama Barang:", value=str(row_data["Nama Barang"]))
                e_kat = st.text_input("Kategori:", value=str(row_data["Kategori"]))
                e_hbeli = st.number_input("Harga Beli (Rp):", min_value=0, value=int(row_data["Harga Beli"]), step=500)
                e_hjual = st.number_input("Harga Jual (Rp):", min_value=0, value=int(row_data["Harga Jual"]), step=500)
                e_sawal = st.number_input("Stok Awal:", min_value=0, value=int(row_data["Stok Awal"]), step=1)
                e_restok = st.number_input("Total Restok:", min_value=0, value=int(row_data["Total Restok"]), step=1)
                e_keluar = st.number_input("Total Keluar:", min_value=0, value=int(row_data["Total Keluar"]), step=1)
                e_satuan = st.text_input("Satuan:", value=str(row_data["Satuan"]))
                
                btn_update = st.form_submit_button("💾 Perbarui Data Barang")
                
                if btn_update:
                    idx = df[df["Nama Barang"] == pilih_edit].index[0]
                    df.at[idx, "Kode"] = str(e_kode).strip()
                    df.at[idx, "Nama Barang"] = str(e_nama).strip()
                    df.at[idx, "Kategori"] = str(e_kat).strip()
                    df.at[idx, "Harga Beli"] = int(e_hbeli)
                    df.at[idx, "Harga Jual"] = int(e_hjual)
                    df.at[idx, "Stok Awal"] = int(e_sawal)
                    df.at[idx, "Total Restok"] = int(e_restok)
                    df.at[idx, "Total Keluar"] = int(e_keluar)
                    df.at[idx, "Satuan"] = str(e_satuan).strip()
                    
                    if save_data(df[["Kode", "Nama Barang", "Kategori", "Harga Beli", "Harga Jual", "Stok Awal", "Total Restok", "Total Keluar", "Satuan"]]):
                        st.success(f"Data barang '{e_nama}' berhasil diperbarui!")
                        st.rerun()
        else:
            st.warning("Belum ada data barang.")

    with tab_edit2:
        st.subheader("🗑️ Hapus Spesifik Merek Rokok")
        if not df.empty and "Nama Barang" in df.columns:
            pilih_hapus = st.selectbox("Pilih Merek Rokok yang Ingin Dihapus dari Sistem:", df["Nama Barang"].tolist(), key="select_hapus_brg")
            if st.button("❌ Hapus Rokok Ini dari Database", type="secondary"):
                df_filtered = df[df["Nama Barang"] != pilih_hapus].reset_index(drop=True)
                if save_data(df_filtered[["Kode", "Nama Barang", "Kategori", "Harga Beli", "Harga Jual", "Stok Awal", "Total Restok", "Total Keluar", "Satuan"]]):
                    st.success(f"Merek rokok '{pilih_hapus}' berhasil dihapus!")
                    st.rerun()
        
        st.markdown("---")
        st.subheader("⚠️ Zona Bahaya: Reset Seluruh Sistem")
        st.caption("Tombol di bawah ini akan menghapus seluruh database SQLite secara permanen.")
        
        konfirmasi_reset = st.checkbox("Saya mengerti risiko tindakan ini dan ingin mereset total aplikasi")
        if konfirmasi_reset:
            if st.button("🚨 RESET TOTAL SEMUA DATA", type="primary"):
                import os
                if os.path.exists(DB_FILE):
                    os.remove(DB_FILE)
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("Semua data di database berhasil direset! Memuat ulang aplikasi...")
                st.rerun()
