# Anime/Manga Mapped Database

A comprehensive anime and manga ID mapping database that aggregates data from multiple services and creates unified cross-reference mappings.

## Features

- **Parallel Scraping**: All services scraped simultaneously using GitHub Actions
- **Cross-Service Mapping**: Intelligent ID linking using graph algorithms
- **Incremental Updates**: Checkpoint system for resume capability
- **Clean Output**: Matches Fribb's anime-lists format exactly

## Supported Services

### Anime (11 services)
- AniDB (Base ID)
- AniList
- MyAnimeList
- Kitsu
- AnimeNewsNetwork
- Anime-Planet
- Livechart
- SIMKL
- TMDB
- TVDB
- IMDB

### Manga (3 services)
- AniList (Base ID)
- MyAnimeList
- Kitsu

## Quick Start

### Local Testing

```bash
# Clone repository
git clone https://github.com/itsmechinmoy/animanga-mapped.git
cd animanga-mapped

# Install dependencies
pip install -r requirements.txt

# Run individual scraper
python scripts/run_anime_scraper.py --service anilist

# Run mapper
python scripts/run_mapper.py --type anime
```

### GitHub Actions

Push to GitHub and the workflows will automatically:
1. Scrape all services in parallel
2. Merge and map the data
3. Commit final mapped files

## Output Format

```json
[
  {
    "type": "TV",
    "anidb_id": 1,
    "anilist_id": 290,
    "mal_id": 290,
    "kitsu_id": 265,
    "themoviedb_id": 26209,
    "tvdb_id": 72025,
    "imdb_id": "tt0286390",
    "season": {
      "tvdb": 1,
      "tmdb": 1
    }
  }
]
```

## Project Structure

```
animanga-mapped/
├── scrapers/           # Individual service scrapers
├── mappers/           # Mapping & merging logic
├── utils/             # Utility functions
├── scraped-data/      # Raw scraped data (artifacts)
├── mapped-data/       # Final mapped output (committed)
├── checkpoints/       # Scraping progress
└── scripts/           # Execution scripts
```

## License
MIT License

## Credits
Inspired by:
- [anime-lists](https://github.com/Anime-Lists/anime-lists) by ScudLee
- [anime-lists-generator](https://github.com/Fribb/anime-lists-generator) by Fribb
- [anime-offline-database](https://github.com/manami-project/anime-offline-database)
