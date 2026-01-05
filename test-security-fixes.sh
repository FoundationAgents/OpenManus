#!/bin/bash
# Security Fixes Testing Script
# Tests all the dependency updates and security fixes

set -e  # Exit on error

echo "════════════════════════════════════════════════════════"
echo "  Security Fixes Testing Script"
echo "════════════════════════════════════════════════════════"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Root package security audit
echo "📋 Test 1: Root Package Security Audit"
echo "----------------------------------------"
cd /home/user/OpenManus
if npm audit | grep -q "found 0 vulnerabilities"; then
    echo -e "${GREEN}✓ PASSED${NC} - No vulnerabilities in root package"
else
    echo -e "${RED}✗ FAILED${NC} - Vulnerabilities found in root package"
    npm audit
    exit 1
fi
echo ""

# Test 2: Chart visualization security audit
echo "📋 Test 2: Chart Visualization Security Audit"
echo "----------------------------------------"
cd /home/user/OpenManus/app/tool/chart_visualization
if npm audit | grep -q "found 0 vulnerabilities"; then
    echo -e "${GREEN}✓ PASSED${NC} - No vulnerabilities in chart_visualization"
else
    echo -e "${RED}✗ FAILED${NC} - Vulnerabilities found in chart_visualization"
    npm audit
    exit 1
fi
echo ""

# Test 3: Check minimist version
echo "📋 Test 3: Minimist Version Check"
echo "----------------------------------------"
cd /home/user/OpenManus/app/tool/chart_visualization
MINIMIST_VERSION=$(npm ls minimist --depth=999 2>/dev/null | grep minimist@ | head -1 | grep -oP '\d+\.\d+\.\d+')
if [ "$MINIMIST_VERSION" = "1.2.8" ] || [ "$MINIMIST_VERSION" \> "1.2.8" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - minimist is at secure version: $MINIMIST_VERSION"
else
    echo -e "${RED}✗ FAILED${NC} - minimist version is outdated: $MINIMIST_VERSION"
    exit 1
fi
echo ""

# Test 4: Check @visactor/vchart version
echo "📋 Test 4: VChart Version Check"
echo "----------------------------------------"
cd /home/user/OpenManus/app/tool/chart_visualization
VCHART_VERSION=$(npm ls @visactor/vchart --depth=0 2>/dev/null | grep @visactor/vchart@ | grep -oP '\d+\.\d+\.\d+')
if [[ "$VCHART_VERSION" == 2.0.* ]] || [[ "$VCHART_VERSION" > "2.0.11" ]]; then
    echo -e "${GREEN}✓ PASSED${NC} - @visactor/vchart is at v2.x: $VCHART_VERSION"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - @visactor/vchart version unexpected: $VCHART_VERSION"
fi
echo ""

# Test 5: Verify serve is in devDependencies
echo "📋 Test 5: Serve Dependency Location"
echo "----------------------------------------"
cd /home/user/OpenManus
if grep -q '"devDependencies"' package.json && grep -A 3 '"devDependencies"' package.json | grep -q '"serve"'; then
    echo -e "${GREEN}✓ PASSED${NC} - serve is correctly in devDependencies"
else
    echo -e "${RED}✗ FAILED${NC} - serve is not in devDependencies"
    exit 1
fi
echo ""

# Test 6: Check package override is present
echo "📋 Test 6: NPM Overrides Configuration"
echo "----------------------------------------"
cd /home/user/OpenManus/app/tool/chart_visualization
if grep -q '"overrides"' package.json && grep -A 3 '"overrides"' package.json | grep -q '"minimist"'; then
    echo -e "${GREEN}✓ PASSED${NC} - npm overrides configured for minimist"
else
    echo -e "${RED}✗ FAILED${NC} - npm overrides not found in package.json"
    exit 1
fi
echo ""

# Test 7: Dependency count (optional - informational)
echo "📋 Test 7: Dependency Analysis"
echo "----------------------------------------"
cd /home/user/OpenManus
ROOT_DEPS=$(npm ls --depth=0 --dev 2>/dev/null | grep -c "├──\|└──" || echo "0")
echo "Root package dependencies: $ROOT_DEPS (dev-only)"

cd /home/user/OpenManus/app/tool/chart_visualization
CHART_DEPS=$(npm ls --depth=0 2>/dev/null | grep -c "├──\|└──" || echo "0")
echo "Chart visualization dependencies: $CHART_DEPS"
echo -e "${GREEN}✓ INFO${NC} - Dependency analysis complete"
echo ""

# Summary
echo "════════════════════════════════════════════════════════"
echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Test chart visualization functionality manually"
echo "2. Run: npm run dev (to verify local development)"
echo "3. Deploy to staging/preview and verify functionality"
echo ""
