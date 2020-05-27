import yaml

with open('keywords.yaml', encoding='utf8') as stream:
    KEYWORDS = yaml.safe_load(stream)
del stream
