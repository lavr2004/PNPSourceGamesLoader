# PNPSourceGamesLoader
`PNPSourceGamesLoader` is a tool designed to automate the downloading of assets (images, 3D models, PDFs, etc.) from Steam Workshop mods for Tabletop Simulator. It extracts links from workshop mod files and saves them to a local folder with appropriate file extensions (e.g., `.png`, `.pdf`, `.obj`). This is particularly useful for crafting physical versions of Print-and-Play tabletop games or accessing digital assets for use in Tabletop Simulator.

# How to use

1. Log in into steam via browser
2. Go to tabletop simulator workshop by url: https://steamcommunity.com/workshop/browse/?appid=286160&browsesort=trend&section=readytouseitems
3. Browse required tabletop game
4. Copy url from browser in format: https://steamcommunity.com/sharedfiles/filedetails/?id=dddddddddd 
5. Setup constant STEAM_WORKSHOP_URL as that url and launch the script

---

The script supports:
- Downloading assets from Steam Workshop mods.
- Handling various file types (images, 3D models, PDFs, archives, etc.).
- Automatic detection of file extensions based on content signatures.
- Support for Imgur, Dropbox, and Steam Cloud URLs.
- Logging of download progress and errors for debugging.

## Prerequisites

Before using the script, ensure you have the following:
- **Python**: Version 3.10 or higher.
- **Dependencies**:
    - `requests` (version 2.28.1): For making HTTP requests.
    - `tqdm` (version 4.66.5): For displaying a progress bar during downloads.
- **Steam Account**: You must be logged into Steam via a browser to access some private or restricted workshop content.
- **Tabletop Simulator**: Optional, for verifying mod content in-game.

## Installation

1. **Install Python**:
    - Download and install Python 3.10 or higher from [python.org](https://www.python.org/downloads/).
    - Ensure `pip` is installed and available in your command line.

2. **Clone or Download the Repository**:
    - Clone this repository or download it as a ZIP file and extract it to a folder, e.g., `D:\!DEV_APPS\051_python_SteamWorkShopsTabletopPNPDownloader\SteamWorkShopsTabletopPNPDownloader`.

3. **Install Dependencies**:
    - Open a terminal in the project directory and run:
      ```bash
      pip install requests==2.28.1
      pip install tqdm==4.66.5