import boto, os

BUCKET = os.getenv('S3_BUCKET','frog.randomly.org')

def upload(f, key_name, content_type=None, public=True, rr=True):
    s3 = boto.connect_s3()
    bucket = s3.get_bucket(BUCKET)

    key = bucket.new_key(key_name=key_name)
    if content_type: key.content_type = content_type
    
    policy = 'public-read' if public else None
    key.set_contents_from_filename(filename = f,
                                   replace = True,
                                   reduced_redundancy = rr,
                                   policy = policy)
