from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

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
    bash_command='python /opt/fieldsense/preprocess.py',
    dag=dag
)

# Task 2: Fuse and route data
fuse_and_route = BashOperator(
    task_id='fuse_and_route',
    bash_command='python /opt/fieldsense/fusion_router.py',
    dag=dag
)

# Task 3: Run inference client
run_inference = BashOperator(
    task_id='run_inference',
    bash_command='python /opt/fieldsense/inference_client.py',
    dag=dag
)

# Define task dependencies
preprocess_data >> fuse_and_route >> run_inference 