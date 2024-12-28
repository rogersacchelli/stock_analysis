import hashlib


def get_report_hash(data):

    md5_hash = hashlib.md5()
    # Update the hash object with the bytes of the data
    md5_hash.update(data.encode('utf-8'))

    # Get the hexadecimal digest of the hash
    hex_digest = md5_hash.hexdigest()

    return hex_digest
