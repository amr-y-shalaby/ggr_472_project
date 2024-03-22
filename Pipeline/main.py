from data_extractor import configs_obj, read_configs, initialize_database
import data_loader
import datetime
import pandas as pd
import dataframes_creator
from dataframes_creator import dfs_obj
import maps_creator
import os

# Configure the Run Conditions:
# 1. create_tables: boolean : If the Tables are already created, then set create_tables = False
# 2. show_maps: boolean : To display maps in the browser after maps are built.
# 3. If AutoML to be skipped.
configs_obj.run_conditions = {'create_tables': False, 'show_maps': False, 'run_auto_ml': True
            , 'map_types': ['folium', 'mapbox', 'turf']}

# First Step is to create Staging and Production Data.  This can be bypassed if the Tables are created
if configs_obj.run_conditions['create_tables']:
    read_configs()
    initialize_database()
    start = datetime.datetime.now()
    print('Executing Pipeline as of ' + str(start))
    staging_tables_list = data_loader.create_staging_tables(sqlalchemy_engine=configs_obj.sqlalchemy_engine)
    production_tables_list = data_loader.create_production_tables()
    df_production = pd.DataFrame(production_tables_list,
                        columns=['step_name', 'duration_seconds', 'start_time', 'end_time', 'files_processed'])
    df_production['phase'] = 'production'
    df_production = df_production[
        ['phase', 'step_name', 'duration_seconds', 'start_time', 'end_time', 'files_processed']]
    df_stage = pd.DataFrame(staging_tables_list,
                            columns=['step_name', 'duration_seconds', 'start_time', 'end_time', 'files_processed'])
    df_stage['phase'] = 'stage'
    df_stage = df_stage[['phase', 'step_name', 'duration_seconds', 'start_time', 'end_time', 'files_processed']]
    pipeline_df = pd.concat([df_production, df_stage])
    pipeline_df.drop(pipeline_df.tail(1).index, inplace=True)
    del df_stage, df_production
    if configs_obj.save_locally:
        print('Saving Data Model Performance {} in: {}'.format('data_model_performance.csv',
                                                               configs_obj.parent_dir + '/Analytics/'))
        pipeline_df.to_csv(configs_obj.parent_dir + '/Analytics/data_model_performance.csv', index=False,
                           index_label=False)

    pipeline_df['step_name'] = pipeline_df['step_name'].apply(lambda x: os.path.basename(x))
    pipeline_df.to_sql(name='data_model_performance_tbl', con=configs_obj.sqlalchemy_engine, if_exists='replace',
                       schema='public', index_label=False, index=False)

    # Track Performance of WebMaps and AutoML Steps.
    print('Inserting WebMaps Performance Logs Entries into database.')
    webmaps_query = f"""insert into public.data_model_performance_tbl (phase, step_name, duration_seconds, start_time, end_time, files_processed) 
         VALUES   
         ('WebMaps', 'folium', -1, '2002-05-01 00:00:00.0000', '2002-03-15 13:59:12.498894', -1)
       , ('WebMaps', 'mapbox', -1, '2002-05-01 00:00:00.0000', '2002-03-15 13:59:12.498894', -1)
       , ('WebMaps', 'turf', -1, '2002-05-01 00:00:00.0000', '2002-03-15 13:59:12.498894', -1)
       , ('WebMaps', 'auto_ml', -1, '2002-05-01 00:00:00.0000', '2002-03-15 13:59:12.498894', -1)
       , ('WebMaps', 'create_dataframes', -1, '2002-05-01 00:00:00.0000', '2024-03-15 13:59:12.498894', -1);"""
    cur = configs_obj.pg_engine.cursor()
    cur.execute(webmaps_query)
    configs_obj.pg_engine.commit()
    end = datetime.datetime.now()
    total_seconds = (end - start).total_seconds()
    print('Done Executing Pipeline as of {} in {} Seconds'.format(end, str(total_seconds)))
    print('*****************************\n')
# End of the First Step #

# Second Step : Not optional.  Create Dataframes needed for the AutoML #
# Create the Object Containing the Dataframes to avoid running create_dfs() function repeatedly in auto_ml() and
# create_maps().  Also H2O Auto ML needs to save and insert Prediction Dataframes into object.
if not configs_obj.run_conditions['create_tables']:
    read_configs()
    initialize_database()
dataframes_creator.create_dataframes(configs_obj)

# Auto Machine Learning can be omitted.
if configs_obj.run_conditions['run_auto_ml']:
    dataframes_creator.auto_ml(dfs_obj)

# Third Step: Create HTML Maps.  It Cannot be skipped. If AutoML was skipped, the forecast
# layer will not be added to the map.
maps_creator.create_maps(dfs_obj=dfs_obj, configs_obj=configs_obj
                    , map_types=configs_obj.run_conditions['map_types']
                    , show=configs_obj.run_conditions['show_maps']
                    , add_auto_ml=configs_obj.run_conditions['run_auto_ml'])

# Fourth Step: Test Load the Created HTML Maps
