"""
Generates an M3U playlist file from a downloaded playlist, preserving the
original playlist order from YouTube Music.
"""

import os
import re
from pathlib import Path

import SomeDL.utils.console as console
from SomeDL.utils.config import config


def generate_m3u(
    songs_list: list,
    metadata_success_list: list,
    already_downloaded_list: list,
    playlist_name: str = "playlist",
) -> None:
    """
    Write an M3U playlist file that mirrors the order of *songs_list* (i.e.
    the original YouTube Music playlist order).

    Only songs that were successfully downloaded or were already present on disk
    are included. Songs that failed to download are silently skipped with a
    warning.

    Args:
        songs_list:              Full ordered list of songs as returned by
                                 generateSongList(). This defines the playlist order.
        metadata_success_list:   Newly downloaded songs (have a ``path`` key).
        already_downloaded_list: Songs that were already on disk (also have a
                                 ``path`` key when the path could be resolved).
        playlist_name:           Base name used for the output .m3u file.
    """

    # --- Build a lookup: song_id -> absolute file path from successful downloads
    path_by_id: dict = {}

    for item in metadata_success_list + already_downloaded_list:
        song_id = item.get("song_id") or item.get("original_url_id")
        path = item.get("path")
        if song_id and path:
            path_by_id[song_id] = path

    # --- Determine the output directory for the playlist file
    output_dir = Path(config["download"]["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Sanitize playlist name for use as a filename
    safe_name = _sanitize_filename(playlist_name)
    if not safe_name:
        safe_name = "playlist"

    m3u_path = output_dir / (safe_name + ".m3u")

    # --- Avoid silently overwriting an existing playlist by appending a counter
    if m3u_path.exists():
        counter = 1
        while m3u_path.exists():
            m3u_path = output_dir / (safe_name + "_" + str(counter) + ".m3u")
            counter += 1

    lines = ["#EXTM3U", "#PLAYLIST:" + playlist_name, ""]

    skipped = 0
    added = 0

    for song in songs_list:
        song_id = song.get("song_id") or song.get("original_url_id")
        path = path_by_id.get(song_id)

        if not path:
            skipped += 1
            artist = song.get("artist_name", "")
            title = song.get("song_title", song_id or "Unknown")
            label = (artist + " - " + title) if artist else title
            console.warning("M3U: skipping \"" + label + "\" (not downloaded or path unavailable)")
            continue

        duration = song.get("duration", -1) or -1
        artist = song.get("artist_name", "")
        title = song.get("song_title", "")
        display = (artist + " - " + title) if artist else title

        # --- Make path relative to the playlist file location when possible
        try:
            rel_path = os.path.relpath(path, output_dir)
        except ValueError:
            # On Windows, relpath raises ValueError for different drives
            rel_path = path

        lines.append("#EXTINF:" + str(int(duration)) + "," + display)
        lines.append(rel_path)
        lines.append("")
        added += 1

    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\nM3U playlist saved to: " + str(m3u_path))
    print("  Tracks included: " + str(added))
    if skipped:
        print("  Tracks skipped (failed/missing): " + str(skipped))


def _sanitize_filename(name: str) -> str:
    """Remove characters that are unsafe in file names across platforms."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name).strip()
