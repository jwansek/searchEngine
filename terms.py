from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
from nltk.util import ngrams  
import collections  
import documents
import database
import bs4
import re

STOPWORDS = set(stopwords.words('english')).difference({
    "how", "because", "through", "or", "as", "about", "not",
    "no", "who", "of", "can", "over", "you"
}).union({chr(i) for i in range(97, 123)}.difference({"a", "i"}))
LEM = WordNetLemmatizer()

def main():
    numdocs = documents.get_num_documents()
    for document_id in range(1, numdocs):
        parse_document(document_id, documents.get_document_name_by_id(document_id), numdocs)

        # break

def parse_document(document_id, document_path, numdocs):
    with open(document_path, "r") as f:
       soup = bs4.BeautifulSoup(f.read(), "lxml")

    text = [e.text for e in soup.find("div", {"class": "mw-parser-output"}).findChildren(recursive = True)]
    text = [re.sub(r"[^a-zA-Z\s]", "", i).rstrip().lower() for i in text]
    
    terms = []
    for i in text:
        terms += re.split(r"\s+|\n", i)
    
    terms = [LEM.lemmatize(i) for i in terms if i != "" and i not in STOPWORDS]
    terms_counted = collections.Counter(terms)

    with database.Database() as db:
        db.append_terms(terms)
        print("[%f%%] Added %d terms from docid: %d" % ((document_id/numdocs)*100, len(terms_counted), document_id)) 

        db.append_terms_in_document(document_id, terms_counted)
        print("Appended term frequency too")

if __name__ == "__main__":
    main()