import os
import shlex
import sys
from datetime import datetime
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

# Folder holding the pipeline scripts and the "raw data" folder. The scripts use
# paths relative to it, so every task runs with it as the working directory.
# Defaults to this file's real folder (so a symlink in your DAGs folder works).
# If you copy the file instead, or in production, set it: FIELDSENSE_HOME=/opt/fieldsense
FIELDSENSE_HOME = os.environ.get("FIELDSENSE_HOME", os.path.dirname(os.path.realpath(__file__)))
PYTHON = shlex.quote(sys.executable)

# Define default arguments
default_args = {
    'owner': 'fieldsense',
    'depends_on_past': False,
    'start_date': datetime(2025, 4, 30),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1
}

# Create DAG
dag = DAG(
    'fieldsense_inference_router',
    default_args=default_args,
    description='FieldSense multimodal inference router pipeline',
    schedule=None,  # Manual trigger only (changed from schedule_interval in Airflow 3.0)
    catchup=False
)

# Task 1: Preprocess raw data
preprocess_data = BashOperator(
    task_id='preprocess_data',
    bash_command=f'{PYTHON} preprocess.py',
    cwd=FIELDSENSE_HOME,
    dag=dag
)

# Task 2: Fuse and route data
fuse_and_route = BashOperator(
    task_id='fuse_and_route',
    bash_command=f'{PYTHON} fusion_router.py',
    cwd=FIELDSENSE_HOME,
    dag=dag
)

# Task 3: Run inference client
run_inference = BashOperator(
    task_id='run_inference',
    bash_command=f'{PYTHON} inference_client.py',
    cwd=FIELDSENSE_HOME,
    dag=dag
)

# Define task dependencies
preprocess_data >> fuse_and_route >> run_inference
