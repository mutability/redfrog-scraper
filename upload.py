import boto, os

_bucket = None

def init():
    global _bucket
    if _bucket is None:
        import ConfigParser
        parser = ConfigParser.ConfigParser()
        parser.read('rfscrape.ini')

        s3 = boto.connect_s3()
        _bucket = s3.get_bucket(parser.get('s3','bucket'))

def upload(f, key_name, content_type=None, public=True, rr=True):
    init()

    key = _bucket.new_key(key_name=key_name)
    if content_type: key.content_type = content_type
    
    policy = 'public-read' if public else None
    key.set_contents_from_filename(filename = f,
                                   replace = True,
                                   reduced_redundancy = rr,
                                   policy = policy)
