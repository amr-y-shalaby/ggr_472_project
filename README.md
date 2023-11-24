# GGR473 : GGR473 Group Project

## Members:
|     Name     | Student Number |             Email             |
|:------------:|:--------------:|:-----------------------------:|
| Matthew Ruku |   1000881272   | matthew.ruku@mail.utoronto.ca |
|   Ryan Siu   |   1007268519   |   ryan.siu@mail.utoronto.ca   |
| Amr Shalaby  |   1005280397   | amr.shalaby@mail.utoronto.ca  |


## Pipeline Design

## 1. Staging Layer:
### 1. Monthly Data Web Scraping:
To download the Ontario monthly air quality data from https://dd.weather.gc.ca/air_quality/aqhi/ont/observation/monthly/csv/, function _load_monthly_data(boolean save_loally)_in the the Data Loader is /Python/Data_Loader.py File.
which ingests the public data into the **first** staging table "**stg_monthly_air_data**."

| Column         | Data Type        |
|----------------|------------------|
| index          | bigint           |
| date           | date             |
| hour_utc       | bigint           |
| FAFFD          | double precision |
| FALIF          | double precision |
| FALJI          | double precision |
| FAMXK          | double precision |
| FAYJG          | double precision |
| FAZKI          | double precision |
| FBKKK          | double precision |
| FBLJL          | double precision |
| FBLKS          | double precision |
| FCAEN          | double precision |
| FCCOT          | double precision |
| FCFUU          | double precision |
| FCGKZ          | double precision |
| FCIBD          | double precision |
| FCKTB          | double precision |
| FCNJT          | double precision |
| FCTOV          | double precision |
| FCWFX          | double precision |
| FCWOV          | double precision |
| FCWYG          | double precision |
| FDATE          | double precision |
| FDCHU          | double precision |
| FDEGT          | double precision |
| FDGED          | double precision |
| FDGEJ          | double precision |
| FDGEM          | double precision |
| FDJFN          | double precision |
| FDMOP          | double precision |
| FDQBU          | double precision |
| FDQBX          | double precision |
| FDSUS          | double precision |
| FDZCP          | double precision |
| FEAKO          | double precision |
| FEARV          | double precision |
| FEBWC          | double precision |
| FEUTC          | double precision |
| FEUZB          | double precision |
| FEVJR          | double precision |
| FEVJS          | double precision |
| FEVJV          | double precision |
| FEVNS          | double precision |
| FEVNT          | double precision |
| last_updated   | timestamp        |
| donwnload_link | text             |
| src_filename   | text             |

### 2. Monthly Forecasts Data Web Scraping:
To download the Ontario monthly air quality data from https://dd.weather.gc.ca/air_quality/aqhi/ont/forecast/model/csv/, the function _load_monthly_forecasts(boolean save_locally)_ in the Data Loader located at /Python/Data_Loader.py File.
which ingests the public data into the **second** staging table "**stg_monthly_forecasts**" with the option to locally save the CSV files with a prefix **'FORECAST_'** to differentiate them from the actual monthly data.


|      Column       | Data Type |
|:-----------------:|:---------:|
|       index       |  bigint   |
|    cgndb_code     |   text    |
|  community_name   |   text    |
|   validity_date   |   date    |
| validity_time_utc |   text    |
|      period       |  bigint   |
|       value       |  bigint   |
|      amended      |  bigint   |
|   last_updated    | timestamp |
|  donwnload_link   |   text    |
|   src_filename    |   text    |


### 3. Traffic Volume:
Using the REST API provided for Toronto Traffic Volume https://open.toronto.ca/dataset/traffic-volumes-at-intersections-for-all-modes/, the function _load_traffic_volumes(boolean save_locally)_ in the Data Loader located at /Python/Data_Loader.py File.
which ingests the traffic volume data into the **third** staging table "**stg_traffic_volume**" with the option to locally save the CSV file to _'./Data/traffic_volume.csv'_.

|      Column       |    Data Type     |
|:-----------------:|:----------------:|
|        _id        |      bigint      |
|    location_id    |      bigint      |
|     location      |       text       |
|        lng        | double precision |
|        lat        | double precision |
|  centreline_type  | double precision |
|   centreline_id   | double precision |
|        px         | double precision |
| latest_count_date |       text       |
|   download_link   |       text       |
|     filename      |       text       |
|   last_updated    |    timestamp     |

### 4. Geographical D:
Downloads and extracts the zip file of the Geographical Names Data from https://natural-resources.canada.ca/earth-sciences/geography/download-geographical-names-data/9245, the function _load_geo_names(boolean save_locally)_ in the Data Loader located at /Python/Data_Loader.py File.
which ingests the geographical names data containing the coordinates of the air quality stations into the **fourth** staging table "**stg_geo_names**" with the option to retain the extracted CSV file to _'./Data/cgn_canada_csv_eng.csv'_.

|        Column        |    Data Type     |
|:--------------------:|:----------------:|
|        index         |      bigint      |
|       cgndb_id       |       text       |
|  geographical_name   |       text       |
|       language       |       text       |
|    syllabic_form     |       text       |
|     generic_term     |       text       |
|   generic_category   |       text       |
|     concise_code     |       text       |
| toponymic_feature_id |       text       |
|       latitude       | double precision |
|      longitude       | double precision |
|       location       |       text       |
|  province_territory  |       text       |
|  relevance_at_scale  |      bigint      |
|    decision_date     |       date       |
|        source        |       text       |
|     last_updated     |    timestamp     |
|    donwnload_link    |       text       |
|     src_filename     |       text       |
