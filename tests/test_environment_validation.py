import pytest
from BitVector import BitVector
from ais_area_notice import imo_001_26_environment as env


def test_sensor_report_base_validation():
    # Valid
    env.SensorReport(
        report_type=0, year=2020, month=5, day=15, hour=12, minute=30, site_id=5
    )
    with pytest.raises(ValueError):
        env.SensorReport(
            report_type=99, year=2020, month=5, day=15, hour=12, minute=30, site_id=5
        )
    with pytest.raises(ValueError):
        env.SensorReport(
            report_type=0, year=1999, month=5, day=15, hour=12, minute=30, site_id=5
        )
    with pytest.raises(ValueError):
        env.SensorReport(
            report_type=0, year=2101, month=5, day=15, hour=12, minute=30, site_id=5
        )
    with pytest.raises(ValueError):
        env.SensorReport(
            report_type=0, year=2020, month=13, day=15, hour=12, minute=30, site_id=5
        )
    with pytest.raises(ValueError):
        env.SensorReport(
            report_type=0, year=2020, month=5, day=32, hour=12, minute=30, site_id=5
        )
    with pytest.raises(ValueError):
        env.SensorReport(
            report_type=0, year=2020, month=5, day=15, hour=24, minute=30, site_id=5
        )
    with pytest.raises(ValueError):
        env.SensorReport(
            report_type=0, year=2020, month=5, day=15, hour=12, minute=60, site_id=5
        )
    with pytest.raises(ValueError):
        env.SensorReport(
            report_type=0, year=2020, month=5, day=15, hour=12, minute=30, site_id=128
        )


def test_sensor_report_decode_bits():
    sr = env.SensorReport(report_type=0, site_id=1)
    with pytest.raises(ValueError):
        sr.decode_bits(BitVector(size=26))  # too small
    with pytest.raises(ValueError):
        sr.decode_bits(BitVector(size=113))  # too big
    with pytest.raises(ValueError):
        sr.decode_bits(BitVector(size=112), year=1999)  # invalid year
    with pytest.raises(ValueError):
        sr.decode_bits(BitVector(size=112), year=2020, month=13)  # invalid month


def test_sensor_report_get_bits():
    sr = env.SensorReport(report_type=0, site_id=1)
    sr.report_type = 0
    sr.day = 1
    sr.hour = 1
    sr.minute = 1
    sr.site_id = 1
    # We shouldn't easily hit the size exceptions here since size is fixed,
    # but the assertions exist in the code just in case length is somehow wrong.


def test_sensor_report_location_validation():
    with pytest.raises(ValueError):
        env.SensorReportLocation(site_id=1, lon=182, lat=90)
    with pytest.raises(ValueError):
        env.SensorReportLocation(site_id=1, lon=-181, lat=90)
    with pytest.raises(ValueError):
        env.SensorReportLocation(site_id=1, lon=0, lat=92)
    with pytest.raises(ValueError):
        env.SensorReportLocation(site_id=1, lon=0, lat=-91)
    with pytest.raises(ValueError):
        env.SensorReportLocation(site_id=1, alt=-1)
    with pytest.raises(ValueError):
        env.SensorReportLocation(site_id=1, alt=200.4)
    with pytest.raises(ValueError):
        env.SensorReportLocation(site_id=1, owner=7)
    with pytest.raises(ValueError):
        env.SensorReportLocation(site_id=1, timeout=6)
    with pytest.raises(ValueError):
        env.SensorReportLocation(site_id=None)


def test_sensor_report_id_validation():
    with pytest.raises(ValueError):
        env.SensorReportId(site_id=1, id_str="this_is_a_very_long_string_indeed")


def test_sensor_report_wind_validation():
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, speed=-1)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, speed=123)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, gust=-1)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, gust=123)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, dir=-1)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, dir=361)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, gust_dir=-1)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, gust_dir=361)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, data_descr=99)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, forecast_speed=123)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, forecast_gust=123)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, forecast_dir=361)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, forecast_day=32)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, forecast_hour=25)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, forecast_minute=61)
    with pytest.raises(ValueError):
        env.SensorReportWind(site_id=1, duration_min=256)


def test_sensor_report_water_level_validation():
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, wl_type=2)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, wl=-328)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, wl=328)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, trend=4)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, vdatum=15)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, data_descr=99)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, forecast_type=2)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, forecast_wl=-328)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, forecast_day=32)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, forecast_hour=25)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, forecast_minute=61)
    with pytest.raises(ValueError):
        env.SensorReportWaterLevel(site_id=1, duration_min=256)


def test_sensor_report_current2d_validation():
    with pytest.raises(ValueError):
        env.SensorReportCurrent2d(site_id=1, speed_1=25.0)
    with pytest.raises(ValueError):
        env.SensorReportCurrent2d(site_id=1, dir_1=361)
    with pytest.raises(ValueError):
        env.SensorReportCurrent2d(site_id=1, level_1=363)
    with pytest.raises(ValueError):
        env.SensorReportCurrent2d(site_id=1, data_descr=99)


def test_sensor_report_current3d_validation():
    with pytest.raises(ValueError):
        env.SensorReportCurrent3d(site_id=1, n_1=25.0)
    with pytest.raises(ValueError):
        env.SensorReportCurrent3d(site_id=1, e_1=25.0)
    with pytest.raises(ValueError):
        env.SensorReportCurrent3d(site_id=1, z_1=25.0)
    with pytest.raises(ValueError):
        env.SensorReportCurrent3d(site_id=1, level_1=363)
    with pytest.raises(ValueError):
        env.SensorReportCurrent3d(site_id=1, data_descr=99)


def test_sensor_report_current_horz_validation():
    with pytest.raises(ValueError):
        env.SensorReportCurrentHorz(site_id=1, bearing_1=361)
    with pytest.raises(ValueError):
        env.SensorReportCurrentHorz(site_id=1, dist_1=123)
    with pytest.raises(ValueError):
        env.SensorReportCurrentHorz(site_id=1, dir_1=361)
    with pytest.raises(ValueError):
        env.SensorReportCurrentHorz(site_id=1, level_1=362)


def test_sensor_report_sea_state_validation():
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, swell_height=25.0)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, swell_period=62)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, swell_dir=362)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, sea_state=14)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, swell_data_descr=99)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, temp=-11.0)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, temp_depth=13.0)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, temp_data_descr=99)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, wave_height=25.0)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, wave_period=62)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, wave_dir=362)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, wave_data_descr=99)
    with pytest.raises(ValueError):
        env.SensorReportSeaState(site_id=1, salinity=51.0)


def test_sensor_report_salinity_validation():
    with pytest.raises(ValueError):
        env.SensorReportSalinity(site_id=1, temp=-11.0)
    with pytest.raises(ValueError):
        env.SensorReportSalinity(site_id=1, cond=-1.0)
    with pytest.raises(ValueError):
        env.SensorReportSalinity(site_id=1, cond=8.0)
    with pytest.raises(ValueError):
        env.SensorReportSalinity(site_id=1, pres=-1.0)
    with pytest.raises(ValueError):
        env.SensorReportSalinity(site_id=1, pres=6001.0)
    with pytest.raises(ValueError):
        env.SensorReportSalinity(site_id=1, salinity=-1.0)
    with pytest.raises(ValueError):
        env.SensorReportSalinity(site_id=1, salinity=51.0)
    with pytest.raises(ValueError):
        env.SensorReportSalinity(site_id=1, salinity_type=3)
    with pytest.raises(ValueError):
        env.SensorReportSalinity(site_id=1, data_descr=99)


def test_sensor_report_weather_validation():
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, air_temp=-61.0)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, air_temp_data_descr=99)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, precip=4)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, vis=-1.0)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, vis=25.0)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, dew=-21.0)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, dew=51.0)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, dew_data_descr=99)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, air_pres=799)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, air_pres=1203)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, air_pres_trend=4)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, air_pres_data_descr=99)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, salinity=-1.0)
    with pytest.raises(ValueError):
        env.SensorReportWeather(site_id=1, salinity=51.0)


def test_sensor_report_air_gap_validation():
    with pytest.raises(ValueError):
        env.SensorReportAirGap(site_id=1, draft=82.0)
    with pytest.raises(ValueError):
        env.SensorReportAirGap(site_id=1, gap=82.0)
    with pytest.raises(ValueError):
        env.SensorReportAirGap(site_id=1, gap_trend=4)
    with pytest.raises(ValueError):
        env.SensorReportAirGap(site_id=1, forecast_gap=82.0)
    with pytest.raises(ValueError):
        env.SensorReportAirGap(site_id=1, forecast_day=32)
    with pytest.raises(ValueError):
        env.SensorReportAirGap(site_id=1, forecast_hour=25)
    with pytest.raises(ValueError):
        env.SensorReportAirGap(site_id=1, forecast_minute=61)


def test_environment_validation():
    with pytest.raises(ValueError):
        env.Environment(source_mmsi=-1)
    with pytest.raises(ValueError):
        env.Environment(source_mmsi=1000000000)
