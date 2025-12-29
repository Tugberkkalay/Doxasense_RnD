# RUNPOD SERVERLESS ENDPOINT OLUŞTURMA KILAVUZU

## ⚠️ ÖNEMLİ: Serverless Kullan (GPU Pods değil!)

**Neden Serverless?**
- ✅ Pay-per-use (sadece kullanırken öde)
- ✅ Auto-scaling (çok upload gelirse otomatik scale)
- ✅ Queue ile mükemmel uyum
- ✅ Idle durumda $0 maliyet

**GPU Pods vs Serverless:**
| Özellik | GPU Pods | Serverless (✓ Önerilen) |
|---------|----------|-------------------------|
| Maliyet | $0.25/hour (7/24) = $180/ay | $0.25/hour (sadece işlem sırasında) |
| Idle Cost | $180/ay | $0 |
| Scaling | Manuel | Otomatik |
| Queue | Zor | Mükemmel |
| 100 dosya/gün | $180/ay | ~$5/ay |

---

## 📋 ADIM ADIM SERVERLESS ENDPOINT OLUŞTURMA

### 1. Serverless Sekmesine Git
```
Runpod Console → Sol menü → "Serverless" (🚀 ikonu)
URL: https://www.runpod.io/console/serverless
```

### 2. "New Endpoint" Butonuna Tıkla
Sağ üstteki "+ New Endpoint" butonu

### 3. Template Seç

**Hızlı Başlangıç (Önerilen):**
```
Template: "Transformers" veya "PyTorch 2.1"
(Hazır template, hemen çalışır)
```

**Veya Custom Image (Gelişmiş):**
```
Docker Image: runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel
(Kendi handler'ımızı yükleyeceğiz)
```

### 4. GPU Seç
```
GPU Type: RTX A4000 (16GB)
Pricing: Spot ($0.25/hr) veya On-Demand ($0.34/hr)
```

### 5. Configuration

**Container Configuration:**
```
Container Disk: 20 GB
Container Registry Credentials: (boş bırak - public image)
Environment Variables:
  (Şimdilik boş bırakabilirsin)
```

**Endpoint Configuration:**
```
Name: doxasense-worker
Workers:
  Min: 0 (idle'da 0 worker, maliyet $0)
  Max: 3 (aynı anda max 3 paralel işlem)
GPUs per Worker: 1
Idle Timeout: 30 seconds
Max Jobs per Worker: 1
Scale Type: Queue Delay (önerilen)
```

### 6. Deploy!

"Deploy" butonuna tıkla. 2-3 dakika bekle.

### 7. Endpoint Bilgilerini Al

Deploy sonrası göreceksin:
```
Endpoint ID: xxxxxxxxxxxxxxxxxx
Endpoint URL: https://api.runpod.ai/v2/xxxxxxxxxxxxxxxxxx

Örnek:
https://api.runpod.ai/v2/abc123def456
```

### 8. Bana Endpoint URL'ini Ver

Endpoint URL'i kopyala ve bana gönder. Ben:
- .env dosyasına ekleyeceğim
- Backend'i restart edeceğim
- Test edeceğiz!

---

## 🎯 ENDPOINT URL NASIL BULUNUR?

Deploy sonrası:
1. "Endpoints" listesinde endpoint'ini gör
2. Endpoint'e tıkla
3. "Endpoint URL" kopyala (sağ üstte)

Örnek:
```
https://api.runpod.ai/v2/abc123def456
```

**Bu URL'i bana ver, gerisini ben hallederim! 🚀**

---

## 💡 ŞİMDİLİK YAPILACAK

1. Runpod Console'a git: https://www.runpod.io/console/serverless
2. "+ New Endpoint" tıkla
3. PyTorch template seç
4. A4000 GPU seç
5. Deploy tıkla
6. Endpoint URL'ini kopyala
7. Bana gönder!

Endpoint oluşturduktan sonra URL'i ver, ben hemen entegre edip test ederim! ✅
