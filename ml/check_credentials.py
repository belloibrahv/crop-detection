import pathlib

cache_paths = [
    pathlib.Path.home() / '.cache' / 'kagglehub' / 'credentials.json',
    pathlib.Path.home() / '.kaggle' / 'kaggle.json',
    pathlib.Path.home() / '.kaggle' / 'access_token',
]
for p in cache_paths:
    if p.exists():
        print(f'Found: {p}')
    else:
        print(f'Missing: {p}')
