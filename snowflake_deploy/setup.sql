-- =============================================================================
-- XAU_AI_PRO - setup para Streamlit in Snowflake (SiS)
-- =============================================================================
-- Usa el database USER$ (default del usuario) y schema PUBLIC de tu workspace.
-- Ajusta COMMIT_WH y STREAMLIT_WH al nombre de tu warehouse (compute).
-- Ejecuta los pasos en orden con snowsql o en el worksheet Snowsight.
-- =============================================================================

-- 1) CREAR EL STAGE (almacen interno para los archivos del app)
--    Ver https://docs.snowflake.com/developer-guide/snowflake-native-app-features/creating-a-stage
CREATE OR REPLACE STAGE xau_ai_pro_stage
    FILE_FORMAT = 'CSV' CSV_DELIMITER = ',' CSV_HEADER = TRUE;

-- 2) SUBIR los archivos del app al stage (ejecutar desde snowsql CLI):
--    !define stage_name xau_ai_pro_stage
--    PUT file://ruta/a/XAU_AI_PRO/snowflake_deploy/app.py @xau_ai_pro_stage;
--    PUT file://ruta/a/XAU_AI_PRO/snowflake_deploy/environment.yml @xau_ai_pro_stage;
--
--    O desde Snowsight: crea el stage y sube los archivos con el boton Upload.

-- 3) CREAR LAS TABLAS BASE (opcional; el app muestra 0 si no existen)
CREATE OR REPLACE TABLE USER$.PUBLIC.XAU_AI_PRO_DATASET (
    TIMESTAMP TIMESTAMP_NTZ,
    PRICE FLOAT,
    PREDICTION FLOAT,
    CONFIDENCE FLOAT
);

CREATE OR REPLACE TABLE USER$.PUBLIC.XAU_AI_PRO_PREDICTIONS (
    CREATED_AT TIMESTAMP_NTZ,
    SYMBOL VARCHAR,
    PREDICTION VARCHAR,
    CONFIDENCE FLOAT
);

CREATE OR REPLACE TABLE USER$.PUBLIC.XAU_AI_PRO_FEEDBACK (
    CREATED_AT TIMESTAMP_NTZ,
    PREDICTION_ID VARCHAR,
    FEEDBACK VARCHAR
);

CREATE OR REPLACE TABLE USER$.PUBLIC.XAU_AI_PRO_RETRAIN_LOG (
    CREATED_AT TIMESTAMP_NTZ,
    RESULT VARCHAR,
    DURATION_SECONDS FLOAT
);

-- 4) CREAR EL APP STREAMLIT IN SNOWFLAKE
--    main_file apunta a app.py dentro del stage.
--    Reemplaza TU_WAREHOUSE por el nombre real de tu compute warehouse.
CREATE STREAMLIT xau_ai_pro_dashboard
    ROOT_LOCATION = '@xau_ai_pro_stage'
    MAIN_FILE = 'app.py'
    QUERY_WAREHOUSE = 'TU_WAREHOUSE';

-- 5) VERIFICAR y abrir:
--    SHOW STREAMLITS;
--    Deploy / open en Snowsight -> Apps de Streamlit.