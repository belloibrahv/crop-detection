# AgroScan NG - Current Model Limitations and Implementation Status

## Executive Summary

The current AgroScan NG model (v1) has significant limitations compared to the original requirements. This document outlines the current state, root causes, and recommended next steps.

## Current Model Status (v1)

### Supported Crops and Classes

**Total Classes: 14 (vs 28 required)**

| Crop | Classes Available | Classes Required | Gap |
|------|------------------|------------------|-----|
| **Cassava** | 1 (Healthy only) | 5 | 4 missing |
| **Maize** | 4 (Common Rust, Healthy, Leaf Blight, Leaf Spot) | 6 | 2 missing |
| **Tomato** | 8 (Bacterial Spot, Early Blight, Healthy, Late Blight, Leaf Mould, Mosaic Virus, Septoria Leaf Spot, Yellow Leaf Curl Virus) | 8 | ✅ Complete |
| **Rice** | 1 (Blast only) | 5 | 4 missing |
| **Yam** | 0 | 5 | 5 missing |

### Data Distribution Issues

**Severe Class Imbalance:**
- Tomato Yellow Leaf Curl Virus: 10,714 images
- Cassava Healthy: 302 images
- **Ratio: 35:1** (largest to smallest class)

This imbalance causes the model to be biased toward Tomato classes and perform poorly on underrepresented classes.

### Model Performance

**Training Results:**
- Phase 1 training accuracy: 13-21% (very poor)
- Validation accuracy: Unstable (13-40%)
- **Root Cause:** Severe class imbalance and insufficient training data for many classes

## Root Causes

### 1. Data Availability Issues

**Missing Public Datasets:**
- **Cassava:** Kaggle competition dataset requires special access (403 Forbidden errors)
- **Rice:** Multiple Kaggle datasets blocked by API restrictions
- **Yam:** No public dataset exists (requires local collection)

**Data Quality Issues:**
- CCMT dataset import failed (0 images imported)
- Only PlantVillage dataset successfully downloaded and organized

### 2. Training Pipeline Limitations

The training pipeline is well-configured but cannot compensate for:
- Missing training data for 14/28 required classes
- Severe class imbalance (35:1 ratio)
- Insufficient samples per class for effective learning

## Immediate Fixes Applied

### Frontend Changes
1. ✅ Removed Yam from crop selection dropdown (Diagnose.tsx)
2. ✅ Updated Home page to show only supported crops (Home.tsx)
3. ✅ Added warning banner about current model limitations

### Backend Changes
1. ✅ Added server-side validation to reject unsupported crop types
2. ✅ Returns clear error message when unsupported crop is submitted

## Recommended Next Steps

### Phase 1: Improve Current Model (Short-term)

**Option A: Reduced Scope Implementation**
- Train model on only Tomato + Maize (12 classes, 38,732 images)
- Remove Cassava and Rice from supported crops
- Expected accuracy: 70-85% (reasonable for production)
- Timeline: 2-3 days

**Option B: Balanced Dataset**
- Downsample Tomato classes to ~1,000 images each
- Augment Cassava and Rice classes to match
- Keep all 14 current classes
- Expected accuracy: 60-75%
- Timeline: 1 week

### Phase 2: Complete Dataset Collection (Long-term)

**Cassava Data Collection:**
- Apply for Kaggle competition access
- Alternative: Download from Mendeley Data (requires manual download)
- Target: 5 classes, ~1,000 images each

**Rice Data Collection:**
- Find alternative public sources (not Kaggle)
- Contact research institutions for dataset access
- Target: 5 classes, ~1,000 images each

**Yam Data Collection (Critical):**
- No public source exists
- Must collect local images from Nigerian farms
- Target: 50-100 real images per disease class
- Locations: Ogun State and surrounding areas
- Timeline: 2-3 months (field work required)

### Phase 3: Full Implementation

**Once complete dataset is available:**
1. Retrain model with all 28 classes
2. Achieve ≥93% weighted accuracy (NFR-2 requirement)
3. Update frontend to include all 5 crops
4. Remove limitation warnings
5. Deploy to production

## Current System Capabilities

### What Works Now
- ✅ Tomato disease detection (8 classes, good data)
- ✅ Maize disease detection (4 classes, good data)
- ✅ API inference service operational
- ✅ Frontend diagnosis flow functional
- ✅ Database and persistence working
- ✅ Offline history caching

### What Doesn't Work
- ❌ Yam detection (no training data)
- ❌ Cassava detection (only Healthy class, poor data)
- ❌ Rice detection (only Blast class, poor data)
- ❌ Model accuracy below production threshold (26.8% vs 93% required)

## Recommendations for Production

### Immediate (This Week)
1. **Implement Option A** - Train on Tomato + Maize only
2. Update marketing materials to reflect current capabilities
3. Set user expectations about supported crops
4. Begin Yam data collection planning

### Short-term (Next Month)
1. Acquire Cassava and Rice datasets
2. Train expanded model (14 classes)
3. Achieve 70-80% accuracy threshold
4. Beta testing with farmers

### Long-term (Next Quarter)
1. Complete Yam data collection
2. Train full 28-class model
3. Achieve 93% accuracy requirement
4. Full production deployment

## Data Collection Requirements for Yam

### Target Classes (5)
1. Yam Anthracnose
2. Yam Mosaic Virus
3. Yam Dry Rot
4. Yam Leaf Spot
5. Yam Healthy

### Collection Guidelines
- **Minimum:** 50 real images per class
- **Target:** 100 real images per class
- **Image Quality:** 512x512 pixels minimum
- **Lighting:** Natural daylight, avoid shadows
- **Focus:** Single leaf, clear disease symptoms
- **Background:** Remove or blur background
- **Format:** JPG or PNG

### Collection Locations
- Ogun State agricultural zones
- Partner with local farmers and extension officers
- Use mobile phones with good cameras
- Document GPS coordinates and date

### Augmentation Plan
Once 50-100 real images per class are collected:
1. Apply data augmentation (flip, rotate, color jitter)
2. Generate synthetic images to reach 300 per class
3. Balance with other crop classes
4. Include in training pipeline

## Conclusion

The current system is functional for Tomato and Maize detection but falls short of the original requirements due to data availability issues. The recommended path forward is to:

1. **Deploy limited version** (Tomato + Maize) for immediate value
2. **Collect missing data** systematically (especially Yam)
3. **Expand coverage incrementally** as data becomes available
4. **Achieve full requirements** within 3-6 months

This approach provides immediate utility while working toward the complete solution outlined in the original requirements.
