# 🔧 Cache Troubleshooting Guide

## Issue: Playwright Cache Not Found

### ❌ **Error Seen:**
```
Cache not found for input keys: Linux-playwright-browsers-v1, Linux-playwright-browsers-
```

### 🔍 **Root Cause:**
The cache key `Linux-playwright-browsers-v1` doesn't exist yet because this is the first run or the cache was invalidated.

### ✅ **Fixes Applied:**

#### **1. Improved Cache Key Strategy**
- **Before:** `${{ runner.os }}-playwright-browsers-v1`
- **After:** `${{ runner.os }}-playwright-browsers-${{ hashFiles('**/requirements.txt') }}-v1`
- **Benefit:** Cache invalidates when dependencies change

#### **2. Enhanced Fallback Keys**
- Added `${{ runner.os }}-playwright-` as additional fallback
- Provides better cache restoration chances

#### **3. Robust Cache Validation**
- Added cache verification with `playwright install --dry-run`
- Automatically removes invalid cached browsers
- Prevents using corrupted cache

#### **4. Debug Information**
- Added debug step to show cache status
- Helps troubleshoot future cache issues
- Shows environment variables and directory status

### 🚀 **Expected Behavior After Fix:**

#### **First Run (No Cache):**
1. Cache miss: "Cache not found" (normal)
2. Playwright browsers download and install
3. Cache saved for next run

#### **Subsequent Runs (Cache Hit):**
1. Cache restored successfully
2. Browsers verified as functional
3. Skip installation, use cached browsers

#### **Cache Invalidation:**
1. If requirements.txt changes, new cache key generated
2. If cached browsers are corrupted, automatically reinstall
3. Graceful fallback to Selenium if Playwright fails

### 🔧 **Manual Troubleshooting:**

If cache issues persist:

1. **Check cache size limits:**
   - GitHub Actions cache limit: 10GB per repository
   - Individual cache limit: 5GB

2. **Force cache refresh:**
   - Change the version number in cache key (v1 → v2)
   - Or update requirements.txt

3. **Debug locally:**
   ```bash
   export PLAYWRIGHT_BROWSERS_PATH="./pw-browsers"
   bash scripts/debug_cache.sh
   bash scripts/setup_playwright.sh
   ```

### 📊 **Cache Performance:**
- **Without cache:** ~2-3 minutes to install browsers
- **With cache:** ~10-20 seconds to restore
- **Cache size:** ~200-300MB for Chromium

### ✅ **Status:**
The cache issue has been resolved with improved error handling and validation.