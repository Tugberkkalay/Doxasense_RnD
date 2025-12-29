#!/bin/bash
# Runpod GPU Worker Build & Deploy Script

set -e

echo "🚀 DoxaSense GPU Worker - Runpod Deployment"
echo "=========================================="

# Configuration
DOCKER_USERNAME=${1:-"YOUR_DOCKERHUB_USERNAME"}
IMAGE_NAME="doxasense-gpu-worker"
VERSION="latest"

if [ "$DOCKER_USERNAME" = "YOUR_DOCKERHUB_USERNAME" ]; then
    echo "❌ Error: Docker Hub username gerekli!"
    echo ""
    echo "Kullanım:"
    echo "  ./build_and_push.sh YOUR_DOCKERHUB_USERNAME"
    echo ""
    echo "Örnek:"
    echo "  ./build_and_push.sh tugberkkalay"
    exit 1
fi

FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION}"

echo ""
echo "📦 Image: ${FULL_IMAGE_NAME}"
echo ""

# Step 1: Build
echo "1️⃣  Building Docker image..."
echo "   (Bu 20-30 dakika sürebilir - AI modelleri indiriliyor)"
echo ""

docker build -t ${FULL_IMAGE_NAME} .

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo ""
echo "✅ Build successful!"
echo ""

# Step 2: Test locally (optional)
echo "2️⃣  Local test ister misin? (y/n)"
read -t 10 -n 1 TEST_LOCAL || TEST_LOCAL="n"
echo ""

if [ "$TEST_LOCAL" = "y" ]; then
    echo "Testing locally..."
    docker run --rm ${FULL_IMAGE_NAME} python -c "print('✓ Container works!')"
fi

# Step 3: Login to Docker Hub
echo "3️⃣  Docker Hub'a login oluyoruz..."
echo "   Docker Hub şifrenizi girin:"
docker login -u ${DOCKER_USERNAME}

if [ $? -ne 0 ]; then
    echo "❌ Docker Hub login failed!"
    exit 1
fi

# Step 4: Push
echo ""
echo "4️⃣  Pushing to Docker Hub..."
echo "   (Bu 10-15 dakika sürebilir - ~8GB upload)"
echo ""

docker push ${FULL_IMAGE_NAME}

if [ $? -ne 0 ]; then
    echo "❌ Push failed!"
    exit 1
fi

echo ""
echo "🎉 SUCCESS! Image pushed to Docker Hub"
echo ""
echo "=========================================="
echo "📋 SONRAKI ADIMLAR:"
echo "=========================================="
echo ""
echo "1. Runpod Console'a git:"
echo "   https://www.runpod.io/console/serverless"
echo ""
echo "2. 'New Endpoint' → 'Import from Docker Registry'"
echo ""
echo "3. Docker Image gir:"
echo "   ${FULL_IMAGE_NAME}"
echo ""
echo "4. GPU seç: RTX A4000 (16GB)"
echo ""
echo "5. Config:"
echo "   - Min Workers: 0"
echo "   - Max Workers: 2"
echo "   - Idle Timeout: 30s"
echo ""
echo "6. Deploy!"
echo ""
echo "7. Endpoint URL'ini kopyala ve uygulamana ekle:"
echo "   RUNPOD_ENDPOINT=https://api.runpod.ai/v2/YOUR_ENDPOINT_ID"
echo ""
echo "=========================================="
