import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import pandas as pd
from collections import defaultdict
import re

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="Web Site Tarayıcı",
    page_icon="🕷️",
    layout="wide"
)

class WebScraper:
    def __init__(self, domain):
        self.domain = domain
        self.base_url = f"https://{domain}" if not domain.startswith('http') else domain
        self.visited_urls = set()
        self.all_links = set()
        self.file_extensions = defaultdict(int)
        
    def is_valid_url(self, url):
        """URL'nin geçerli olup olmadığını kontrol et"""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and bool(parsed.scheme)
        except:
            return False
    
    def is_same_domain(self, url):
        """URL'nin aynı domain'e ait olup olmadığını kontrol et"""
        try:
            parsed_url = urlparse(url)
            parsed_base = urlparse(self.base_url)
            return parsed_url.netloc == parsed_base.netloc or parsed_url.netloc.endswith(f".{parsed_base.netloc}")
        except:
            return False
    
    def get_file_extension(self, url):
        """URL'den dosya uzantısını çıkar"""
        try:
            path = urlparse(url).path
            if '.' in path:
                ext = path.split('.')[-1].lower()
                # Sadece yaygın dosya uzantılarını kabul et
                if len(ext) <= 5 and ext.isalnum():
                    return f".{ext}"
        except:
            pass
        return None
    
    def scrape_page(self, url, max_depth=2, current_depth=0):
        """Sayfayı tara ve linkleri topla"""
        if current_depth > max_depth or url in self.visited_urls:
            return
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            
            self.visited_urls.add(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Tüm linkleri bul
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                full_url = urljoin(url, href)
                
                if self.is_valid_url(full_url) and self.is_same_domain(full_url):
                    self.all_links.add(full_url)
                    
                    # Dosya uzantısını kontrol et
                    ext = self.get_file_extension(full_url)
                    if ext:
                        self.file_extensions[ext] += 1
                    
                    # Recursive tarama (sadece HTML sayfalar için)
                    if not ext and current_depth < max_depth:
                        time.sleep(0.5)  # Rate limiting
                        self.scrape_page(full_url, max_depth, current_depth + 1)
                        
        except Exception as e:
            st.warning(f"Hata: {url} - {str(e)}")
    
    def start_scraping(self, max_depth=2):
        """Taramayı başlat"""
        self.scrape_page(self.base_url, max_depth)
        return self.all_links, self.file_extensions

def main():
    st.title("🕷️ Web Site Tarayıcı")
    st.markdown("Bir web sitesindeki tüm linkleri tarayın ve dosya türlerine göre filtreleyin.")
    
    # Sidebar
    st.sidebar.header("⚙️ Ayarlar")
    
    # Domain input
    domain = st.text_input(
        "🌐 Domain adresini girin:",
        placeholder="example.com veya https://example.com",
        help="Taramak istediğiniz web sitesinin domain adresini girin"
    )
    
    # Tarama derinliği
    max_depth = st.sidebar.slider("📊 Tarama Derinliği", 1, 3, 2)
    
    if domain:
        if st.button("🚀 Taramayı Başlat", type="primary"):
            with st.spinner("Site taranıyor... Bu işlem biraz zaman alabilir."):
                try:
                    scraper = WebScraper(domain)
                    all_links, file_extensions = scraper.start_scraping(max_depth)
                    
                    if all_links:
                        st.success(f"✅ Tarama tamamlandı! {len(all_links)} link bulundu.")
                        
                        # Dosya uzantıları seçimi
                        st.subheader("📁 Dosya Türü Filtreleme")
                        
                        if file_extensions:
                            st.write("Bulunan dosya türleri:")
                            
                            # Checkbox'lar için kolonlar
                            cols = st.columns(4)
                            selected_extensions = []
                            
                            for i, (ext, count) in enumerate(file_extensions.items()):
                                with cols[i % 4]:
                                    if st.checkbox(f"{ext} ({count})", value=True):
                                        selected_extensions.append(ext)
                        else:
                            selected_extensions = []
                            st.info("Özel dosya türü bulunamadı.")
                        
                        # HTML sayfaları da dahil et seçeneği
                        include_html = st.checkbox("📄 HTML sayfalarını dahil et", value=True)
                        
                        # Sonuçları filtrele
                        filtered_links = []
                        for link in all_links:
                            ext = scraper.get_file_extension(link)
                            
                            if ext and ext in selected_extensions:
                                filtered_links.append(link)
                            elif not ext and include_html:
                                filtered_links.append(link)
                        
                        # Sonuçları göster
                        st.subheader("🔗 Bulunan Linkler")
                        st.write(f"Toplam: {len(filtered_links)} link")
                        
                        if filtered_links:
                            # DataFrame oluştur
                            df_data = []
                            for link in filtered_links:
                                ext = scraper.get_file_extension(link) or "HTML"
                                df_data.append({"URL": link, "Tür": ext})
                            
                            df = pd.DataFrame(df_data)
                            
                            # Tablo göster
                            st.dataframe(df, use_container_width=True)
                            
                            # İndirme butonu
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 CSV olarak indir",
                                data=csv,
                                file_name=f"{domain}_links.csv",
                                mime="text/csv"
                            )
                        else:
                            st.warning("Seçilen kriterlere uygun link bulunamadı.")
                    
                    else:
                        st.error("❌ Hiç link bulunamadı. Domain adresini kontrol edin.")
                        
                except Exception as e:
                    st.error(f"❌ Hata oluştu: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown("💡 **İpucu:** Büyük siteler için tarama uzun sürebilir. Sabırlı olun!")

if __name__ == "__main__":

    main()
