import boto3

bucket_name = 'datasci-210-summer-2025-sec-documents' 

# Initialize S3 client using env vars
s3 = boto3.client('s3')

# List all objects with .json extension
def list_json_files(bucket):
    response = s3.list_objects_v2(Bucket=bucket)
    if 'Contents' not in response:
        print("❌ No files found in bucket.")
        return

    print("📂 JSON files in bucket:")
    for obj in response['Contents']:
        key = obj['Key']
        if key.endswith('.json'):
            print(f" - {key}")

if __name__ == "__main__":
    list_json_files(bucket_name)