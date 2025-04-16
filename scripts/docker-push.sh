#!/bin/bash

set -e

if [ $# -gt 1 ]; then
    echo "Usage: $0 [version]"
    echo "Example: $0 1.0.0"
    exit 1
fi

VERSION=${1}
CORE_IMAGE="iheytang/openmanus-core:${VERSION}"
WEB_IMAGE="iheytang/openmanus-web:${VERSION}"
ALIYUN_REGISTRY="registry.cn-hangzhou.aliyuncs.com/iheytang"

# Print push information
echo "=============================================="
echo "Starting to push Docker images..."
echo "Core service image: ${CORE_IMAGE}"
echo "Web service image: ${WEB_IMAGE}"
echo "Version: ${VERSION}"
echo "=============================================="

# Push to Docker Hub
echo "=============================================="
echo "Pushing to Docker Hub..."
echo "=============================================="
docker push ${CORE_IMAGE}
docker push ${WEB_IMAGE}

# Push to Aliyun registry
echo "=============================================="
echo "Pushing to Aliyun registry..."
echo "=============================================="
docker push ${ALIYUN_REGISTRY}/openmanus-core:${VERSION}
docker push ${ALIYUN_REGISTRY}/openmanus-web:${VERSION}

# Check push result
if [ $? -eq 0 ]; then
    echo "=============================================="
    echo "Push successful!"
    echo "Docker Hub images:"
    echo "- ${CORE_IMAGE}"
    echo "- ${WEB_IMAGE}"
    echo "Aliyun registry images:"
    echo "- ${ALIYUN_REGISTRY}/openmanus-core:${VERSION}"
    echo "- ${ALIYUN_REGISTRY}/openmanus-web:${VERSION}"
    echo "Version: ${VERSION}"
    echo "=============================================="
else
    echo "=============================================="
    echo "Push failed!"
    echo "=============================================="
    exit 1
fi
