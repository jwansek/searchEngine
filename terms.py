from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from nltk.util import ngrams
from nltk import pos_tag  
import collections
import itertools  
import documents
import database
import random
import nltk
import time
import bs4
import os
import re

import spacy
from spacy import displacy
nlp = spacy.load("en_core_web_sm")
nlp.max_length = 100000000

STOPWORDS = set(stopwords.words('english')).difference({
    "how", "because", "through", "or", "as", "about", "not",
    "no", "who", "of", "can", "over", "you"
}).union({chr(i) for i in range(98, 123)})
STOPWORDS.remove("a")
LEM = WordNetLemmatizer()

def main():
    numdocs = documents.get_num_documents()
    with database.Database() as db:
        startat = db.get_max_linked_terms() - 1
    #docid = random.randint(1, numdocs)
    #parse_document(docid, documents.get_document_name_by_id(docid), numdocs)

    for document_id in range(startat, numdocs):
        parse_document(document_id, documents.get_document_name_by_id(document_id), numdocs)

        #break

def parse_region(raw_text, region_weight, document_id):
    print("d: %d; w: %d; len = %d" % (document_id, region_weight, len(raw_text)))
    terms = word_tokenize(raw_text)
    terms = [re.sub(r"[^a-zA-Z0-9\s]", "", term).rstrip().lower() for term in terms]
    terms = [LEM.lemmatize(i) for i in terms if i != "" and i not in STOPWORDS]

    processed = nlp(raw_text)
    linked_words = []
    for ent in processed.ents:
        words = [
            re.sub(r"[^a-zA-Z0-9\s]", "", word).rstrip().lower() 
            for word in word_tokenize(ent.text) 
            if re.sub(r"[^a-zA-Z0-9\s]", "", word).rstrip().lower() != ""
        ]
        if len(words) > 1:
            linked_words.append(words)

    return append_region(terms, linked_words, region_weight, document_id)

def append_region(terms, linked_words, region_weight, document_id):
    flattened_linked_words = set(itertools.chain.from_iterable(linked_words))
    with database.Database() as db:
        db.append_terms(flattened_linked_words.union(set(terms)))
        ids = db.get_vocabulary_ids(flattened_linked_words)
        
        linked_words_ids = [str([ids[j] for j in i])[1:-1].replace(" ", "") for i in linked_words]
        db.append_merged_terms(linked_words_ids)

    weighted_terms = {i[0]:i[1] * region_weight for i in collections.Counter(terms).items()}
    weighted_linked_terms = {i[0]:i[1] * region_weight for i in collections.Counter(linked_words_ids).items()}

    return weighted_terms, weighted_linked_terms

def parse_document(document_id, document_path, numdocs):
    starttime = time.time()
    with open(document_path, "r") as f:
       soup = bs4.BeautifulSoup(f.read(), "lxml")

    weighted_terms = collections.Counter()
    weighted_linked_terms = collections.Counter()

    # parse the file name, it has a weight of 100
    filenametext = os.path.splitext(os.path.split(document_path)[-1])[0]
    region_weighted_terms, region_linked_terms = parse_region(filenametext, 100, document_id)
    weighted_terms += region_weighted_terms
    weighted_linked_terms += region_linked_terms

    # parse the main text, it has a weight of 1
    text = " ".join([e.text for e in soup.find("div", {"class": "mw-parser-output"}).findChildren(recursive = True)])
    # split large texts into more manageable chunks
    for splittext in [text[i:i+99999] for i in range(0, len(text), 99999)]:
        region_weighted_terms, region_linked_terms = parse_region(splittext, 1, document_id)
        weighted_terms += region_weighted_terms
        weighted_linked_terms += region_linked_terms

    # parse html headers
    elemtexts = []
    try:
        elemtexts += [e.text for e in soup.h1.findChildren(recursive = True)]
    except AttributeError:
        pass
    
    try:
        elemtexts += [e.text for e in soup.h2.findChildren(recursive = True)]
    except AttributeError:
        pass

    region_weighted_terms, region_linked_terms = parse_region(re.sub(r"edit|Contents|source", "", " ".join(elemtexts)), 50, document_id)
    weighted_terms += region_weighted_terms
    weighted_linked_terms += region_linked_terms

    # parse html link elements texts, has a weight of 10
    a_texts = [e.text for e in soup.select("a") if e.text != "" and e.text != "edit" and e.text != "edit source"]
    region_weighted_terms, region_linked_terms = parse_region(" ".join(a_texts), 10, document_id)
    weighted_terms += region_weighted_terms
    weighted_linked_terms += region_linked_terms

    with database.Database() as db:
        db.append_document_term_weights(weighted_terms, document_id)
        db.append_document_linked_term_weights(weighted_linked_terms, document_id)

    print("[%.3f%%] {%.1fs} %d terms (weight %d), %d linked terms (weight %d) - %s" % (
        (document_id/numdocs)*100,
        time.time() - starttime, 
        len(weighted_terms), 
        sum(weighted_terms.values()), 
        len(weighted_linked_terms), 
        sum(weighted_linked_terms.values()),
        document_path
    ))


if __name__ == "__main__":
    main()
