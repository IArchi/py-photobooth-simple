import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from libs.stats_store import StatsStore
from libs.web_server import WebServer


def test_log_files_are_sorted_newest_first(tmp_path):
    old_log = tmp_path / 'old.log'
    new_log = tmp_path / 'new.log'
    old_log.write_text('old', encoding='utf-8')
    new_log.write_text('new', encoding='utf-8')
    os.utime(old_log, (1000, 1000))
    os.utime(new_log, (2000, 2000))

    server = WebServer.__new__(WebServer)
    server.logs_directory = str(tmp_path)

    assert [item['filename'] for item in server._get_log_files()] == ['new.log', 'old.log']


def test_log_path_rejects_traversal(tmp_path):
    log_file = tmp_path / 'photobooth.log'
    log_file.write_text('safe', encoding='utf-8')

    server = WebServer.__new__(WebServer)
    server.logs_directory = str(tmp_path)

    assert server._get_safe_log_path('photobooth.log') == str(log_file)
    assert server._get_safe_log_path('../config.ini') is None
    assert server._get_safe_log_path('missing.log') is None


def test_delete_all_log_files_removes_only_files(tmp_path):
    log_file = tmp_path / 'photobooth.log'
    nested_dir = tmp_path / 'archive'
    nested_log = nested_dir / 'old.log'
    log_file.write_text('log', encoding='utf-8')
    nested_dir.mkdir()
    nested_log.write_text('old', encoding='utf-8')

    server = WebServer.__new__(WebServer)
    server.logs_directory = str(tmp_path)

    assert server._delete_all_log_files() == 1
    assert not log_file.exists()
    assert nested_log.exists()


def test_disk_usage_info_uses_save_directory(tmp_path):
    server = WebServer.__new__(WebServer)
    server.save_directory = str(tmp_path)
    server.project_root = str(tmp_path.parent)

    disk_usage = server._get_disk_usage_info()

    assert disk_usage['path'] == str(tmp_path)
    assert disk_usage['total'].endswith(('GB', 'TB'))
    assert disk_usage['used'].endswith(('GB', 'TB'))
    assert disk_usage['free'].endswith(('GB', 'TB'))
    assert 0 <= disk_usage['used_percent'] <= 100


def test_print_limit_reads_and_updates_stats(tmp_path):
    stats_file = tmp_path / '.stats.json'
    stats_file.write_text('{"prints": 2}\n', encoding='utf-8')

    store = StatsStore(str(stats_file), max_prints=3)

    info = store.get_print_limit_info()

    assert info == {
        'enabled': True,
        'max_prints': 3,
        'prints': 2,
        'remaining': 1,
        'reached': False,
    }
    assert store.can_print() is True

    store.track_print()

    updated_info = store.get_print_limit_info()
    assert updated_info['prints'] == 3
    assert updated_info['remaining'] == 0
    assert updated_info['reached'] is True
    assert store.can_print() is False


def test_print_limit_disabled_by_default(tmp_path):
    store = StatsStore(str(tmp_path / '.stats.json'))

    info = store.get_print_limit_info()

    assert info == {
        'enabled': False,
        'max_prints': None,
        'prints': 0,
        'remaining': None,
        'reached': False,
    }
    assert store.can_print() is True
