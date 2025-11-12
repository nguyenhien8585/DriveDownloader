import streamlit as st
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import io
import re
import os
import time
from pathlib import Path
import threading

# ============= CẤU HÌNH =============
st.set_page_config(
    page_title="📥 Download Drive - nguyenhien",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============= CUSTOM CSS =============
st.markdown("""
<style>
    /* Main theme */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Card style */
    .css-1r6slb0 {
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Header */
    .main-header {
        background: linear-gradient(90deg, #2196F3 0%, #21CBF3 100%);
        padding: 30px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(33, 150, 243, 0.3);
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5em;
        margin: 0;
        font-weight: 700;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1em;
        margin: 10px 0 0 0;
    }
    
    /* Success/Error messages */
    .success-box {
        background: #d4edda;
        border-left: 5px solid #28a745;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .error-box {
        background: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .info-box {
        background: #d1ecf1;
        border-left: 5px solid #17a2b8;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    /* Log container */
    .log-container {
        background: #f8f9fa;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        max-height: 400px;
        overflow-y: auto;
    }
    
    /* Stats card */
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .stat-value {
        font-size: 2em;
        font-weight: bold;
        color: #2196F3;
    }
    
    .stat-label {
        color: #666;
        font-size: 0.9em;
        margin-top: 5px;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 8px;
        font-weight: 600;
        font-size: 16px;
        padding: 12px 24px;
        transition: all 0.3s;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# ============= SESSION STATE =============
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'is_downloading' not in st.session_state:
    st.session_state.is_downloading = False
if 'download_stats' not in st.session_state:
    st.session_state.download_stats = {
        'total': 0,
        'completed': 0,
        'failed': 0,
        'progress': 0
    }

# ============= HELPER FUNCTIONS =============

def add_log(message):
    """Thêm log vào session state"""
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")

def sanitize_path(path_str):
    """Làm sạch đường dẫn file"""
    invalid_chars = r'[:*?"<>|\\[\]]'
    sanitized = re.sub(invalid_chars, '_', path_str)
    parts = re.split(r'[/\\]', sanitized)
    cleaned_parts = [part.strip() for part in parts if part.strip()]
    if not cleaned_parts:
        return "default_file"
    return os.path.join(*cleaned_parts)

def download_from_freezone(drive_path, url, base_save_dir):
    """Download file từ freezone.sbs"""
    original_drive_path = drive_path
    safe_drive_path = sanitize_path(drive_path)
    
    try:
        # Tạo đường dẫn đầy đủ
        full_filepath = os.path.join(base_save_dir, safe_drive_path)
        directory = os.path.dirname(full_filepath)
        
        # Tạo thư mục
        os.makedirs(directory, exist_ok=True)
        
        if original_drive_path != safe_drive_path:
            add_log(f'⚠️ Đã sửa đường dẫn: "{original_drive_path}" → "{safe_drive_path}"')
        
        add_log(f'🔄 Đang xử lý: {original_drive_path}')
        
        # Gửi request đến freezone
        session = requests.Session()
        resp = session.post(
            'https://tools.freezone.sbs/docs/index.php',
            data={'q': url},
            timeout=30
        )
        resp.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(resp.text, 'html.parser')
        download_tag = soup.find('a', class_='download')
        
        if not download_tag or not download_tag.get('href'):
            add_log(f'❌ Không tìm thấy link: {original_drive_path}')
            return (original_drive_path, url)
        
        download_link = download_tag.get('href')
        add_log(f'⬇️ Đang tải: {original_drive_path}')
        
        # Download file
        download_resp = session.get(download_link, stream=True, timeout=60)
        download_resp.raise_for_status()
        
        with open(full_filepath, 'wb') as f:
            for chunk in download_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        add_log(f'✅ Hoàn thành: {original_drive_path}')
        return None
        
    except Exception as e:
        add_log(f'❌ Lỗi: {original_drive_path} - {str(e)}')
        return (original_drive_path, url)

def read_links_from_string(tsv_content):
    """Đọc links từ TSV content"""
    links_with_paths = []
    f = io.StringIO(tsv_content)
    reader = csv.reader(f, delimiter='\t')
    
    for i, row in enumerate(reader, 1):
        try:
            if len(row) >= 2:
                path = row[-2].strip()
                link = row[-1].strip()
                if path and link.startswith('http'):
                    links_with_paths.append((path, link))
        except IndexError as e:
            add_log(f'⚠️ Dòng {i} bị lỗi format, bỏ qua: {str(e)}')
            continue
    
    return links_with_paths

def write_failed_links(failed_list, base_save_dir):
    """Ghi các link thất bại vào file"""
    if failed_list:
        try:
            failed_file = os.path.join(base_save_dir, 'failed_links.tsv')
            with open(failed_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter='\t')
                for path, link in failed_list:
                    writer.writerow([path, link])
            add_log(f'📝 Đã ghi {len(failed_list)} link thất bại vào: failed_links.tsv')
        except Exception as e:
            add_log(f'❌ Lỗi ghi file failed_links: {str(e)}')

def download_batch_multithread(tsv_content, base_save_dir, max_workers):
    """Download batch với multi-threading"""
    links_with_paths = read_links_from_string(tsv_content)
    
    if not links_with_paths:
        add_log('❌ Không có link hợp lệ')
        return
    
    add_log(f'📋 Tìm thấy {len(links_with_paths)} link')
    add_log(f'⚙️ Sử dụng {max_workers} luồng')
    add_log('-' * 50)
    
    # Update stats
    st.session_state.download_stats['total'] = len(links_with_paths)
    st.session_state.download_stats['completed'] = 0
    st.session_state.download_stats['failed'] = 0
    
    failed_downloads = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_link = {
            executor.submit(download_from_freezone, path, link, base_save_dir): (path, link)
            for path, link in links_with_paths
        }
        
        for future in as_completed(future_to_link):
            try:
                result = future.result()
                if result:
                    failed_downloads.append(result)
                    st.session_state.download_stats['failed'] += 1
                else:
                    st.session_state.download_stats['completed'] += 1
                
                # Update progress
                completed = st.session_state.download_stats['completed'] + st.session_state.download_stats['failed']
                st.session_state.download_stats['progress'] = completed / len(links_with_paths)
                
                add_log(f'📊 Tiến độ: {completed}/{len(links_with_paths)}')
                
            except Exception as e:
                add_log(f'❌ Lỗi không mong đợi: {str(e)}')
                st.session_state.download_stats['failed'] += 1
    
    add_log('-' * 50)
    add_log(f'✅ Hoàn thành: {st.session_state.download_stats["completed"]}/{len(links_with_paths)}')
    
    if failed_downloads:
        add_log(f'❌ Thất bại: {len(failed_downloads)}')
        write_failed_links(failed_downloads, base_save_dir)
    else:
        add_log('🎉 Tất cả đã tải xong!')
    
    st.session_state.is_downloading = False

def start_download_thread(tsv_content, base_save_dir, max_workers):
    """Bắt đầu download trong thread riêng"""
    st.session_state.is_downloading = True
    st.session_state.logs = []
    
    thread = threading.Thread(
        target=download_batch_multithread,
        args=(tsv_content, base_save_dir, max_workers)
    )
    thread.daemon = True
    thread.start()

# ============= MAIN UI =============

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📥 DOWNLOAD DRIVE</h1>
        <p>Công cụ tải file từ Google Drive - by nguyenhien</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar - Configuration
    with st.sidebar:
        st.markdown("### ⚙️ Cấu hình")
        
        # Thư mục lưu
        save_dir = st.text_input(
            "📁 Thư mục lưu file",
            value="TaiLieuDrive",
            help="Nhập tên thư mục hoặc đường dẫn đầy đủ"
        )
        
        # Số luồng
        max_workers = st.slider(
            "🔄 Số luồng download",
            min_value=1,
            max_value=20,
            value=5,
            help="Số luồng song song (càng nhiều càng nhanh nhưng tốn tài nguyên)"
        )
        
        st.markdown("---")
        
        # Stats
        if st.session_state.download_stats['total'] > 0:
            st.markdown("### 📊 Thống kê")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "✅ Hoàn thành",
                    st.session_state.download_stats['completed']
                )
            with col2:
                st.metric(
                    "❌ Thất bại",
                    st.session_state.download_stats['failed']
                )
            
            st.metric(
                "📋 Tổng số",
                st.session_state.download_stats['total']
            )
            
            # Progress bar
            st.progress(st.session_state.download_stats['progress'])
        
        st.markdown("---")
        
        # Info
        st.markdown("""
        ### 💡 Hướng dẫn
        
        1. **Copy TSV từ Google Sheets**
           - Chọn cột chứa đường dẫn và link
           - Copy (Ctrl+C)
        
        2. **Paste vào ô bên phải**
           - Format: `Đường dẫn [TAB] Link`
        
        3. **Nhấn "Bắt đầu tải"**
        
        4. **Đợi hoàn thành**
           - File lỗi sẽ được lưu vào `failed_links.tsv`
        """)
        
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 0.9em;'>
            <p>📱 Zalo: 0325511366</p>
            <p>Made with ❤️ by nguyenhien</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Main content
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # TSV Input
        st.markdown("### 📝 Nội dung TSV")
        st.markdown("""
        <div class="info-box">
            💡 Dán nội dung TSV từ Google Sheets vào đây (chứa đường dẫn và link Drive)
        </div>
        """, unsafe_allow_html=True)
        
        tsv_content = st.text_area(
            "",
            height=300,
            placeholder="Dán TSV vào đây...\n\nVí dụ:\nĐường dẫn 1\thttps://drive.google.com/...\nĐường dẫn 2\thttps://drive.google.com/...",
            label_visibility="collapsed"
        )
        
        # Download button
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.session_state.is_downloading:
                st.button(
                    "⏳ Đang tải xuống...",
                    disabled=True,
                    use_container_width=True,
                    type="primary"
                )
            else:
                if st.button(
                    "🚀 BẮT ĐẦU TẢI",
                    use_container_width=True,
                    type="primary"
                ):
                    if not tsv_content.strip() or not save_dir.strip():
                        st.error("⚠️ Vui lòng nhập đầy đủ thông tin!")
                    else:
                        # Tạo thư mục nếu chưa có
                        os.makedirs(save_dir, exist_ok=True)
                        start_download_thread(tsv_content, save_dir, max_workers)
                        st.rerun()
    
    with col2:
        # Log display
        st.markdown("### 📊 Tiến trình")
        
        log_container = st.container()
        with log_container:
            if st.session_state.logs:
                log_text = "\n".join(st.session_state.logs[-50:])  # Show last 50 logs
                st.markdown(f"""
                <div class="log-container">
                    <pre>{log_text}</pre>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("📝 Chưa có log. Nhấn 'Bắt đầu tải' để bắt đầu.")
        
        # Auto refresh when downloading
        if st.session_state.is_downloading:
            time.sleep(1)
            st.rerun()
    
    # Success message
    if not st.session_state.is_downloading and st.session_state.download_stats['total'] > 0:
        if st.session_state.download_stats['failed'] == 0:
            st.balloons()
            st.success("🎉 Tất cả file đã được tải xuống thành công!")
        else:
            st.warning(f"⚠️ Đã hoàn thành với {st.session_state.download_stats['failed']} file lỗi. Xem file `failed_links.tsv` để retry.")

if __name__ == '__main__':
    main()
