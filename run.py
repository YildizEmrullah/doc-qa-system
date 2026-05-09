"""
DocuAsk - Uygulama Başlatıcı
Çalıştırmak için: python run.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,          # Geliştirme modunda otomatik yenileme
        log_level="info",
        access_log=True
    )
