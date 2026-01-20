# Universal Anime/Manga Database Scraper

Comprehensive scraper that collects **ALL metadata** from **ALL major anime/manga services** and cross-references everything.

## 🎯 What It Does

- **Scrapes independently** from: AniList, MAL, Kitsu, AniDB, Simkl, TMDB, IMDB
- **Every file contains EVERYTHING**: Full metadata from ALL services + complete ID mappings
- **Two modes**: Full scrape (unlimited) or Update (check recent changes)
- **Automatic GitHub Actions**: Runs daily to keep data fresh

## 📁 Output Structure

```
media_database/
├── anilist/
│   ├── anime/
│   │   ├── 123.json  ← Contains ALL data from ALL services
│   │   └── ...
│   └── manga/
├── mal/
│   ├── anime/
│   └── manga/
├── kitsu/
├── anidb/
├── simkl/
├── tmdb/
└── imdb/
```

### Each File Contains:
```json
{
  "service": "anilist",
  "media_id": "123",
  "id_mappings": {
    "anilist": "123",
    "mal": "456",
    "kitsu": "789",
    "anidb": "999",
    "simkl": "111",
    "tmdb": "222",
    "imdb": "tt333"
  },
  "metadata_from_all_services": {
    "anilist": { /* Complete AniList data */ },
    "mal": { /* Complete MAL data */ },
    "kitsu": { /* Complete Kitsu data */ },
    "anidb": { /* Complete AniDB data */ },
    "simkl": { /* Complete Simkl data */ }
  }
}
```

## 🚀 GitHub Setup (Recommended)

### 1. Fork/Create Repository

1. Create new repository or fork this one
2. Add all files to your repo:
   - `scraper.py`
   - `requirements.txt`
   - `.github/workflows/scraper.yml`

### 2. Add Secret

Go to: **Settings → Secrets and variables → Actions → New repository secret**

- **Name:** `SIMKL_CLIENT_ID`
- **Value:** Your Simkl API key (or use default in code)

### 3. Run the Scraper

#### First Time (Full Scrape):
- Go to **Actions** tab
- Click "Anime/Manga Database Scraper"
- Click "Run workflow"
- Select: `full` mode
- This will scrape **ALL data from ALL services** (takes hours/days)

#### After First Run (Daily Updates):
- Automatically runs daily at 2 AM UTC
- Uses `update` mode
- Only updates entries older than 7 days
- Much faster!

#### Manual Update:
- Go to **Actions**
- Run workflow with `update` mode

## 💻 Local Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Scraper

**Full scrape (get everything):**
```bash
export SCRAPE_MODE=full
python scraper.py
```

**Update mode (check recent only):**
```bash
export SCRAPE_MODE=update
python scraper.py
```

**With custom Simkl key:**
```bash
export SIMKL_CLIENT_ID=your_key_here
export SCRAPE_MODE=full
python scraper.py
```

## 🔑 API Keys Required

**Only ONE key needed:**
- ✅ **Simkl** - Get from https://simkl.com/settings/developer/
  - Or use the default key in code (public demo key)

**No keys needed for:**
- ✅ AniList - Public API
- ✅ MAL (via Jikan) - Free, no auth
- ✅ Kitsu - Public API
- ✅ AniDB - Web scraping (be gentle!)

## 📊 Scrape Modes

### Full Mode (`SCRAPE_MODE=full`)
- Gets **ALL** data from **ALL** services
- No limits, scrapes everything
- Takes a long time (hours to days)
- Use for initial database build
- Recommended: Run once, then use update mode

### Update Mode (`SCRAPE_MODE=update`)
- Checks for new entries
- Updates entries older than 7 days
- Much faster
- Use for daily maintenance
- Default for scheduled runs

## ⚙️ Rate Limits

Built-in delays to respect API limits:
- AniList: 1 second
- MAL: 1 second
- Kitsu: 0.5 seconds
- AniDB: 3 seconds (strict!)
- Simkl: 0.5 seconds

## 📈 Monitoring

Check scraper status:
- **Actions tab**: See workflow runs
- **stats.json**: Contains scrape statistics
- **scraper_checkpoint.json**: Resume progress
- **cross_reference.json**: Master ID mappings

## 🛠️ Troubleshooting

### GitHub Actions fails
- Check secrets are set correctly
- Increase timeout in workflow file if needed
- Check rate limits weren't exceeded

### Local scraping stops
- Uses checkpoints - just run again to resume
- Check internet connection
- AniDB might temporarily block - wait and retry

### Missing data
- Some services might not have all anime/manga
- Cross-references fill in missing IDs
- Run enrichment phase to complete mappings

## 📝 Files Explained

- `scraper.py` - Main scraper with all logic
- `requirements.txt` - Python dependencies
- `.github/workflows/scraper.yml` - GitHub Actions automation
- `scraper_checkpoint.json` - Resume progress (auto-generated)
- `cross_reference.json` - Master ID mappings (auto-generated)
- `media_database/` - All scraped data (auto-generated)
- `media_database/stats.json` - Scrape statistics (auto-generated)

## 🎯 Use Cases

- Build anime/manga tracking apps
- Cross-reference IDs between services
- Aggregate metadata from multiple sources
- Sync user lists across platforms
- Create unified anime/manga database
- Data analysis and research

## ⚠️ Important Notes

1. **First run takes LONG**: Full scrape can take days
2. **Be respectful**: Don't decrease rate limits
3. **AniDB is sensitive**: Respect the 3s delay
4. **GitHub Actions timeout**: Max 24 hours per run
5. **Storage**: Database can grow very large
6. **Resume capability**: Always uses checkpoints

## 📜 License

Use freely, but please:
- Respect API rate limits
- Credit data sources
- Don't abuse services
- Share improvements!

---

**Questions?** Open an issue!
**Want to contribute?** Pull requests welcome!
