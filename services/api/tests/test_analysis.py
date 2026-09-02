from app.service.analysis import _suffix


def test_suffix_preserves_safe_extension() -> None:
    assert _suffix("tracks/Album/Song.MP3") == ".mp3"


def test_suffix_ignores_directory_components() -> None:
    assert _suffix("tracks/looks.like.folder/song") == ".audio"


def test_suffix_rejects_unsafe_extension() -> None:
    assert _suffix("tracks/song.mp3/../../secret.wav") == ".wav"
    assert _suffix("tracks/song.extensiontoolong") == ".audio"
    assert _suffix("tracks/song.m4a-backup") == ".audio"
    assert _suffix("tracks/song.tar.gz") == ".gz"
