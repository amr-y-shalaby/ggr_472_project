import datetime
import gc
import h2o
import pandas as pd
import geopandas as gpd
from h2o.automl import H2OAutoML
from data_extractor import configs_obj
import sys
h2o.init()


# A Generic Class to store the needed dataframes of three main types:
# Pandas, GeoPandas, and H2O Dataframes for the AutoML Step.
class GenericClass():
    def __init__(self):
        self.geopandas_dict = {}
        self.pandas_dict = {}
        self.h2o_dict = {}
        self.forecasts_dict = {}
        self.lists = {}


dfs_obj = GenericClass()

#
def create_dataframes(configs_obj):
    dfs_start = datetime.datetime.now()
    query_get_tables = """SELECT table_name FROM information_schema.tables
            WHERE (table_schema = 'public') and (table_name not in(
            'spatial_ref_sys','geography_columns','geometry_columns','data_model_performance_tbl'))"""
    cur = configs_obj.pg_engine.cursor()
    cur.execute(query_get_tables)
    del query_get_tables
    public_tables = [item[0] for item in cur.fetchall()]
    print('+++++++++++++++++++++++++++++\nPublic Tables in Production Schema: ', public_tables, '\n+++++++++++++++++++++++++++++')
    print('Creating Dataframes From Public Schema Tables as of: {}\n'.format(datetime.datetime.now()))

    i = 1
    for public_table in public_tables:
        print(f"{i} of {len(public_tables)}: Processing Public Table '{public_table}':")
        if 'proj' not in public_table:
            print(f"\tCreating Dataframe 'df_{public_table}' from Table '{public_table}'")
            pd_exec_statement = f"df_{public_table} = pd.read_sql_table(table_name='{public_table}', con=configs_obj.sqlalchemy_engine, schema='public')"
            exec(pd_exec_statement, globals())
            exec(f"df_{public_table}.dropna(inplace=True)", globals())
            if 'fact_traffic_volume' == public_table:
                df_fact_traffic_volume['latest_count_date'] = pd.to_datetime(df_fact_traffic_volume['latest_count_date'])
            exec(f"h_df_{public_table} = h2o.h2o.H2OFrame(df_{public_table})", globals())
            df_name = f"'df_{public_table}'"
            exec(f"dfs_obj.pandas_dict[{df_name}] = df_{public_table}", globals())
            exec(f"dfs_obj.h2o_dict[{df_name}] = h_df_{public_table}", globals())
            if 'fact_traffic_volume' in public_table:
                df_fact_traffic_volume['latest_count_date'] = pd.to_datetime(df_fact_traffic_volume['latest_count_date'])
                dfs_obj.df_fact_traffic_volume = df_fact_traffic_volume.dropna()
                dfs_obj.h_df_fact_traffic_volume = h2o.h2o.H2OFrame(dfs_obj.df_fact_traffic_volume)
                dfs_obj.h_df_fact_traffic_volume['_id'] = dfs_obj.h_df_fact_traffic_volume['_id'].asfactor()
                dfs_obj.h_df_fact_traffic_volume['location_id'] = dfs_obj.h_df_fact_traffic_volume['location_id'].asfactor()
                dfs_obj.h_df_fact_traffic_volume['location'] = dfs_obj.h_df_fact_traffic_volume['location'].asfactor()

        if 'proj' in public_table:
            print(f"\tCreating Projected Dataframe 'gpdf_{public_table}' from Table '{public_table}'")
            gpdf_exec_statement = f"gdf_{public_table} = gpd.read_postgis('SELECT * FROM public.{public_table}', con=configs_obj.sqlalchemy_engine, geom_col='geom', crs='EPSG:26917')"
            exec(gpdf_exec_statement, globals())
            exec(f"gdf_{public_table}.dropna(inplace=True)", globals())
            exec(f"h_gdf_{public_table} = h2o.h2o.H2OFrame(gdf_{public_table})", globals())
            df_name = f"'df_{public_table}'"
            exec(f"dfs_obj.geopandas_dict[{df_name}] = gdf_{public_table}", globals())
            exec(f"dfs_obj.h2o_dict[{df_name}] = h_gdf_{public_table}", globals())
        i = i + 1

    temp_df = df_fact_gta_traffic_arcgis.dropna()
    temp_df['count_date'] = pd.to_datetime(temp_df['count_date'])
    temp_df.sort_values(by=['count_date'], inplace=True)
    temp_df.set_index('count_date', inplace=True)

    data = []
    for _, d in temp_df.groupby('count_date'):
        data.append([[row['latitude'], row['longitude'], row['f8hr_vehicle_volume']] for _, row in d.iterrows()])

    dfs_obj.pandas_dict['temp_df'] = temp_df
    dfs_obj.lists['traffic'] = data
    dfs_end = datetime.datetime.now()
    dfs_total_seconds = (dfs_end - dfs_start).total_seconds()

    performance_query = f"""UPDATE public.data_model_performance_tbl
        SET duration_seconds = {dfs_total_seconds} , files_processed = {len(public_tables)}
        , start_time = '{dfs_start}', end_time = '{dfs_end}'
        WHERE step_name = 'create_dataframes';"""
    cur = configs_obj.pg_engine.cursor()
    cur.execute(performance_query)
    configs_obj.pg_engine.commit()
    print(
        f"****************************\nDone Storing Public Tables in Dataframes Object 'dfs_obj' whose size is: {sys.getsizeof(dfs_obj)} Byes in {dfs_total_seconds} Seconds.\n****************************"
    )
    del dfs_start, dfs_end, temp_df, data, dfs_total_seconds
    gc.collect()
    return dfs_obj


## Auto Machine Learning Step using the previously-created data frames object.
def auto_ml(dfs_obj):
    automl_start = datetime.datetime.now()

    # Part 1: Traffic Prediction
    print(
        f"Starting Traffic AutoML with Runtime: {configs_obj.run_time_seconds} Seconds, "
        f"Traffic Forecast Horizon: {configs_obj.forecast_horizon}, and Traffic Forecast Frequency: "
        f"{configs_obj.forecast_description}.")
    X = ['location_id', '_id', 'latest_count_date', 'lat', 'lng']
    y = 'px'
    aml = H2OAutoML(max_runtime_secs=configs_obj.run_time_seconds)
    aml.train(x=X, y=y, training_frame=dfs_obj.h_df_fact_traffic_volume, leaderboard_frame=dfs_obj.h_df_fact_traffic_volume)
    leader_model = aml.leader
    df_traffic_forecasts = pd.DataFrame()
     
    for location_id in dfs_obj.df_fact_traffic_volume['location_id'].unique():
        df_preds = pd.DataFrame()
        df_location = dfs_obj.df_fact_traffic_volume[dfs_obj.df_fact_traffic_volume['location_id'] == location_id]
        df_location['latest_count_date'] = pd.to_datetime(dfs_obj.df_fact_traffic_volume['latest_count_date'])
        start = pd.to_datetime(dfs_obj.df_fact_traffic_volume['latest_count_date'].max() + pd.Timedelta(days=7))
        future_dates = pd.date_range(start=start, freq=configs_obj.forecast_frequency,periods=configs_obj.forecast_horizon)
        df_preds['latest_count_date'] = future_dates
        df_preds['location_id'] = location_id
        df_preds['_id'] = dfs_obj.df_fact_traffic_volume['_id'].unique()[0]
        latitude = dfs_obj.df_fact_traffic_volume['lat'][dfs_obj.df_fact_traffic_volume['location_id'] == location_id].unique()[0]
        longitude = dfs_obj.df_fact_traffic_volume['lng'][dfs_obj.df_fact_traffic_volume['location_id'] == location_id].unique()[0]
        df_preds = df_preds[['location_id', '_id', 'latest_count_date']]
        h_df_preds = h2o.H2OFrame(df_preds)
        h_df_preds['location_id'] = h_df_preds['location_id'].asfactor()
        h_df_preds['_id'] = h_df_preds['_id'].asfactor()
        df_location.reset_index(drop=True, inplace=True)
        predicted_traffic = leader_model.predict(h_df_preds)
        h_df_preds['predicted_traffic'] = predicted_traffic
        df_preds = h_df_preds.as_data_frame()
        df_preds['future_date'] = pd.to_datetime(df_preds['latest_count_date'], unit='ms').dt.date
        df_preds['lat'] = latitude
        df_preds['lng'] = longitude
        df_preds['predicted_traffic'] = int(round(df_preds['predicted_traffic'],0))
        df_preds = df_preds[['location_id', '_id' ,'lat', 'lng', 'future_date', 'predicted_traffic']]
        df_traffic_forecasts = df_traffic_forecasts._append(df_preds)

    df_traffic_forecasts['last_inserted'] = datetime.datetime.now()
    dfs_obj.forecasts_dict['df_traffic_forecasts'] = df_traffic_forecasts
    df_traffic_forecasts.to_sql(name='fact_h2o_traffic_forecasts', con=configs_obj.sqlalchemy_engine
                                , schema='public', if_exists='replace', index=False, index_label=False)
    print(f'Saved Forecasts to Database in : {(datetime.datetime.now()-automl_start).total_seconds()} Seconds')
    del df_traffic_forecasts, dfs_obj.df_fact_traffic_volume, dfs_obj.h_df_fact_traffic_volume
    # End of Part 1 Traffic Prediction.

    # Part 2: Pedestrians Prediction
    print(
        f"Starting Pedestrians AutoML with Runtime: {configs_obj.run_time_seconds} Seconds, "
        f"Pedestrians Forecast Horizon: {configs_obj.forecast_horizon}, and Pedestrians Forecast Frequency: "
        f"{configs_obj.forecast_description}.")
    X = ['objectid', 'tcs__', 'main', 'latitude', 'longitude', 'count_date']
    y = 'f8hr_pedestrian_volume'
    aml = H2OAutoML(max_runtime_secs=configs_obj.run_time_seconds)
    dfs_obj.h2o_dict['df_fact_gta_traffic_arcgis']['objectid'] = dfs_obj.h2o_dict['df_fact_gta_traffic_arcgis']['objectid'].asfactor()
    dfs_obj.h2o_dict['df_fact_gta_traffic_arcgis']['tcs__'] = dfs_obj.h2o_dict['df_fact_gta_traffic_arcgis']['tcs__'].asfactor()
    dfs_obj.h2o_dict['df_fact_gta_traffic_arcgis']['main'] = dfs_obj.h2o_dict['df_fact_gta_traffic_arcgis']['main'].asfactor()
    aml.train(x=X, y=y, training_frame=dfs_obj.h2o_dict['df_fact_gta_traffic_arcgis'], leaderboard_frame=dfs_obj.h2o_dict['df_fact_gta_traffic_arcgis'])
    leader_model = aml.leader
    df_pedestrians_forecasts = pd.DataFrame()

    for objectid in dfs_obj.pandas_dict['df_fact_gta_traffic_arcgis']['objectid'].unique():
        df_preds = pd.DataFrame()
        df_location = dfs_obj.pandas_dict['df_fact_gta_traffic_arcgis'][dfs_obj.pandas_dict['df_fact_gta_traffic_arcgis']['objectid'] == objectid]
        df_location['count_date'] = pd.to_datetime(df_location['count_date'])
        start = pd.to_datetime(dfs_obj.pandas_dict['df_fact_gta_traffic_arcgis']['count_date'].max() + pd.offsets.DateOffset(years=9))
        future_dates = pd.date_range(start=start, freq=configs_obj.forecast_frequency,periods=configs_obj.forecast_horizon)
        df_preds['count_date'] = future_dates
        df_preds['objectid'] = objectid
        df_preds['tcs__'] = dfs_obj.pandas_dict['df_fact_gta_traffic_arcgis']['tcs__'].unique()[0]
        df_preds['latitude'] = df_location['latitude'][df_location['objectid'] == objectid].unique()[0]
        df_preds['longitude'] = df_location['longitude'][df_location['objectid'] == objectid].unique()[0]
        df_preds['main'] = df_location['main'][df_location['objectid'] == objectid].unique()[0]
        df_preds = df_preds[['objectid', 'tcs__', 'main', 'latitude', 'longitude', 'count_date']]
        h_df_preds = h2o.H2OFrame(df_preds)
        h_df_preds['objectid'] = h_df_preds['objectid'].asfactor()
        h_df_preds['tcs__'] = h_df_preds['tcs__'].asfactor()
        h_df_preds['main'] = h_df_preds['main'].asfactor()
        df_location.reset_index(drop=True, inplace=True)
        predicted_pedestrians = leader_model.predict(h_df_preds)
        h_df_preds['predicted_pedestrians'] = predicted_pedestrians
        df_preds = h_df_preds.as_data_frame()
        df_preds['future_date'] = pd.to_datetime(df_preds['count_date'], unit='ms').dt.date
        df_preds['predicted_pedestrians'] = int(round(df_preds['predicted_pedestrians'],0))
        df_preds = df_preds[['objectid', 'tcs__' , 'main', 'latitude', 'longitude', 'future_date', 'predicted_pedestrians']]
        df_pedestrians_forecasts = df_pedestrians_forecasts._append(df_preds)

    df_pedestrians_forecasts['last_inserted'] = datetime.datetime.now()
    dfs_obj.forecasts_dict['df_pedestrians_forecasts'] = df_pedestrians_forecasts
    df_pedestrians_forecasts.to_sql(name='fact_h2o_pedestrians_forecasts', con=configs_obj.sqlalchemy_engine
                                , schema='public', if_exists='replace', index=False, index_label=False)
    print(f'Saved Pedestrians Forecasts to Database in {(datetime.datetime.now()-automl_start).total_seconds()} Seconds')
    del df_pedestrians_forecasts
    # End of Part 2 Pedestrians forecast
    gc.collect()
    h2o.cluster().shutdown()
    automl_end = datetime.datetime.now()
    automl_duration = (automl_end - automl_start).total_seconds()
    performance_query = f"""UPDATE public.data_model_performance_tbl
        SET duration_seconds = {automl_duration} , files_processed = {1}
        , start_time = '{automl_start}', end_time = '{automl_end}'
        WHERE step_name = 'auto_ml';"""
    cur = configs_obj.pg_engine.cursor()
    cur.execute(performance_query)
    configs_obj.pg_engine.commit()
    print(
        f'****************************\nDone AutoML Using Configuration Runtime: {configs_obj.run_time_seconds} Seconds, Forecast '
        f'Horizon: {configs_obj.forecast_horizon}, and Forecast Frequency: { configs_obj.forecast_description}.\n'
        f'Objects Dataframe Size is now: {sys.getsizeof(dfs_obj)} Byes.  AutoML duration in realtime is: {automl_duration} Seconds.\n****************************')
    return dfs_obj