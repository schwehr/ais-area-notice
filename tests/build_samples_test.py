import datetime
import io
import os

from ais_area_notice import build_samples
from ais_area_notice import imo_001_22_area_notice as an
from ais_area_notice import imo_001_26_environment as env


def test_env_dump(capsys):
    e = env.Environment(source_mmsi=366001)
    e.append(
        env.SensorReportLocation(
            year=2012,
            month=10,
            day=22,
            hour=0,
            minute=8,
            site_id=1,
            owner=5,
            timeout=5,
        )
    )
    build_samples.env_dump(e, "Test description")
    captured = capsys.readouterr()
    assert "Test description" in captured.out


def test_env_samples(capsys):
    build_samples.env_samples()
    captured = capsys.readouterr()
    assert "No location" in captured.out


def test_dump_all(capsys):
    area = an.AreaNotice(
        an.notice_type["cau_mammals_not_obs"],
        datetime.datetime(2011, 7, 6, 1, 10, 0, tzinfo=datetime.UTC),
        60,
        10,
        source_mmsi=123456789,
    )
    area.name = "test_area"
    f = io.StringIO()
    build_samples.dump_all(area, f)
    captured = capsys.readouterr()
    assert "test_area" in captured.out


def test_point(capsys):
    f = io.StringIO()
    build_samples.point(-69.8, 42.0, an.notice_type["cau_mammals_not_obs"], f)
    captured = capsys.readouterr()
    assert "# Point" in captured.out


def test_main(capsys, tmp_path, monkeypatch):
    # Copy areanotice_styles.kml to tmp_path
    with open("areanotice_styles.kml", "r") as f:
        styles = f.read()

    monkeypatch.chdir(tmp_path)
    with open("areanotice_styles.kml", "w") as f:
        f.write(styles)

    build_samples.main()
    captured = capsys.readouterr()
    assert "# Building sample set on" in captured.out
    assert os.path.exists("samples.kml")
