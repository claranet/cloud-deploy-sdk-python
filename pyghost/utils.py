def is_dev_version(version):
    if version.startswith('GHOST-'):
        version = 'dev'
    if version in {'dev', 'master', 'stable'}:
        return True
    return False
