#!/usr/bin/env python
"""Container start-up: wait for dependencies, prepare them, then exec the server.

Waiting here rather than in compose's `depends_on` because a container reporting
"up" only means its process started -- Postgres accepts connections seconds later,
and MinIO later still. Doing it in code also means the same guarantees hold on
AWS, where there is no compose file to express ordering at all.
"""
import os
import subprocess
import sys
import time


def log(msg):
    print(f"[entrypoint] {msg}", flush=True)


def wait_for(name, check, timeout=90):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            check()
            log(f"{name} ready")
            return
        except Exception as exc:  # noqa: BLE001 - any failure means "not ready yet"
            last = exc
            time.sleep(1.5)
    log(f"FATAL: {name} not ready after {timeout}s -- last error: {last}")
    sys.exit(1)


def wait_for_postgres():
    import psycopg

    dsn = (
        f"host={os.environ.get('POSTGRES_HOST', 'db')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'aeonx')} "
        f"user={os.environ.get('POSTGRES_USER', 'aeonx')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'aeonx')}"
    )

    def check():
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            conn.execute("SELECT 1")

    wait_for("postgres", check)


def ensure_bucket():
    """Create the bucket if missing and make its objects publicly readable.

    Only ever runs against a self-hosted endpoint (MinIO). On real S3 the bucket
    and its policy are managed by whoever owns the AWS account -- an application
    that can rewrite its own bucket policy is a liability, and the deploy IAM role
    should not even carry the permission.
    """
    endpoint = os.environ.get("AWS_S3_ENDPOINT_URL")
    if not endpoint:
        log("no custom S3 endpoint -- assuming a managed bucket, skipping setup")
        return

    import json

    import boto3
    from botocore.client import Config

    bucket = os.environ.get("AWS_STORAGE_BUCKET_NAME", "aeonx-documents")

    def check():
        boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        ).list_buckets()

    wait_for("minio", check)

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    existing = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
    if bucket not in existing:
        s3.create_bucket(Bucket=bucket)
        log(f"created bucket {bucket}")

    # Investor filings are public records; anonymous GET is the intended access
    # path. Scoped to reads of objects only -- never to listing or writing.
    s3.put_bucket_policy(
        Bucket=bucket,
        Policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }],
        }),
    )
    log(f"bucket {bucket} is public-read")


def run(*args):
    log(" ".join(args))
    subprocess.run(args, check=True)


def main():
    wait_for_postgres()
    ensure_bucket()

    run("python", "manage.py", "migrate", "--noinput")
    run("python", "manage.py", "createcachetable")
    run("python", "manage.py", "bootstrap_roles")

    if not os.environ.get("DJANGO_DEBUG", "").lower() in ("1", "true", "yes", "on"):
        run("python", "manage.py", "collectstatic", "--noinput")

    # Convenience for a fresh local stack only. Django's createsuperuser refuses
    # to clobber an existing username, so re-running is harmless.
    if os.environ.get("DJANGO_SUPERUSER_USERNAME") and os.environ.get("DJANGO_SUPERUSER_PASSWORD"):
        try:
            run("python", "manage.py", "createsuperuser", "--noinput")
        except subprocess.CalledProcessError:
            log("superuser already exists -- continuing")

    log(f"starting: {' '.join(sys.argv[1:])}")
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
