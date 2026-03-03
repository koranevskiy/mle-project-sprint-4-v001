# download_recs.py
import os
import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

def download_recommendations():
    """Загрузка файлов с рекомендациями из S3"""
    
    # Параметры подключения к S3
    endpoint = "https://storage.yandexcloud.net"
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    bucket_name = os.getenv('BUCKET_NAME')
    
    # Создаем клиент S3
    session = boto3.session.Session()
    s3_client = session.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4'),
    )
    
    local_dir = 'recsys/recommendations'
    os.makedirs(local_dir, exist_ok=True)
    
    files_to_download = [
        'recommendations.parquet',
        'similar.parquet',
        'top_popular.parquet'
    ]
    
    print("📥 Загрузка файлов из S3...")
    
    for filename in files_to_download:
        s3_key = f"recsys/recommendations/{filename}"
        local_path = os.path.join(local_dir, filename)
        
        try:
            print(f"  Загрузка {filename}...")
            s3_client.download_file(bucket_name, s3_key, local_path)
            print(f"  ✅ {filename} загружен")
        except Exception as e:
            print(f"  ❌ Ошибка загрузки {filename}: {e}")
    
    print("\n✅ Загрузка завершена!")

if __name__ == "__main__":
    download_recommendations()