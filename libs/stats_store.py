import json
import os
import threading
from datetime import datetime

from kivy.logger import Logger

class StatsStore:
    """Persist photobooth usage statistics in a JSON file."""

    def __init__(self, stats_file, max_prints=None):
        self.stats_file = stats_file
        self.max_prints = max_prints if isinstance(max_prints, int) and max_prints >= 0 else None
        self._lock = threading.Lock()

    def get_default_stats(self):
        return {
            'photos_taken': 0,
            'prints': 0,
            'downloads': 0,
            'gallery_views': 0,
            'collage_views': 0,
            'image_views': 0,
            'first_photo_date': None,
            'last_photo_date': None,
            'last_print_date': None,
            'last_download_date': None,
            'sessions': [],
        }

    def load(self):
        stats = self.get_default_stats()

        try:
            with self._lock:
                if os.path.exists(self.stats_file):
                    with open(self.stats_file, 'r', encoding='utf-8') as handle:
                        loaded_stats = json.load(handle)

                    if isinstance(loaded_stats, dict):
                        stats.update(loaded_stats)
        except Exception as exc:
            Logger.error(f'StatsStore: Error loading stats: {exc}')

        return stats

    def save(self, stats):
        try:
            with self._lock:
                stats_directory = os.path.dirname(self.stats_file)
                if stats_directory:
                    os.makedirs(stats_directory, exist_ok=True)

                temp_stats_file = f'{self.stats_file}.tmp'
                with open(temp_stats_file, 'w', encoding='utf-8') as handle:
                    json.dump(stats, handle, indent=2)
                    handle.write('\n')

                os.replace(temp_stats_file, self.stats_file)
        except Exception as exc:
            Logger.error(f'StatsStore: Error saving stats: {exc}')

    def track_event(self, event_type):
        try:
            with self._lock:
                stats = self.get_default_stats()

                if os.path.exists(self.stats_file):
                    with open(self.stats_file, 'r', encoding='utf-8') as handle:
                        loaded_stats = json.load(handle)

                    if isinstance(loaded_stats, dict):
                        stats.update(loaded_stats)

                if event_type == 'print':
                    stats['prints'] += 1
                    stats['last_print_date'] = datetime.now().isoformat()
                elif event_type == 'download':
                    stats['downloads'] += 1
                    stats['last_download_date'] = datetime.now().isoformat()
                elif event_type == 'gallery_view':
                    stats['gallery_views'] += 1
                elif event_type == 'collage_view':
                    stats['collage_views'] += 1
                elif event_type == 'image_view':
                    stats['image_views'] += 1

                stats_directory = os.path.dirname(self.stats_file)
                if stats_directory:
                    os.makedirs(stats_directory, exist_ok=True)

                temp_stats_file = f'{self.stats_file}.tmp'
                with open(temp_stats_file, 'w', encoding='utf-8') as handle:
                    json.dump(stats, handle, indent=2)
                    handle.write('\n')

                os.replace(temp_stats_file, self.stats_file)
        except Exception as exc:
            Logger.error(f'StatsStore: Error tracking event: {exc}')

    def track_photo_taken(self, session_id=None):
        try:
            stats = self.load()
            stats['photos_taken'] += 1
            photo_timestamp = datetime.now().isoformat()
            stats['last_photo_date'] = photo_timestamp

            if stats['first_photo_date'] is None:
                stats['first_photo_date'] = photo_timestamp

            if session_id and session_id not in stats['sessions']:
                stats['sessions'].append(session_id)

            self.save(stats)
        except Exception as exc:
            Logger.error(f'StatsStore: Error tracking photo: {exc}')

    def reset(self):
        self.save(self.get_default_stats())

    def get_print_limit_info(self):
        stats = self.load()
        prints = max(0, int(stats.get('prints', 0) or 0))

        if self.max_prints is None:
            return {
                'enabled': False,
                'max_prints': None,
                'prints': prints,
                'remaining': None,
                'reached': False,
            }

        remaining = max(0, self.max_prints - prints)
        return {
            'enabled': True,
            'max_prints': self.max_prints,
            'prints': prints,
            'remaining': remaining,
            'reached': prints >= self.max_prints,
        }

    def can_print(self):
        return not self.get_print_limit_info()['reached']

    def track_print(self):
        self.track_event('print')
