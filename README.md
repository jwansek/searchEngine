# searchEngine

## Setup

- `sudo pip3 install -r requirements.txt`

- Install nltk and spacy `en_core_web_sm`

## Index files

- Unzip Wikibooks.zip to a given directory

- Run `documents.py` with the first argument as the path to the HTML files:

- e.g. `python3 documents.py ../../Wikibooks`

- Run `terms.py`. This took me a few days. If it stops you can just run it again and it'll automatically restart at the correct place

## Setting up TF-IDF weighting

- `python3 tf_idf.py`

## Searching!

- You can use `search.py` to conduct searches. Make search terms command line arguments. 

- e.g. `python3 search.py AQA GCSE Computer Science` 

- Results are printed to stdout, to `searches/` as a markdown file

- It will be rendered as HTML and shown in a web browser automatically