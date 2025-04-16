#!/bin/bash

# 设置错误处理
set -e

# 检查参数
if [ $# -gt 1 ]; then
    echo "Usage: $0 [version]"
    echo "Example: $0 1.0.0"
    exit 1
fi

VERSION=${1}
CORE_IMAGE="iheytang/openmanus-core:${VERSION}"
WEB_IMAGE="iheytang/openmanus-web:${VERSION}"
ALIYUN_REGISTRY="registry.cn-hangzhou.aliyuncs.com/iheytang"

# Print build information
echo "=============================================="
echo "Starting to build Docker images..."
echo "Core service image: ${CORE_IMAGE}"
echo "Web service image: ${WEB_IMAGE}"
echo "Version: ${VERSION}"
echo "=============================================="

# Build core service image
echo "=============================================="
echo "Building core service image..."
echo "Using Dockerfile: Dockerfile.run_api"
echo "=============================================="
docker build --progress=plain -t ${CORE_IMAGE} -f Dockerfile.run_api .

# Build web service image
echo "=============================================="
echo "Building web service image..."
echo "Using Dockerfile: web/Dockerfile"
echo "=============================================="
docker build --progress=plain -t ${WEB_IMAGE} -f web/Dockerfile web/

# Check build result
if [ $? -eq 0 ]; then
    echo "=============================================="
    echo "Build successful!"
    echo "Core service image: ${CORE_IMAGE}"
    echo "Web service image: ${WEB_IMAGE}"
    echo "Version: ${VERSION}"
    echo "=============================================="

    # Tag and push to Aliyun registry
    echo "=============================================="
    echo "Tagging images for Aliyun registry..."
    echo "=============================================="
    docker tag ${CORE_IMAGE} ${ALIYUN_REGISTRY}/openmanus-core:${VERSION}
    docker tag ${WEB_IMAGE} ${ALIYUN_REGISTRY}/openmanus-web:${VERSION}

    echo "=============================================="
    echo "Images tagged successfully:"
    echo "${ALIYUN_REGISTRY}/openmanus-core:${VERSION}"
    echo "${ALIYUN_REGISTRY}/openmanus-web:${VERSION}"
    echo "=============================================="
else
    echo "=============================================="
    echo "Build failed!"
    echo "=============================================="
    exit 1
fi
