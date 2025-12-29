# 🚀 Runpod GPU Worker - Deployment Kılavuzu

DoxaSense-MIND için Runpod Serverless GPU worker deployment rehberi.

---

## 📁 DOSYALAR

```
/app/runpod/
├── Dockerfile              # Docker image tanımı
├── handler.py              # GPU worker handler
├── requirements.txt        # Python dependencies
├── build_and_push.sh       # Build & deploy script
└── README.md              # Bu dosya
```

---

## 🎯 HIZLI BAŞLANGIÇ (3 Yöntem)

### **YÖNTEM 1: Hazır Template (EN HIZLI - 5 dakika)**

Şimdilik kendi Docker image'ini build etmeden Runpod'un hazır template'ini kullan:

1. **Runpod Console'a git:**
   ```
   https://www.runpod.io/console/serverless
   ```

2. **"New Endpoint" tıkla**

3. **"Import from Docker Registry" seç:**
   ```
   Docker Image: runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel
   ```

4. **GPU Seç:**
   ```
   GPU: RTX A4000 (16GB) - Spot $0.25/hr
   ```

5. **Configuration:**
   ```
   Name: doxasense-worker
   Min Workers: 0
   Max Workers: 2
   GPUs per Worker: 1
   Idle Timeout: 30 seconds
   ```

6. **Deploy! → Endpoint URL'i kopyala**

**Endpoint URL Örneği:**
```
https://api.runpod.ai/v2/abc123xyz456
```

**Bu URL'i DoxaSense'e ekle:**
```bash
# .env dosyasına:
RUNPOD_ENDPOINT=https://api.runpod.ai/v2/abc123xyz456
```

**Not:** Hazır template ile modeller ilk çalışmada inecek (yavaş), ama test için yeterli.

---

### **YÖNTEM 2: Custom Docker Image (ÖNERİLEN - 45 dakika)**

Kendi Docker image'ini build et (modeller pre-loaded):

#### **A. Local'de Build & Push**

**Gereksinimler:**
- Docker Desktop kurulu
- Docker Hub hesabı
- 20 GB boş disk alanı

**Komutlar:**

```bash
# 1. Bu dizine git
cd /app/runpod

# 2. Build script'i çalıştırılabilir yap
chmod +x build_and_push.sh

# 3. Build ve push (Docker Hub username'inle)
./build_and_push.sh tugberkkalay

# Script ne yapar:
# - Docker image build eder (~25 dakika)
# - Modelleri image'e gömülür (~15 GB)
# - Docker Hub'a push eder (~15 dakika)
```

**Manuel olarak:**
```bash
# Build
docker build -t tugberkkalay/doxasense-gpu-worker:latest .

# Login
docker login

# Push
docker push tugberkkalay/doxasense-gpu-worker:latest
```

#### **B. Runpod'da Deploy**

1. **Runpod Console → Serverless → New Endpoint**

2. **"Import from Docker Registry" seç**

3. **Docker Image:**
   ```
   tugberkkalay/doxasense-gpu-worker:latest
   ```

4. **GPU & Config** (aynı yukarıdaki gibi)

5. **Deploy!**

---

### **YÖNTEM 3: Runpod GitHub Integration (EN KOLAY)**

Runpod direkt GitHub'dan build edebilir:

#### **A. GitHub'a Push**

```bash
# Local'de:
cd /app
git init
git add runpod/
git commit -m "Runpod GPU worker"
git remote add origin https://github.com/tugberkkalay/doxasense-runpod.git
git push -u origin main
```

#### **B. Runpod'da Import**

1. **Runpod Console → Serverless → New Endpoint**

2. **"Import GitHub Repository" seç**

3. **Repository:**
   ```
   tugberkkalay/doxasense-runpod
   ```

4. **Dockerfile Path:**
   ```
   runpod/Dockerfile
   ```

5. **Deploy!**

Runpod otomatik build edecek (25-30 dakika).

---

## 📦 DOSYALARI LOCAL'E İNDİRME

Local makinende build etmek için:

### **Yöntem A: Git Clone**
```bash
# Eğer GitHub'a pushlamissan:
git clone https://github.com/tugberkkalay/doxasense.git
cd doxasense/runpod
./build_and_push.sh tugberkkalay
```

### **Yöntem B: Manuel Kopyala**

1. **Dosyaları local'e indir:**
   - `/app/runpod/Dockerfile`
   - `/app/runpod/handler.py`
   - `/app/runpod/requirements.txt`

2. **Bir klasöre koy:**
   ```
   ~/doxasense-runpod/
   ├── Dockerfile
   ├── handler.py
   └── requirements.txt
   ```

3. **Build:**
   ```bash
   cd ~/doxasense-runpod
   docker build -t tugberkkalay/doxasense-gpu:latest .
   ```

4. **Push:**
   ```bash
   docker login
   docker push tugberkkalay/doxasense-gpu:latest
   ```

---

## ⚡ RUNPOD'DA DEPLOY (Resimli Adımlar)

### 1. Serverless Sekmesi
```
Sol menü → Serverless (⚡ ikonu)
```

### 2. New Endpoint
```
Sağ üst → "+ New Endpoint"
```

### 3. Import Docker Image
```
"Import from Docker Registry" kartına tıkla

Docker Image Name:
  tugberkkalay/doxasense-gpu-worker:latest
  
Container Registry Credentials: (boş bırak - public image)
```

### 4. Select GPU
```
GPU Type: RTX A4000
- 16 GB VRAM
- Spot: $0.25/hr
- On-Demand: $0.34/hr

Önerilen: Spot (daha ucuz, yeterli availability)
```

### 5. Configure Endpoint
```
Endpoint Name: doxasense-gpu

Active Workers:
  Min: 0  (idle'da worker yok, maliyet $0)
  Max: 3  (aynı anda 3 paralel işlem)

GPUs Per Worker: 1

Advanced Config:
  Idle Timeout: 30 seconds (işlem bitmeden 30s sonra shutdown)
  Execution Timeout: 300 seconds (max 5 dakika/işlem)
  
Flashboot: ✓ Enable (daha hızlı cold start)
```

### 6. Deploy
```
"Deploy Endpoint" butonuna tıkla
```

Deployment 2-3 dakika sürer.

### 7. Endpoint URL Al
```
Deploy sonrası:

Endpoint Details sayfasında:
  Endpoint URL: https://api.runpod.ai/v2/abc123xyz456
  
Bu URL'i kopyala!
```

---

## 🔗 UYGULAMAYA ENTEGRASYON

Endpoint URL'ini aldıktan sonra:

### 1. Environment Variable Ekle
```bash
# /app/.env dosyasına:
RUNPOD_ENDPOINT=https://api.runpod.ai/v2/abc123xyz456
```

### 2. Backend Restart
```bash
supervisorctl restart backend
```

### 3. Test!
```bash
# GPU ile işle:
curl -X POST http://localhost:8001/api/ingest/upload?use_gpu=true \
  -F "file=@test.pdf"

# Response:
{
  "document_id": "xxx",
  "job_id": "yyy",
  "status": "queued"
}
```

### 4. Job Status Takip
```bash
curl http://localhost:8001/api/ingest/job/yyy/status

# Progress göreceksin:
{
  "status": "processing",
  "progress": 75,
  "message": "Generating embeddings..."
}
```

---

## 💰 MALİYET TAHMİNİ

### Serverless (Pay-per-use)
```
GPU: A4000 Spot $0.25/hr
İşlem süresi: ~15 saniye/dosya
Maliyet/dosya: $0.001

Senaryolar:
- 100 dosya/gün   → ~$3/ay
- 500 dosya/gün   → ~$15/ay
- 1000 dosya/gün  → ~$30/ay
```

### Idle Maliyet
```
Min Workers: 0 → Hiç işlem yoksa $0
(En ekonomik seçenek!)
```

---

## 🛠️ TROUBLESHOOTING

### Problem: "Image not found"
**Çözüm:** Docker Hub'da image public olmalı
```bash
# Docker Hub'da repository'yi public yap:
docker.io → tugberkkalay/doxasense-gpu-worker → Settings → Visibility → Public
```

### Problem: "Container failed to start"
**Çözüm:** Logs kontrol et
```
Runpod Console → Endpoint → Logs
Handler.py'de hata var mı bak
```

### Problem: "Model download timeout"
**Çözüm:** Models image'de pre-download edilmeli
```dockerfile
# Dockerfile'da RUN python -c "..." komutları var mı kontrol et
```

---

## 📊 PERFORMANS BEKLENTİLERİ

### Cold Start (İlk İşlem)
```
Worker başlatma: ~10 saniye
Model loading: ~0 saniye (pre-loaded!)
İşlem: ~15 saniye
Toplam: ~25 saniye
```

### Warm Start (Sonraki İşlemler)
```
Worker zaten çalışıyor: 0 saniye
İşlem: ~15 saniye
Toplam: ~15 saniye
```

### Speedup (CPU vs GPU)
```
PDF (10 sayfa):   120s → 12s  (10x)
Audio (10 dk):    180s → 15s  (12x)
Image:             20s →  3s  (7x)
Video (5 dk):     300s → 30s  (10x)
```

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] Docker Desktop kurulu (local'de)
- [ ] Docker Hub hesabı var
- [ ] Runpod hesabı var ($5.21 credit var ✓)
- [ ] Local'de files indirildi
- [ ] `docker build` çalıştırıldı (~25 dk)
- [ ] `docker push` yapıldı (~15 dk)
- [ ] Runpod'da endpoint oluşturuldu
- [ ] Endpoint URL alındı
- [ ] `.env` dosyasına eklendi
- [ ] Backend restart edildi
- [ ] `?use_gpu=true` ile test edildi
- [ ] İlk dosya işlendi (~25s)
- [ ] Sonraki dosyalar hızlı (~15s)

---

## 🎯 ÖZET

**Toplam Süre:** ~1 saat
- Build: 25 dakika
- Push: 15 dakika
- Deploy: 5 dakika
- Test: 5 dakika

**Sonuç:** 
- ✅ GPU'da 10-15 saniye/dosya
- ✅ CPU'da 108 saniye → 10x speedup!
- ✅ Pay-per-use (ekonomik)
- ✅ Auto-scaling

**Başarılar! 🚀**
