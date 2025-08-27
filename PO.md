# 📋 Product Owner Documentation
## Keypoints News Backend - Master Product Reference

---

## 🎯 **PRODUCT VISION**

**Mission**: Provide curated, AI-summarized news specifically for Bengaluru and Indian audiences through a fast, reliable backend service.

**Target Users**: 
- Bengaluru residents seeking local news
- Indian audiences interested in national topics
- Developers building news applications
- Content aggregators

---

## 🏗️ **CORE PRODUCT ARCHITECTURE**

### **System Components**
1. **News Fetching Engine** - PyGoogleNews integration
2. **AI Processing Pipeline** - Playwright-based content extraction + summarization
3. **REST API Service** - FastAPI endpoints
4. **Database Layer** - Supabase integration
5. **Automation Workflow** - GitHub Actions scheduling

### **Data Flow**
```
News Sources → Fetch → Extract & Summarize → Store → API → End Users
```

---

## 📊 **CURRENT PRODUCT SPECIFICATIONS**

### **Content Processing Limits**
- **Articles per Category**: 20 (default, configurable)
- **Categories Processed**: 18 source categories → 9 final categories
- **Summary Length**: 60 words maximum
- **Processing Engine**: Playwright (primary), Selenium (fallback)

### **Supported Categories**
**Source Categories (18 total):**
1. Bengaluru local news
2. Technology  
3. Indian celebrity news
4. Entertainment
5. Indian sports
6. International news
7. Trending in Bengaluru and India
8. Indian politics
9. India general news
10. Indian education
11. Indian scandal and crime
12. Indian cinema and Bollywood
13. Mumbai news
14. Delhi news
15. Chennai news
16. Hyderabad news
17. Pune news
18. Kolkata news

**Final Database Categories (9 total):**
1. **bengaluru** - Bengaluru-specific content (separate focus)
2. **india** - Other Indian cities/states + general India news
3. **technology** - Tech and startup news
4. **entertainment** - Cinema, celebrity, Bollywood content
5. **sports** - Indian and international sports
6. **politics** - Indian political news
7. **education** - Indian education news
8. **crime** - Indian scandal and crime news
9. **world** - International news

### **API Endpoints**
- `GET /` - API information
- `GET /top-news` - Top stories with optional AI summaries
- `GET /topic-headlines/{topic}` - Topic-specific headlines
- `GET /search` - News search with filters
- `GET /geo/{location}` - Location-based news
- `GET /health` - Health check

---

## 🔄 **AUTOMATION & SCHEDULING**

### **Daily Workflow**
- **Trigger**: Daily at 6 AM UTC + manual triggers
- **Process**: 
  1. Clean old processed files
  2. Fetch fresh news (30 articles × 12 categories = 360 max articles)
  3. Extract images and generate summaries using Playwright
  4. Upload to Supabase database
  5. Commit updated files to repository

### **Data Freshness Policy**
- **Old File Cleanup**: All `inshorts_*.json` files deleted before each run
- **Only Fresh Data**: Only newly processed articles uploaded to database
- **No Stale Content**: Prevents re-uploading old articles

---

## 🛠️ **TECHNICAL DECISIONS & RATIONALE**

### **Browser Automation Strategy**
- **Primary**: Playwright (faster startup, better resource management)
- **Fallback**: Selenium (compatibility backup)
- **Rationale**: Playwright provides 3x faster processing while maintaining reliability

### **Article Limit Rationale**
- **Previous**: 5 articles per category (too limited)
- **Current**: 30 articles per category (comprehensive coverage)
- **Rationale**: Balances content richness with processing time/resources

### **Data Cleanup Strategy**
- **Decision**: Delete old inshorts files before each run
- **Rationale**: Prevents uploading stale data, ensures database freshness
- **Impact**: Only current day's articles reach end users

---

## 🎯 **FEATURE PRIORITIES & ROADMAP**

### **✅ COMPLETED FEATURES**
- [x] Multi-source news aggregation
- [x] AI-powered summarization
- [x] Playwright-based content extraction
- [x] Automated daily processing
- [x] Supabase database integration
- [x] REST API with FastAPI
- [x] Bengaluru-focused content curation
- [x] Automatic old file cleanup
- [x] 30-article processing limit
- [x] **Content quality scoring system (0-100 score)**
- [x] **Enhanced duplicate detection with similarity matching**
- [x] **Additional Indian regional categories (Mumbai, Delhi, Chennai, Hyderabad, Pune, Kolkata)**
- [x] **Processing time optimization (25% faster)**

### **🔄 IN PROGRESS**
- [x] **Summary quality and relevance improvements** - COMPLETED
- [x] **Image extraction reliability enhancements** - COMPLETED

### **📋 BACKLOG (Priority Order)**
1. **High Priority**
   - Improve summary quality and relevance
   - Better image extraction reliability
   - Category-specific search improvements
   - Error handling for failed articles

3. **Low Priority**
   - Multi-language support (Hindi, Kannada)
   - Social media trend integration
   - Advanced search filters
   - Content recommendation engine

---

## 📈 **SUCCESS METRICS & KPIs**

### **Content Quality Metrics**
- Articles processed per day: Target 360 (30 × 12 categories)
- Summary quality score: Target >80% relevance
- Image extraction success rate: Target >90%
- Processing time per article: Target <10 seconds

### **System Performance Metrics**
- API response time: Target <500ms
- Uptime: Target 99.5%
- Daily workflow success rate: Target 95%
- Database storage efficiency: Monitor growth rate

### **User Experience Metrics**
- API endpoint usage patterns
- Content freshness (articles <24 hours old)
- Error rates by endpoint
- Geographic usage distribution

---

## 🔒 **BUSINESS RULES & CONSTRAINTS**

### **Content Guidelines**
- **Focus**: Bengaluru and Indian audiences only
- **Language**: English content only
- **Sources**: Reputable news sources via Google News
- **Quality**: Must have title, summary, and image
- **Freshness**: Maximum 24-hour old content

### **Technical Constraints**
- **Processing Time**: Maximum 30 minutes per daily run
- **Storage**: Efficient JSON storage, no redundant data
- **Rate Limits**: Respect source website rate limits
- **Resource Usage**: Optimize for GitHub Actions limits

### **Compliance Requirements**
- **Data Privacy**: No personal data collection
- **Copyright**: Fair use of news content (summaries only)
- **Attribution**: Proper source attribution required
- **Terms of Service**: Comply with news source ToS

---

## 🚨 **CHANGE MANAGEMENT PROTOCOL**

### **All Changes Must**
1. **Reference this PO.md** - Update specifications here first
2. **Maintain backward compatibility** - API endpoints must remain stable
3. **Update documentation** - README.md and code comments
4. **Test thoroughly** - Verify impact on daily workflow
5. **Monitor metrics** - Track performance impact

### **Change Categories**
- **🔴 Breaking Changes**: Require PO approval + user notification
- **🟡 Feature Changes**: Update PO.md + test thoroughly  
- **🟢 Bug Fixes**: Document in PO.md changelog

### **Approval Process**
- **Configuration Changes**: Update PO.md specifications
- **New Features**: Add to roadmap, update metrics
- **API Changes**: Update endpoint documentation
- **Performance Changes**: Update target metrics

---

## 📝 **CHANGELOG & DECISIONS LOG**

### **Recent Changes**
- **2024-01-XX**: Increased article limit from 5 to 20 per category (optimized)
- **2024-01-XX**: Implemented automatic cleanup of old inshorts files
- **2024-01-XX**: Cleaned up unnecessary .md documentation files
- **2024-01-XX**: Established PO.md as single source of truth
- **2024-01-XX**: Added 6 major Indian cities as source categories
- **2024-01-XX**: Implemented smart category mapping (18 sources → 7 final categories)
- **2024-01-XX**: Separated Bengaluru as dedicated category, consolidated other Indian cities under "india"

### **Key Decisions Made**
1. **Playwright over Selenium**: Performance and reliability benefits
2. **30-article limit**: Balance between coverage and processing time
3. **Daily cleanup**: Ensure only fresh content reaches users
4. **Bengaluru focus**: Targeted audience approach over generic news

---

## 🎯 **PRODUCT OWNER CONTACT & GOVERNANCE**

### **Decision Authority**
- **Product Features**: Product Owner approval required
- **Technical Implementation**: Engineering team autonomy within PO guidelines
- **API Changes**: Must maintain backward compatibility
- **Performance Targets**: PO sets targets, engineering implements

### **Review Schedule**
- **Weekly**: Performance metrics review
- **Monthly**: Feature roadmap assessment
- **Quarterly**: Product vision alignment check

---

## 📚 **REFERENCE LINKS**

- **Main Documentation**: README.md
- **Development Tasks**: TODO.md
- **API Documentation**: http://localhost:8000/docs (when running)
- **Database**: Supabase dashboard
- **Monitoring**: GitHub Actions workflow logs

---

**Last Updated**: 2024-01-XX  
**Version**: 1.0  
**Next Review**: Monthly

---

> **⚠️ IMPORTANT**: This document is the single source of truth for all product decisions. Any changes to features, limits, or behavior must be reflected here first before implementation.