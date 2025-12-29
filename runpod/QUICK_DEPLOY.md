# 🚀 Runpod'a Hızlı Deploy - Adım Adım

## ✅ ÖNCEKİ ADIMLAR (Tamamlandı)
- [x] Runpod API Key eklendi
- [x] Docker dosyaları hazır
- [x] GitHub repo var: Tugberkkalay/Doxasense_RnD

---

## 📦 YÖNTEM 1: GitHub Integration (EN KOLAY - ÖNERİLEN)

Runpod direkt GitHub'dan build edebilir!

### Adım 1: Runpod'da Endpoint Oluştur

```
1. https://www.runpod.io/console/serverless
2. "+ New Endpoint" tıkla
3. "Import GitHub Repository" SEÇ (ilk seçenek)
```

### Adım 2: Repository Bilgileri

```
GitHub Repository URL:
  https://github.com/Tugberkkalay/Doxasense_RnD

Branch: main

Dockerfile Path:
  runpod/Dockerfile
```

### Adım 3: GPU Seçimi

```
GPU Type: RTX A4000
Pricing: Spot ($0.25/hr)
```

### Adım 4: Configuration

```
Endpoint Name: doxasense-gpu

Workers:
  Min Workers: 0
  Max Workers: 2

Advanced:
  GPUs per Worker: 1
  Idle Timeout: 30 seconds
  Execution Timeout: 300 seconds
  
Flashboot: ✓ Enable
```

### Adım 5: Deploy

```
"Deploy Endpoint" tıkla

Runpod otomatik:
- GitHub'dan clone edecek
- Docker image build edecek (5-10 dakika)
- Deploy edecek
```

### Adım 6: Endpoint URL Al

```
Deploy tamamlanınca:
Endpoint Details → 

Endpoint ID: xxxxxxxxxx
API URL: https://api.runpod.ai/v2/xxxxxxxxxx

Bu URL'i KOPYALA!
```

### Adım 7: Bana URL Gönder

Endpoint URL'i buraya yapıştır, ben:
- ✅ .env'ye ekleyeceğim
- ✅ Backend restart edeceğim
- ✅ Test edeceğiz!

---

## 📦 YÖNTEM 2: Docker Hub (Manuel Build)

Eğer GitHub integration çalışmazsa:

### Local Makinende:

```bash
# 1. Runpod klasörünü indir
# GitHub'dan veya ZIP olarak

# 2. Build
cd runpod/
docker build --platform linux/amd64 -t tugberkkalay/doxasense-gpu:latest .

# 3. Login
docker login

# 4. Push
docker push tugberkkalay/doxasense-gpu:latest
```

### Runpod'da:

```
1. New Endpoint
2. Import from Docker Registry
3. Image: tugberkkalay/doxasense-gpu:latest
4. Deploy
5. Endpoint URL al
```

---

## 🎯 ŞİMDİ YAPILACAK (5 dakika)

**EN KOLAY YOL - GitHub Integration:**

1. Screenshot'taki Runpod ekranında:
   - "Import GitHub Repository" seç
   
2. Repository:
   ```
   https://github.com/Tugberkkalay/Doxasense_RnD
   ```

3. Dockerfile Path:
   ```
   runpod/Dockerfile
   ```

4. GPU: RTX A4000

5. Deploy!

6. **Endpoint URL'i al ve bana gönder!**

---

## 📝 ENDPOINT URL ÖRNEĞİ

```
https://api.runpod.ai/v2/abc123xyz456def789
```

Bu URL'i alınca ben:
- .env'ye RUNPOD_ENDPOINT ekleyeceğim
- Backend restart edeceğim
- Test upload yapacağız
- GPU'da 15 saniyede işlenecek! 🚀

**Endpoint oluştur ve URL'i bekli yorum! ✨**
